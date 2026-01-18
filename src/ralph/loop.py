"""Main iteration loop for Ralph."""

import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Set, TYPE_CHECKING

from ralph import git_utils, gutter, parser, state, task, tokens
from ralph.archive import archive_completed_task
from ralph.debug import debug_log
from ralph.prompts import build_prompt, build_verification_prompt
from ralph.providers import ProviderRotation
from ralph.signals import Signal, CRITICAL_SIGNALS, VERIFICATION_SIGNALS
from ralph.ui import RalphLiveDisplay, get_criteria_list, display_question_panel

if TYPE_CHECKING:
    from rich.console import Console


def _run_iteration_core(
    workspace: Path,
    provider,
    prompt: str,
    log_message: str,
    stop_signals: Set[str],
    timeout_signal: str,
    warn_threshold: int,
    rotate_threshold: int,
    timeout: int,
    on_token_update: Optional[Callable[[tokens.TokenTracker], None]] = None,
    on_task_file_update: Optional[Callable[[Path], None]] = None,
    console: Optional["Console"] = None,
    reraise_exceptions: bool = True,
) -> str:
    """Core iteration logic shared between regular and verification iterations.
    
    Args:
        workspace: Project directory path
        provider: LLM provider instance
        prompt: The prompt to send to the provider
        log_message: Message to log at start (e.g., "Session 1 started" or "Verification started")
        stop_signals: Set of signals that should stop the iteration early
        timeout_signal: Signal to return on timeout
        warn_threshold: Token count at which to warn about context size
        rotate_threshold: Token count at which to trigger rotation
        timeout: Timeout in seconds for provider operations
        on_token_update: Optional callback for token tracker updates
        on_task_file_update: Optional callback for task file updates
        console: Optional Rich Console for output
        reraise_exceptions: If True, re-raise exceptions; if False, return timeout_signal
    
    Returns:
        Signal string from the iteration
    """
    # Create token tracker and gutter detector with configurable thresholds
    token_tracker = tokens.TokenTracker(
        warn_threshold=warn_threshold,
        rotate_threshold=rotate_threshold,
    )
    gutter_detector = gutter.GutterDetector()
    
    # Log session start - use display name for user-facing output
    provider_display = provider.get_display_name()
    provider_cli = provider.cli_tool if hasattr(provider, 'cli_tool') else str(type(provider).__name__)
    state.log_progress(workspace, f"**{log_message}** (provider: {provider_display})")
    
    # Build provider command with workspace directory
    cmd = provider.get_command(prompt, workspace)
    
    # #region agent log
    import json
    import os
    try:
        log_dir = "/Users/alex/repos/pyralph/.cursor"
        os.makedirs(log_dir, exist_ok=True)
        log_path = f"{log_dir}/debug.log"
        provider_cli = provider.get_cli_tool_name() if hasattr(provider, 'get_cli_tool_name') else str(type(provider).__name__)
        entry_log = {
            "id": f"log_{int(time.time())}_entry",
            "timestamp": int(time.time() * 1000),
            "location": "loop.py:_run_iteration_core:69",
            "message": "About to start subprocess",
            "data": {"log_message": log_message, "provider": provider_cli, "cmd": cmd},
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A"
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(entry_log) + "\n")
    except Exception:
        pass
    # #endregion
    
    # Start agent process
    agent_process = None
    try:
        agent_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(workspace),
            text=False,
        )
    except Exception as e:
        # #region agent log
        import json
        import os
        try:
            log_dir = "/Users/alex/repos/pyralph/.cursor"
            os.makedirs(log_dir, exist_ok=True)
            log_path = f"{log_dir}/debug.log"
            provider_cli = provider.get_cli_tool_name() if hasattr(provider, 'get_cli_tool_name') else str(type(provider).__name__)
            error_log = {
                "id": f"log_{int(time.time())}_popen_error",
                "timestamp": int(time.time() * 1000),
                "location": "loop.py:_run_iteration_core:72",
                "message": "Subprocess.Popen failed",
                "data": {"error": str(e), "error_type": type(e).__name__, "cmd": cmd, "provider": provider_cli},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(error_log) + "\n")
        except Exception:
            pass
        # #endregion
        if reraise_exceptions:
            raise
        return timeout_signal
    
    # Send prompt
    agent_process.stdin.write(prompt.encode("utf-8"))
    agent_process.stdin.close()
    
    # Track start time for timeout
    start_time = time.time()
    
    # Set up timeout thread to terminate process if timeout is exceeded
    timeout_timer = None
    if timeout:
        def timeout_handler():
            try:
                agent_process.terminate()
            except Exception:
                pass
        timeout_timer = threading.Timer(timeout, timeout_handler)
        timeout_timer.start()
    
    # Parse stream with timeout checking
    signal = ""
    try:
        for sig in parser.parse_stream(
            workspace, agent_process, token_tracker, gutter_detector, provider,
            on_token_update=on_token_update,
            on_task_file_update=on_task_file_update,
            console=console,
        ):
            signal = sig
            if signal in stop_signals:
                # Stop early if critical signal
                agent_process.terminate()
                break
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                debug_log(
                    "loop.py:_run_iteration_core",
                    "Timeout reached",
                    {"timeout": timeout, "elapsed": elapsed, "provider": provider_cli},
                )
                agent_process.terminate()
                signal = timeout_signal
                break
    except Exception as e:
        # #region agent log
        import json
        import os
        import traceback
        try:
            log_dir = "/Users/alex/repos/pyralph/.cursor"
            os.makedirs(log_dir, exist_ok=True)
            log_path = f"{log_dir}/debug.log"
            provider_cli = provider.get_cli_tool_name() if hasattr(provider, 'get_cli_tool_name') else str(type(provider).__name__)
            error_log = {
                "id": f"log_{int(time.time())}_parse_exception",
                "timestamp": int(time.time() * 1000),
                "location": "loop.py:_run_iteration_core:180",
                "message": "Exception during stream parsing",
                "data": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "provider": provider_cli,
                },
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(error_log) + "\n")
        except Exception:
            pass
        # #endregion
        debug_log(
            "loop.py:_run_iteration_core",
            "Exception during stream parsing",
            {"error": str(e), "provider": provider_cli},
        )
        agent_process.terminate()
        if reraise_exceptions:
            raise
        signal = timeout_signal
    finally:
        # Cancel timeout timer if it's still running
        if timeout_timer:
            timeout_timer.cancel()
    
    # Check if timeout was the reason for termination (no signal received)
    if not signal and timeout and (time.time() - start_time) >= timeout:
        signal = timeout_signal
    
    # Wait for process to finish with timeout
    try:
        agent_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        agent_process.kill()
        agent_process.wait()
    
    # #region agent log
    import json
    import os
    try:
        log_dir = "/Users/alex/repos/pyralph/.cursor"
        os.makedirs(log_dir, exist_ok=True)
        log_path = f"{log_dir}/debug.log"
        returncode = agent_process.returncode
        
        # Read stderr - this may have been partially consumed, try to read what's left
        stderr_bytes = b""
        try:
            if agent_process.stderr:
                remaining_stderr = agent_process.stderr.read()
                if remaining_stderr:
                    stderr_bytes = remaining_stderr
        except Exception:
            pass  # stderr may already be closed
        
        stderr_text = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
        
        # Also try to read any remaining stdout that wasn't consumed by parse_stream
        stdout_bytes = b""
        try:
            if agent_process.stdout:
                # Try to peek/read any remaining data (though parse_stream should have consumed it)
                pass  # stdout is typically consumed by parse_stream, but log if there's anything
        except Exception:
            pass
        
        log_entry = {
            "id": f"log_{int(time.time())}_{id(agent_process)}",
            "timestamp": int(time.time() * 1000),
            "location": "loop.py:_run_iteration_core:229",
            "message": "Process completed - checking returncode and stderr",
            "data": {
                "returncode": returncode,
                "signal": signal,
                "stderr_length": len(stderr_text),
                "stderr_full": stderr_text,  # Log full stderr, not just preview
                "provider": provider_cli,
            },
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A"
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Also persist exact stderr to a user-facing file (even if empty)
        try:
            ralph_dir = workspace / ".ralph"
            ralph_dir.mkdir(exist_ok=True)
            cli_output_file = ralph_dir / "cli_output.log"
            with cli_output_file.open("a", encoding="utf-8") as f_out:
                f_out.write("\n" + "=" * 80 + "\n")
                f_out.write(
                    f"[{time.strftime('%H:%M:%S')}] provider={provider_cli} stream=stderr returncode={returncode} signal={signal}\n"
                )
                f_out.write("=" * 80 + "\n")
                f_out.write(stderr_text)
                f_out.write("\n")
        except Exception:
            pass
    except Exception as e:
        # #region agent log
        import json
        import os
        try:
            log_dir = "/Users/alex/repos/pyralph/.cursor"
            os.makedirs(log_dir, exist_ok=True)
            log_path = f"{log_dir}/debug.log"
            error_log = {
                "id": f"log_{int(time.time())}_error",
                "timestamp": int(time.time() * 1000),
                "location": "loop.py:_run_iteration_core:151",
                "message": "Exception in instrumentation",
                "data": {"error": str(e), "error_type": type(e).__name__},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(error_log) + "\n")
        except Exception:
            pass
        # #endregion
    # #endregion
    
    # Check process returncode - if non-zero and no signal received, treat as failure
    returncode = agent_process.returncode
    if returncode is not None and returncode != 0 and not signal:
        # Process exited with error but no signal was emitted - treat as failure
        # For verification iterations, use VERIFY_FAIL; for regular, use timeout_signal
        state.log_activity(workspace, f"⚠ Process exited with returncode {returncode} but no signal received")
        if timeout_signal == Signal.VERIFY_FAIL:
            signal = Signal.VERIFY_FAIL
        else:
            signal = timeout_signal
    
    return signal


def run_single_iteration(
    workspace: Path, 
    provider,
    iteration: int,
    warn_threshold: int = tokens.WARN_THRESHOLD,
    rotate_threshold: int = tokens.ROTATE_THRESHOLD,
    timeout: int = 300,
    on_token_update: Optional[Callable[[tokens.TokenTracker], None]] = None,
    on_task_file_update: Optional[Callable[[Path], None]] = None,
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
        on_task_file_update: Optional callback for task file updates
        console: Optional Rich Console for output (use Live.console when within Live context)
    """
    prompt = build_prompt(workspace, iteration)
    
    return _run_iteration_core(
        workspace=workspace,
        provider=provider,
        prompt=prompt,
        log_message=f"Session {iteration} started",
        stop_signals=CRITICAL_SIGNALS,
        timeout_signal=Signal.ROTATE,
        warn_threshold=warn_threshold,
        rotate_threshold=rotate_threshold,
        timeout=timeout,
        on_token_update=on_token_update,
        on_task_file_update=on_task_file_update,
        console=console,
        reraise_exceptions=True,
    )


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
    
    return _run_iteration_core(
        workspace=workspace,
        provider=provider,
        prompt=prompt,
        log_message="Verification started",
        stop_signals=VERIFICATION_SIGNALS,
        timeout_signal=Signal.VERIFY_FAIL,
        warn_threshold=warn_threshold,
        rotate_threshold=rotate_threshold,
        timeout=timeout,
        on_token_update=on_token_update,
        on_task_file_update=None,  # Verification doesn't track task file updates
        console=console,
        reraise_exceptions=False,
    )


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
    from ralph.providers import get_provider_rotation
    
    workspace = project_dir.resolve()
    task_file = workspace / "RALPH_TASK.md"
    
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
    
    # Create live display
    try:
        live_display = RalphLiveDisplay(
            max_iterations=max_iterations,
            rotate_threshold=rotate_threshold,
            console=console,
        )
    except Exception:
        raise
    
    # Callback to update live display with token tracker
    def on_token_update(tracker: tokens.TokenTracker) -> None:
        # Re-read criteria to get latest status
        criteria = get_criteria_list(task_file)
        live_display.update(token_tracker=tracker, criteria=criteria)
    
    # Callback to update criteria display when RALPH_TASK.md is written
    def on_task_file_update(file_path: Path) -> None:
        # Re-read criteria and update display immediately
        criteria = get_criteria_list(file_path)
        live_display.update(criteria=criteria)
    
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
                    on_task_file_update=on_task_file_update,
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
                
                if signal == Signal.COMPLETE and completion_status == "COMPLETE":
                    # Agent signaled COMPLETE and all checkboxes checked
                    should_verify = True
                    state.log_progress(workspace, f"**Session {iteration} ended** - Agent signaled COMPLETE, starting verification")
                elif signal == Signal.COMPLETE and completion_status != "COMPLETE":
                    # Agent said complete but checkboxes say otherwise
                    state.log_progress(workspace, f"**Session {iteration} ended** - Agent signaled complete but criteria remain")
                    iteration += 1
                    continue
                
                if should_verify:
                    # Check if we've exceeded max verification failures
                    if verification_failures >= max_verification_failures:
                        state.log_progress(workspace, f"**Verification skipped** - Max failures ({max_verification_failures}) reached, completing anyway")
                        live_display.stop()
                        console.print(f"\n[yellow]⚠ Max verification failures ({max_verification_failures}) reached.[/]")
                        console.print(f"[bold green]✓ RALPH COMPLETE![/] Completing without final verification.")
                        console.print(f"Completed in {iteration} iteration(s).")
                        
                        # Archive completed task
                        archive_path = archive_completed_task(workspace)
                        if archive_path:
                            console.print(f"[dim]Task archived to: {archive_path.relative_to(workspace)}[/]")
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
                    console.print(f"\n[cyan]Starting verification phase with {verification_provider_name}...[/]")
                    
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
                    
                    if verify_signal == Signal.VERIFY_PASS:
                        # Verification passed - archive and exit
                        state.log_progress(workspace, f"**Verification PASSED** - Task complete")
                        live_display.stop()
                        console.print(f"\n[bold green]✓ RALPH COMPLETE![/] Task verified by independent agent.")
                        console.print(f"Completed in {iteration} iteration(s).")
                        
                        # Archive completed task
                        archive_path = archive_completed_task(workspace)
                        if archive_path:
                            console.print(f"[dim]Task archived to: {archive_path.relative_to(workspace)}[/]")
                            state.log_progress(workspace, f"**Task archived** to {archive_path.name}")
                        
                        if open_pr and branch:
                            git_utils.push_branch(workspace, branch)
                            git_utils.open_pr(workspace, branch)
                        
                        return
                    
                    elif verify_signal == Signal.VERIFY_FAIL:
                        # Verification failed - continue loop
                        verification_failures += 1
                        state.log_progress(workspace, f"**Verification FAILED** ({verification_failures}/{max_verification_failures}) - Continuing loop")
                        console.print(f"[yellow]✗ Verification failed ({verification_failures}/{max_verification_failures}). Continuing...[/]")
                        
                        # Re-read criteria after verification agent may have unchecked some
                        criteria = get_criteria_list(task_file)
                        live_display.update(criteria=criteria)
                        
                        iteration += 1
                        continue
                    
                    else:
                        # Unexpected signal or timeout - treat as verification failure
                        verification_failures += 1
                        state.log_progress(workspace, f"**Verification inconclusive** ({verification_failures}/{max_verification_failures}) - Signal: {verify_signal}")
                        console.print(f"[yellow]⚠ Verification inconclusive (signal: {verify_signal}). Treating as failure.[/]")
                        iteration += 1
                        continue
                        
                elif signal == Signal.ROTATE:
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
                    
                    state.log_progress(workspace, f"**Session {iteration} ended** - ↻ Context rotation (token limit reached)")
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
                    
                elif signal == Signal.GUTTER:
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
                    
                    state.log_progress(workspace, f"**Session {iteration} ended** - ⚠ GUTTER (agent stuck) - {provider_name}")
                    
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
                
                elif signal == Signal.QUESTION:
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
                        
                        state.log_activity(workspace, f"? QUESTION: {question_text[:100]}...")
                        state.log_progress(workspace, f"**Agent asked question** (iteration {iteration})")
                        
                        # Prompt user for answer with timeout
                        user_answer = wait_for_user_input_with_timeout(timeout=60)
                        
                        if user_answer:
                            # Write answer to file
                            answer_file.write_text(user_answer, encoding="utf-8")
                            state.log_activity(workspace, f"✓ User answered: {user_answer[:100]}...")
                            console.print(f"[green]✓[/] Answer saved to .ralph/answer.md")
                        else:
                            # No answer (timeout or skipped) - write empty marker
                            answer_file.write_text("", encoding="utf-8")
                            state.log_activity(workspace, "Timeout: No user answer (timeout or skipped)")
                        
                        # Clean up question file after answer written
                        question_file.unlink(missing_ok=True)
                    else:
                        console.print(f"[yellow]⚠ Agent signaled QUESTION but no question.md found[/]")
                        state.log_activity(workspace, "⚠ QUESTION signal but no question.md file")
                    
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
                import traceback
                error_traceback = traceback.format_exc()

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
    state.log_progress(workspace, f"**Loop ended** - ⚠ Max iterations ({max_iterations}) reached")
    console.print(f"\n[yellow]⚠ Max iterations ({max_iterations}) reached.[/]")
    console.print("   Task may not be complete. Check progress manually.")
    raise Exception(f"Max iterations ({max_iterations}) reached")
