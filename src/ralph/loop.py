"""Main iteration loop for Ralph."""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

from ralph import git_utils, gutter, parser, state, task, tokens
from ralph.debug import debug_log
from ralph.providers import ProviderRotation
from ralph.ui import RalphLiveDisplay, get_criteria_list, display_question_panel

if TYPE_CHECKING:
    from rich.console import Console


def archive_completed_task(workspace: Path) -> Optional[Path]:
    """Archive completed RALPH_TASK.md to .ralph/completed/ with timestamp.
    
    Returns the path to the archived file, or None if no task file exists.
    Commits the archive operation to git for state persistence.
    """
    task_file = workspace / "RALPH_TASK.md"
    if not task_file.exists():
        return None
    
    # Create completed directory if needed
    completed_dir = workspace / ".ralph" / "completed"
    completed_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"RALPH_TASK_{timestamp}.md"
    archive_path = completed_dir / archive_name
    
    # Move task file to archive
    task_file.rename(archive_path)
    
    debug_log(
        "loop.py:archive_completed_task",
        "Task archived",
        {"archive_path": str(archive_path)},
    )
    
    # Commit the archive operation to git
    git_utils.commit_changes(
        workspace, 
        f"ralph: archive completed task to {archive_name}"
    )
    
    return archive_path


def build_verification_prompt(workspace: Path, iteration: int) -> str:
    """Build a verification prompt for an independent agent to verify task completion.
    
    Args:
        workspace: Project directory path
        iteration: Current iteration number
    
    Returns:
        Verification prompt string
    """
    task_file = workspace / "RALPH_TASK.md"
    
    # Read task file to get requirements and test_command
    task_content = task_file.read_text(encoding="utf-8") if task_file.exists() else ""
    
    # Parse frontmatter to get test_command
    test_command = "make test"  # default
    if task_content.startswith("---"):
        import yaml
        import re
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n", task_content, re.DOTALL)
        if frontmatter_match:
            try:
                frontmatter = yaml.safe_load(frontmatter_match.group(1)) or {}
                test_command = frontmatter.get("test_command", "make test")
            except yaml.YAMLError:
                pass
    
    prompt = f"""# Ralph Verification Phase - Iteration {iteration}

You are an independent verification agent. A previous agent claimed to have completed the task. Your job is to verify whether the task is truly complete.

## Your Role

You are NOT the agent who completed the work. You are an independent reviewer who will:
1. Run the test suite to verify all tests pass
2. Review the code changes for quality and completeness
3. Check that ALL requirements in RALPH_TASK.md are actually met
4. Make a final judgment: PASS or FAIL

## Task Being Verified

Read RALPH_TASK.md to see the original task requirements and success criteria.

## Verification Steps

1. **Run Tests**: Execute `{test_command}` to verify all tests pass
2. **Review Code**: Read the modified files to ensure:
   - Code quality is acceptable
   - No obvious bugs or issues
   - Changes match what was required
3. **Check Requirements**: Go through EACH success criterion in RALPH_TASK.md:
   - Is it actually implemented?
   - Does it work correctly?
   - Are there edge cases missed?

## Your Verdict

After verification, output ONE of these signals:

### If ALL requirements are met and tests pass:
Output: `<ralph>VERIFY_PASS</ralph>`

### If ANY requirement is NOT met, tests fail, or quality issues exist:
1. Edit RALPH_TASK.md to uncheck the incomplete criteria (change `[x]` back to `[ ]`)
2. Optionally add new criteria if you discovered missing requirements
3. Write a brief explanation in `.ralph/progress.md` about what failed verification
4. Output: `<ralph>VERIFY_FAIL</ralph>`

## Important

- Be thorough but fair - don't fail for minor style issues
- Focus on functional correctness first
- If tests pass and all criteria are genuinely met, approve it
- If anything is incomplete or broken, fail it and be specific about why

Begin verification by reading RALPH_TASK.md and running the test command.
"""
    return prompt


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
5. After committing, signal for fresh context: output `<ralph>ROTATE</ralph>`
   This ensures each commit checkpoint gets a fresh agent context.

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

## Asking Questions (Use Sparingly)

If you are genuinely stuck and human input would significantly help, you can ask the user a question:

1. Write your question to `.ralph/question.md` (be specific and concise)
2. Output the signal: `<ralph>QUESTION</ralph>`
3. The loop will pause and prompt the user for an answer
4. The user's answer (if any) will be written to `.ralph/answer.md`
5. You can read `.ralph/answer.md` to get the response

**Important**: Use this sparingly - only when you truly need clarification that would significantly change your approach. Most tasks should be completable without asking questions. If the user doesn't respond (timeout), proceed with your best judgment.

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
    on_token_update: Optional[Callable[[tokens.TokenTracker], None]] = None,
    console: Optional["Console"] = None,
) -> str:
    """Run a single iteration. Returns signal (ROTATE, GUTTER, COMPLETE, or empty).
    
    Args:
        workspace: Project directory path
        provider: LLM provider instance
        iteration: Current iteration number
        warn_threshold: Token count at which to warn about context size
        rotate_threshold: Token count at which to trigger rotation
        timeout: Timeout in seconds for provider operations (default 300)
        on_token_update: Optional callback for token tracker updates
        console: Optional Rich Console for output (use Live.console when within Live context)
    """
    
    prompt = build_prompt(workspace, iteration)
    
    # Create token tracker and gutter detector with configurable thresholds
    token_tracker = tokens.TokenTracker(
        warn_threshold=warn_threshold,
        rotate_threshold=rotate_threshold,
    )
    gutter_detector = gutter.GutterDetector()
    
    # Log session start - use display name for user-facing output
    provider_display = provider.get_display_name() if hasattr(provider, 'get_display_name') else provider.cli_tool
    provider_cli = provider.cli_tool if hasattr(provider, 'cli_tool') else str(type(provider).__name__)
    state.log_progress(workspace, f"**Session {iteration} started** (provider: {provider_display})")
    
    # Build provider command with workspace directory
    cmd = provider.get_command(prompt, workspace)
    
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
        for sig in parser.parse_stream(
            workspace, agent_process, token_tracker, gutter_detector, provider,
            on_token_update=on_token_update,
            console=console,
        ):
            signal = sig
            if signal in ("ROTATE", "GUTTER", "COMPLETE", "QUESTION", "VERIFY_PASS", "VERIFY_FAIL"):
                # Stop early if critical signal
                agent_process.terminate()
                break
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                debug_log(
                    "loop.py:run_single_iteration",
                    "Timeout reached - terminating provider",
                    {"timeout": timeout, "elapsed": elapsed, "provider": provider_cli},
                )
                agent_process.terminate()
                signal = "ROTATE"
                break
    except Exception as e:
        debug_log(
            "loop.py:run_single_iteration",
            "Exception during stream parsing",
            {"error": str(e), "provider": provider_cli},
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


def run_verification_iteration(
    workspace: Path,
    provider,
    iteration: int,
    warn_threshold: int,
    rotate_threshold: int,
    timeout: int,
    on_token_update: Optional[Callable[[tokens.TokenTracker], None]] = None,
    console: Optional["Console"] = None,
) -> str:
    """Run a verification iteration. Returns signal (VERIFY_PASS, VERIFY_FAIL, or empty).
    
    Args:
        workspace: Project directory path
        provider: LLM provider instance
        iteration: Current iteration number
        warn_threshold: Token count at which to warn about context size
        rotate_threshold: Token count at which to trigger rotation
        timeout: Timeout in seconds for provider operations
        on_token_update: Optional callback for token tracker updates
        console: Optional Rich Console for output (use Live.console when within Live context)
    """
    prompt = build_verification_prompt(workspace, iteration)
    
    # Create token tracker and gutter detector with configurable thresholds
    token_tracker = tokens.TokenTracker(
        warn_threshold=warn_threshold,
        rotate_threshold=rotate_threshold,
    )
    gutter_detector = gutter.GutterDetector()
    
    # Log verification start
    provider_display = provider.get_display_name() if hasattr(provider, 'get_display_name') else provider.cli_tool
    state.log_progress(workspace, f"**Verification started** (provider: {provider_display})")
    
    # Build provider command with workspace directory
    cmd = provider.get_command(prompt, workspace)
    
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
        for sig in parser.parse_stream(
            workspace, agent_process, token_tracker, gutter_detector, provider,
            on_token_update=on_token_update,
            console=console,
        ):
            signal = sig
            if signal in ("VERIFY_PASS", "VERIFY_FAIL", "ROTATE", "GUTTER"):
                # Stop early if critical signal
                agent_process.terminate()
                break
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                debug_log(
                    "loop.py:run_verification_iteration",
                    "Timeout reached - treating as verification fail",
                    {"timeout": timeout, "elapsed": elapsed},
                )
                agent_process.terminate()
                signal = "VERIFY_FAIL"
                break
    except Exception as e:
        debug_log(
            "loop.py:run_verification_iteration",
            "Exception during verification",
            {"error": str(e)},
        )
        agent_process.terminate()
        signal = "VERIFY_FAIL"
    
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
    max_verification_failures: int = 3,
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
        max_verification_failures: Maximum consecutive verification failures before giving up (default 3)
    """
    # #region agent log
    debug_log_path = Path("/Users/alex/repos/pyralph/.cursor/debug.log")
    try:
        with open(debug_log_path, "a") as f:
            log_entry = {
                "id": f"log_{int(time.time() * 1000)}",
                "timestamp": int(time.time() * 1000),
                "location": "loop.py:239",
                "message": "run_ralph_loop entry",
                "data": {"project_dir": str(project_dir), "max_iterations": max_iterations},
                "sessionId": "debug-session",
                "runId": "ralph-loop",
                "hypothesisId": "A"
            }
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
    # #endregion
    
    from ralph.providers import get_provider_rotation
    
    workspace = project_dir.resolve()
    task_file = workspace / "RALPH_TASK.md"
    
    # #region agent log
    try:
        with open(debug_log_path, "a") as f:
            log_entry = {
                "id": f"log_{int(time.time() * 1000)}",
                "timestamp": int(time.time() * 1000),
                "location": "loop.py:262",
                "message": "task_file path set",
                "data": {"task_file": str(task_file), "exists": task_file.exists()},
                "sessionId": "debug-session",
                "runId": "ralph-loop",
                "hypothesisId": "A"
            }
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
    # #endregion
    
    # Commit any uncommitted work first
    if git_utils.has_uncommitted_changes(workspace):
        git_utils.commit_changes(workspace, "ralph: initial commit before loop")
    
    # Create branch if requested
    if branch:
        git_utils.create_branch(workspace, branch)
    
    # Detect available providers and create rotation manager
    provider_rotation = get_provider_rotation()
    if not provider_rotation.providers:
        raise Exception("No LLM providers available. Please install agent, claude, gemini, or codex.")
    
    # Main loop
    iteration = 1
    verification_failures = 0
    
    from rich.console import Console
    console = Console()
    
    # #region agent log
    try:
        with open(debug_log_path, "a") as f:
            log_entry = {
                "id": f"log_{int(time.time() * 1000)}",
                "timestamp": int(time.time() * 1000),
                "location": "loop.py:322",
                "message": "about to create live display",
                "data": {},
                "sessionId": "debug-session",
                "runId": "ralph-loop",
                "hypothesisId": "C"
            }
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
    # #endregion
    
    # Create live display
    try:
        live_display = RalphLiveDisplay(
            max_iterations=max_iterations,
            rotate_threshold=rotate_threshold,
            console=console,
        )
    except Exception as e:
        # #region agent log
        import traceback
        try:
            with open(debug_log_path, "a") as f:
                log_entry = {
                    "id": f"log_{int(time.time() * 1000)}",
                    "timestamp": int(time.time() * 1000),
                    "location": "loop.py:336",
                    "message": "Exception creating live display",
                    "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()},
                    "sessionId": "debug-session",
                    "runId": "ralph-loop",
                    "hypothesisId": "C"
                }
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass
        # #endregion
        raise
    
    # Callback to update live display with token tracker
    def on_token_update(tracker: tokens.TokenTracker) -> None:
        # Re-read criteria to get latest status
        criteria = get_criteria_list(task_file)
        live_display.update(token_tracker=tracker, criteria=criteria)
    
    with live_display:
        while iteration <= max_iterations:
            # Clean up any leftover question/answer files from previous iteration
            question_file = workspace / ".ralph" / "question.md"
            answer_file = workspace / ".ralph" / "answer.md"
            question_file.unlink(missing_ok=True)
            answer_file.unlink(missing_ok=True)
            
            # Get current provider
            provider = provider_rotation.get_current()
            provider_name = provider_rotation.get_provider_name()
            
            # Update live display
            criteria = get_criteria_list(task_file)
            live_display.update(
                iteration=iteration,
                provider=provider_name,
                criteria=criteria,
            )
            
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
            
            try:
                # Run iteration with token update callback
                # Pass live display's console for proper integration with Live context
                signal = run_single_iteration(
                    workspace, provider, iteration,
                    warn_threshold=warn_threshold,
                    rotate_threshold=rotate_threshold,
                    timeout=timeout,
                    on_token_update=on_token_update,
                    console=live_display.console,
                )
                
                # Check task completion
                completion_status = task.check_completion(task_file)
                
                # Update criteria display after iteration
                criteria = get_criteria_list(task_file)
                live_display.update(criteria=criteria)
                
                # Handle completion - either all checkboxes checked or agent signaled COMPLETE
                should_verify = False
                
                if completion_status == "COMPLETE":
                    # All checkboxes checked - trigger verification
                    should_verify = True
                    state.log_progress(workspace, f"**Session {iteration} ended** - All criteria checked, starting verification")
                
                if signal == "COMPLETE" and completion_status == "COMPLETE":
                    # Agent signaled COMPLETE and all checkboxes checked
                    should_verify = True
                    state.log_progress(workspace, f"**Session {iteration} ended** - Agent signaled COMPLETE, starting verification")
                elif signal == "COMPLETE" and completion_status != "COMPLETE":
                    # Agent said complete but checkboxes say otherwise
                    state.log_progress(workspace, f"**Session {iteration} ended** - Agent signaled complete but criteria remain")
                    iteration += 1
                    continue
                
                if should_verify:
                    # Check if we've exceeded max verification failures
                    if verification_failures >= max_verification_failures:
                        state.log_progress(workspace, f"**Verification skipped** - Max failures ({max_verification_failures}) reached, completing anyway")
                        live_display.stop()
                        console.print(f"\n[yellow]⚠️  Max verification failures ({max_verification_failures}) reached.[/]")
                        console.print(f"[bold green]🎉 RALPH COMPLETE![/] Completing without final verification.")
                        console.print(f"Completed in {iteration} iteration(s).")
                        
                        # Archive completed task
                        archive_path = archive_completed_task(workspace)
                        if archive_path:
                            console.print(f"[dim]📁 Task archived to: {archive_path.relative_to(workspace)}[/]")
                            state.log_progress(workspace, f"**Task archived** to {archive_path.name}")
                        
                        if open_pr and branch:
                            git_utils.push_branch(workspace, branch)
                            git_utils.open_pr(workspace, branch)
                        
                        return
                    
                    # Rotate to a different provider for verification
                    completing_provider_name = provider_rotation.get_provider_name()
                    provider_rotation.rotate()
                    verification_provider = provider_rotation.get_current()
                    verification_provider_name = provider_rotation.get_provider_name()
                    
                    state.log_progress(workspace, f"**Verification phase** - Provider: {completing_provider_name} → {verification_provider_name}")
                    console.print(f"\n[cyan]🔍 Starting verification phase with {verification_provider_name}...[/]")
                    
                    # Update live display for verification
                    live_display.update(
                        iteration=iteration,
                        provider=f"verify:{verification_provider_name}",
                        criteria=criteria,
                    )
                    
                    # Run verification iteration
                    verify_signal = run_verification_iteration(
                        workspace,
                        verification_provider,
                        iteration,
                        warn_threshold=warn_threshold,
                        rotate_threshold=rotate_threshold,
                        timeout=timeout,
                        on_token_update=on_token_update,
                        console=live_display.console,
                    )
                    
                    if verify_signal == "VERIFY_PASS":
                        # Verification passed - archive and exit
                        state.log_progress(workspace, f"**Verification PASSED** - Task complete")
                        live_display.stop()
                        console.print(f"\n[bold green]🎉 RALPH COMPLETE![/] Task verified by independent agent.")
                        console.print(f"Completed in {iteration} iteration(s).")
                        
                        # Archive completed task
                        archive_path = archive_completed_task(workspace)
                        if archive_path:
                            console.print(f"[dim]📁 Task archived to: {archive_path.relative_to(workspace)}[/]")
                            state.log_progress(workspace, f"**Task archived** to {archive_path.name}")
                        
                        if open_pr and branch:
                            git_utils.push_branch(workspace, branch)
                            git_utils.open_pr(workspace, branch)
                        
                        return
                    
                    elif verify_signal == "VERIFY_FAIL":
                        # Verification failed - continue loop
                        verification_failures += 1
                        state.log_progress(workspace, f"**Verification FAILED** ({verification_failures}/{max_verification_failures}) - Continuing loop")
                        console.print(f"[yellow]❌ Verification failed ({verification_failures}/{max_verification_failures}). Continuing...[/]")
                        
                        # Re-read criteria after verification agent may have unchecked some
                        criteria = get_criteria_list(task_file)
                        live_display.update(criteria=criteria)
                        
                        iteration += 1
                        continue
                    
                    else:
                        # Unexpected signal or timeout - treat as verification failure
                        verification_failures += 1
                        state.log_progress(workspace, f"**Verification inconclusive** ({verification_failures}/{max_verification_failures}) - Signal: {verify_signal}")
                        console.print(f"[yellow]⚠️  Verification inconclusive (signal: {verify_signal}). Treating as failure.[/]")
                        iteration += 1
                        continue
                        
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
                        state.log_progress(workspace, f"**Provider rotation** - {provider_name} → {next_name} (gutter)")
                        # Retry same iteration with new provider
                        continue
                    else:
                        # No more providers - continue to next iteration
                        iteration += 1
                        continue
                
                elif signal == "QUESTION":
                    # Handle agent question - pause, display, prompt user
                    from ralph.interview_turns import wait_for_user_input_with_timeout
                    
                    debug_log(
                        "loop.py:run_ralph_loop",
                        "QUESTION signal received",
                        {"iteration": iteration, "provider": provider_name},
                    )
                    
                    # Pause live display during user interaction
                    live_display.stop()
                    
                    # Read question from file
                    question_file = workspace / ".ralph" / "question.md"
                    answer_file = workspace / ".ralph" / "answer.md"
                    
                    if question_file.exists():
                        question_text = question_file.read_text(encoding="utf-8")
                        
                        # Display question with Rich panel
                        display_question_panel(console, question_text)
                        
                        state.log_activity(workspace, f"❓ QUESTION: {question_text[:100]}...")
                        state.log_progress(workspace, f"**Agent asked question** (iteration {iteration})")
                        
                        # Prompt user for answer with timeout
                        user_answer = wait_for_user_input_with_timeout(timeout=60)
                        
                        if user_answer:
                            # Write answer to file
                            answer_file.write_text(user_answer, encoding="utf-8")
                            state.log_activity(workspace, f"✅ User answered: {user_answer[:100]}...")
                            console.print(f"[green]✓[/] Answer saved to .ralph/answer.md")
                        else:
                            # No answer (timeout or skipped) - write empty marker
                            answer_file.write_text("", encoding="utf-8")
                            state.log_activity(workspace, "⏱️ No user answer (timeout or skipped)")
                        
                        # Clean up question file after answer written
                        question_file.unlink(missing_ok=True)
                    else:
                        console.print(f"[yellow]⚠️  Agent signaled QUESTION but no question.md found[/]")
                        state.log_activity(workspace, "⚠️ QUESTION signal but no question.md file")
                    
                    # Restart live display and continue same iteration
                    # Agent will read answer.md on next turn
                    live_display.start()
                    iteration += 1
                    continue
                    
                else:
                    # Agent finished naturally
                    if completion_status.startswith("INCOMPLETE:"):
                        remaining = completion_status.split(":")[1]
                        state.log_progress(workspace, f"**Session {iteration} ended** - Agent finished naturally ({remaining} criteria remaining)")
                        iteration += 1
                        
            except Exception as e:
                # #region agent log
                import traceback
                error_traceback = traceback.format_exc()
                debug_log_path = Path("/Users/alex/repos/pyralph/.cursor/debug.log")
                try:
                    with open(debug_log_path, "a") as f:
                        log_entry = {
                            "id": f"log_{int(time.time() * 1000)}",
                            "timestamp": int(time.time() * 1000),
                            "location": "loop.py:458",
                            "message": "Exception caught in loop",
                            "data": {
                                "iteration": iteration,
                                "current_provider": provider_name,
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "traceback": error_traceback
                            },
                            "sessionId": "debug-session",
                            "runId": "ralph-loop",
                            "hypothesisId": "B"
                        }
                        f.write(json.dumps(log_entry) + "\n")
                except Exception:
                    pass
                # #endregion
                
                debug_log(
                    "loop.py:run_ralph_loop",
                    "Exception caught - rotating provider",
                    {
                        "iteration": iteration,
                        "current_provider": provider_name,
                        "current_index_before": provider_rotation.current_index,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "traceback": error_traceback
                    },
                    "C"
                )
                
                # Provider error - rotate to next provider
                state.log_progress(workspace, f"**Session {iteration} failed** - Provider error: {provider_name} - {e}")
                
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
                    state.log_progress(workspace, f"**Provider rotation** - {provider_name} → {next_name}")
                    # Retry same iteration with new provider
                    continue
                else:
                    # No more providers or only one provider
                    iteration += 1
                    continue
            
            # Brief pause between iterations
            time.sleep(2)
    
    # Max iterations reached
    state.log_progress(workspace, f"**Loop ended** - ⚠️ Max iterations ({max_iterations}) reached")
    console.print(f"\n[yellow]⚠️  Max iterations ({max_iterations}) reached.[/]")
    console.print("   Task may not be complete. Check progress manually.")
    raise Exception(f"Max iterations ({max_iterations}) reached")
