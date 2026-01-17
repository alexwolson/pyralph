"""Main iteration loop for Ralph."""

import subprocess
import time
from pathlib import Path
from typing import Optional

from ralph import git_utils, gutter, parser, state, task, tokens
from ralph.debug import debug_log
from ralph.providers import ProviderRotation


def build_prompt(workspace: Path, iteration: int) -> str:
    """Build the Ralph prompt for an iteration."""
    task_file = workspace / "RALPH_TASK.md"
    guardrails_file = workspace / ".ralph" / "guardrails.md"
    progress_file = workspace / ".ralph" / "progress.md"
    errors_file = workspace / ".ralph" / "errors.log"

    # Read state files with explicit UTF-8 encoding
    task_content = task_file.read_text(encoding="utf-8") if task_file.exists() else ""
    guardrails_content = guardrails_file.read_text(encoding="utf-8") if guardrails_file.exists() else ""
    progress_content = progress_file.read_text(encoding="utf-8") if progress_file.exists() else ""
    errors_content = errors_file.read_text(encoding="utf-8") if errors_file.exists() else ""

    prompt = f"""# Ralph Iteration {iteration}

You are an autonomous development agent using the Ralph methodology.

## FIRST: Read State Files

Before doing anything:
1. Read `RALPH_TASK.md` - your task and completion criteria
2. Read `.ralph/guardrails.md` - lessons from past failures (FOLLOW THESE)
3. Read `.ralph/progress.md` - what's been accomplished
4. Read `.ralph/errors.log` - recent failures to avoid

## Working Directory (Critical)

You are already in a git repository. Work HERE, not in a subdirectory:

- Do NOT run `git init` - the repo already exists
- Do NOT run scaffolding commands that create nested directories (`npx create-*`, `npm init`, etc.)
- If you need to scaffold, use flags like `--no-git` or scaffold into the current directory (`.`)
- All code should live at the repo root or in subdirectories you create manually

## Git Protocol (Critical)

Ralph's strength is state-in-git, not LLM memory. Commit early and often:

1. After completing each criterion, commit your changes:
   `git add -A && git commit -m 'ralph: implement state tracker'`
   `git add -A && git commit -m 'ralph: fix async race condition'`
   `git add -A && git commit -m 'ralph: add CLI adapter with commander'`
   Always describe what you actually did - never use placeholders like '<description>'
2. After any significant code change (even partial): commit with descriptive message
3. Before any risky refactor: commit current state as checkpoint
4. Push after every 2-3 commits: `git push`

If you get rotated, the next agent picks up from your last commit. Your commits ARE your memory.

## Task Execution

1. Work on the next unchecked criterion in RALPH_TASK.md (look for `[ ]`)
2. Run tests after changes (check RALPH_TASK.md for test_command)
3. **Mark completed criteria**: Edit RALPH_TASK.md and change `[ ]` to `[x]`
   - Example: `- [ ] Implement parser` becomes `- [x] Implement parser`
   - This is how progress is tracked - YOU MUST update the file
4. Update `.ralph/progress.md` with what you accomplished
5. When ALL criteria show `[x]`: output `<ralph>COMPLETE</ralph>`
6. If stuck 3+ times on same issue: output `<ralph>GUTTER</ralph>`

## Learning from Failures

When something fails:
1. Check `.ralph/errors.log` for failure history
2. Figure out the root cause
3. Add a Sign to `.ralph/guardrails.md` using this format:

```
### Sign: [Descriptive Name]
- **Trigger**: When this situation occurs
- **Instruction**: What to do instead
- **Added after**: Iteration {iteration} - what happened
```

## Context Rotation Warning

You may receive a warning that context is running low. When you see it:
1. Finish your current file edit
2. Commit and push your changes
3. Update .ralph/progress.md with what you accomplished and what's next
4. You will be rotated to a fresh agent that continues your work

Begin by reading the state files.
"""
    return prompt


def run_single_iteration(
    workspace: Path, 
    provider,
    iteration: int,
    warn_threshold: int = tokens.WARN_THRESHOLD,
    rotate_threshold: int = tokens.ROTATE_THRESHOLD,
    timeout: int = 300,
) -> str:
    """Run a single iteration. Returns signal (ROTATE, GUTTER, COMPLETE, or empty).
    
    Args:
        workspace: Project directory path
        provider: LLM provider instance
        iteration: Current iteration number
        warn_threshold: Token count at which to warn about context size
        rotate_threshold: Token count at which to trigger rotation
        timeout: Timeout in seconds for provider operations (default 300)
    """
    
    prompt = build_prompt(workspace, iteration)
    
    # Create token tracker and gutter detector with configurable thresholds
    token_tracker = tokens.TokenTracker(
        warn_threshold=warn_threshold,
        rotate_threshold=rotate_threshold,
    )
    gutter_detector = gutter.GutterDetector()
    
    # Log session start
    provider_name = provider.cli_tool if hasattr(provider, 'cli_tool') else str(type(provider).__name__)
    state.log_progress(workspace, f"**Session {iteration} started** (provider: {provider_name})")
    
    # Build provider command
    cmd = provider.get_command(prompt)
    
    # Start agent process
    agent_process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(workspace),
        text=False,
    )
    
    # Send prompt
    agent_process.stdin.write(prompt.encode("utf-8"))
    agent_process.stdin.close()
    
    # Track start time for timeout
    start_time = time.time()
    
    # Parse stream with timeout checking
    signal = ""
    try:
        for sig in parser.parse_stream(workspace, agent_process, token_tracker, gutter_detector, provider):
            signal = sig
            if signal in ("ROTATE", "GUTTER", "COMPLETE"):
                # Stop early if critical signal
                agent_process.terminate()
                break
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                debug_log(
                    "loop.py:run_single_iteration",
                    "Timeout reached - terminating provider",
                    {"timeout": timeout, "elapsed": elapsed, "provider": provider_name},
                )
                agent_process.terminate()
                signal = "ROTATE"
                break
    except Exception as e:
        debug_log(
            "loop.py:run_single_iteration",
            "Exception during stream parsing",
            {"error": str(e), "provider": provider_name},
        )
        agent_process.terminate()
        raise
    
    # Wait for process to finish with timeout
    try:
        agent_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        agent_process.kill()
        agent_process.wait()
    
    return signal


def run_ralph_loop(
    project_dir: Path,
    max_iterations: int,
    branch: Optional[str] = None,
    open_pr: bool = False,
    warn_threshold: int = tokens.WARN_THRESHOLD,
    rotate_threshold: int = tokens.ROTATE_THRESHOLD,
    timeout: int = 300,
) -> None:
    """Run the main Ralph loop with provider rotation.
    
    Args:
        project_dir: Project directory path
        max_iterations: Maximum number of iterations to run
        branch: Optional branch name to create and work on
        open_pr: Whether to open a PR when complete
        warn_threshold: Token count at which to warn about context size
        rotate_threshold: Token count at which to trigger rotation
        timeout: Timeout in seconds for provider operations (default 300)
    """
    from ralph.providers import get_provider_rotation
    
    workspace = project_dir.resolve()
    
    # Commit any uncommitted work first
    if git_utils.has_uncommitted_changes(workspace):
        git_utils.commit_changes(workspace, "ralph: initial commit before loop")
    
    # Create branch if requested
    if branch:
        git_utils.create_branch(workspace, branch)
    
    # Detect available providers and create rotation manager
    provider_rotation = get_provider_rotation()
    if not provider_rotation.providers:
        raise Exception("No LLM providers available. Please install cursor-agent, claude, gemini, or codex.")
    
    # Main loop
    iteration = 1
    
    from rich.console import Console
    console = Console()
    
    while iteration <= max_iterations:
        # Get current provider
        provider = provider_rotation.get_current()
        provider_name = provider_rotation.get_provider_name()
        
        debug_log(
            "loop.py:run_ralph_loop",
            "Loop iteration started",
            {
                "iteration": iteration,
                "provider_name": provider_name,
                "current_index": provider_rotation.current_index,
                "total_providers": len(provider_rotation.providers),
                "provider_names": [p.cli_tool if hasattr(p, 'cli_tool') else str(type(p).__name__) for p in provider_rotation.providers]
            },
            "A"
        )
        
        console.print(f"\n[bold cyan]🔄 Iteration {iteration}/{max_iterations}[/bold cyan] [dim](provider: {provider_name})[/dim]")
        
        try:
            # Run iteration
            signal = run_single_iteration(
                workspace, provider, iteration,
                warn_threshold=warn_threshold,
                rotate_threshold=rotate_threshold,
                timeout=timeout,
            )
            
            # Check task completion
            task_file = workspace / "RALPH_TASK.md"
            completion_status = task.check_completion(task_file)
            
            if completion_status == "COMPLETE":
                state.log_progress(workspace, f"**Session {iteration} ended** - ✅ TASK COMPLETE")
                print(f"\n🎉 RALPH COMPLETE! All criteria satisfied.")
                print(f"Completed in {iteration} iteration(s).")
                
                # Open PR if requested
                if open_pr and branch:
                    git_utils.push_branch(workspace, branch)
                    git_utils.open_pr(workspace, branch)
                
                return
            
            # Handle signals
            if signal == "COMPLETE":
                # Verify with checkbox check
                if completion_status == "COMPLETE":
                    state.log_progress(workspace, f"**Session {iteration} ended** - ✅ TASK COMPLETE (agent signaled)")
                    print(f"\n🎉 RALPH COMPLETE! Agent signaled completion and all criteria verified.")
                    print(f"Completed in {iteration} iteration(s).")
                    
                    if open_pr and branch:
                        git_utils.push_branch(workspace, branch)
                        git_utils.open_pr(workspace, branch)
                    
                    return
                else:
                    # Agent said complete but checkboxes say otherwise
                    state.log_progress(workspace, f"**Session {iteration} ended** - Agent signaled complete but criteria remain")
                    iteration += 1
                    
            elif signal == "ROTATE":
                debug_log(
                    "loop.py:run_ralph_loop",
                    "ROTATE signal received",
                    {
                        "iteration": iteration,
                        "current_provider": provider_name,
                        "current_index_before": provider_rotation.current_index,
                        "will_rotate_provider": False
                    },
                    "A"
                )
                
                state.log_progress(workspace, f"**Session {iteration} ended** - 🔄 Context rotation (token limit reached)")
                print(f"\n🔄 Rotating to fresh context...")
                
                iteration += 1
                debug_log(
                    "loop.py:run_ralph_loop",
                    "After ROTATE - iteration incremented",
                    {
                        "new_iteration": iteration,
                        "provider_unchanged": provider_name,
                        "current_index_after": provider_rotation.current_index
                    },
                    "A"
                )
                
            elif signal == "GUTTER":
                debug_log(
                    "loop.py:run_ralph_loop",
                    "GUTTER signal received",
                    {
                        "iteration": iteration,
                        "current_provider": provider_name,
                        "current_index_before": provider_rotation.current_index
                    },
                    "B"
                )
                
                state.log_progress(workspace, f"**Session {iteration} ended** - 🚨 GUTTER (agent stuck) - {provider_name}")
                print(f"\n🚨 Gutter detected with {provider_name}. Rotating to next provider...")
                
                # Rotate to next provider
                next_provider = provider_rotation.rotate()
                
                next_name = provider_rotation.get_provider_name() if next_provider else None
                debug_log(
                    "loop.py:run_ralph_loop",
                    "After GUTTER rotation",
                    {
                        "iteration": iteration,
                        "old_provider": provider_name,
                        "new_provider": next_name,
                        "current_index_after": provider_rotation.current_index,
                        "next_provider_returned": next_provider is not None,
                        "has_next": provider_rotation.has_next()
                    },
                    "B"
                )
                
                if next_provider and provider_rotation.has_next():
                    print(f"🔄 Rotating to provider: {next_name}")
                    state.log_progress(workspace, f"**Provider rotation** - {provider_name} → {next_name} (gutter)")
                    # Retry same iteration with new provider
                    continue
                else:
                    # No more providers - continue to next iteration
                    print(f"⚠️  No more providers to try. Continuing to next iteration.")
                    iteration += 1
                    continue
                
            else:
                # Agent finished naturally
                if completion_status.startswith("INCOMPLETE:"):
                    remaining = completion_status.split(":")[1]
                    state.log_progress(workspace, f"**Session {iteration} ended** - Agent finished naturally ({remaining} criteria remaining)")
                    print(f"\n📋 Agent finished but {remaining} criteria remaining.")
                    iteration += 1
                    
        except Exception as e:
            debug_log(
                "loop.py:run_ralph_loop",
                "Exception caught - rotating provider",
                {
                    "iteration": iteration,
                    "current_provider": provider_name,
                    "current_index_before": provider_rotation.current_index,
                    "error": str(e)
                },
                "C"
            )
            
            # Provider error - rotate to next provider
            state.log_progress(workspace, f"**Session {iteration} failed** - Provider error: {provider_name} - {e}")
            print(f"\n⚠️  Provider {provider_name} failed: {e}")
            
            # Rotate to next provider
            next_provider = provider_rotation.rotate()
            
            next_name = provider_rotation.get_provider_name() if next_provider else None
            debug_log(
                "loop.py:run_ralph_loop",
                "After exception rotation",
                {
                    "iteration": iteration,
                    "old_provider": provider_name,
                    "new_provider": next_name,
                    "current_index_after": provider_rotation.current_index,
                    "next_provider_returned": next_provider is not None,
                    "has_next": provider_rotation.has_next()
                },
                "C"
            )
            
            if next_provider and provider_rotation.has_next():
                print(f"🔄 Rotating to provider: {next_name}")
                state.log_progress(workspace, f"**Provider rotation** - {provider_name} → {next_name}")
                # Retry same iteration with new provider
                continue
            else:
                # No more providers or only one provider
                print(f"\n❌ All providers exhausted for iteration {iteration}.")
                iteration += 1
                continue
        
        # Brief pause between iterations
        time.sleep(2)
    
    # Max iterations reached
    state.log_progress(workspace, f"**Loop ended** - ⚠️ Max iterations ({max_iterations}) reached")
    print(f"\n⚠️  Max iterations ({max_iterations}) reached.")
    print("   Task may not be complete. Check progress manually.")
    raise Exception(f"Max iterations ({max_iterations}) reached")
