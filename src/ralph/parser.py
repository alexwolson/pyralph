"""Stream parser for LLM provider output."""

import subprocess
import time
from pathlib import Path
from typing import Callable, Iterator, Optional

from rich.console import Console

from ralph import gutter, state, tokens
from ralph.providers.base import BaseProvider

# Default console for standalone usage (not within Live context)
_default_console = Console()


def parse_stream(
    workspace: Path,
    agent_process: subprocess.Popen,
    token_tracker: tokens.TokenTracker,
    gutter_detector: gutter.GutterDetector,
    provider: BaseProvider,
    on_token_update: Optional[Callable[[tokens.TokenTracker], None]] = None,
    on_task_file_update: Optional[Callable[[Path], None]] = None,
    console: Optional[Console] = None,
) -> Iterator[str]:
    """Parse cursor-agent stream-json output and emit signals.
    
    Args:
        workspace: Project directory path
        agent_process: The running agent subprocess
        token_tracker: Token usage tracker
        gutter_detector: Gutter (stuck agent) detector
        provider: LLM provider instance
        on_token_update: Optional callback for token tracker updates
        console: Optional Rich Console for output (use Live.console when within Live context)
    
    Yields: "ROTATE", "WARN", "GUTTER", "COMPLETE", "QUESTION", "VERIFY_PASS", "VERIFY_FAIL"
    """
    # Use provided console or default
    output_console = console or _default_console
    
    # Initialize activity log
    from datetime import datetime
    
    state.log_activity(workspace, "═══════════════════════════════════════════════════════════════")
    state.log_activity(workspace, f"Ralph Session Started: {datetime.now()}")

    last_token_log = int(time.time())

    # Read line by line from agent stdout
    while True:
        line = agent_process.stdout.readline()
        if not line:
            # Process ended
            break

        line = line.decode("utf-8", errors="ignore").strip()
        if not line:
            continue

        # Parse line using provider adapter
        data = provider.parse_stream_line(line)
        if data is None:
            continue

        signal = process_line(
            workspace, data, token_tracker, gutter_detector, provider,
            on_task_file_update=on_task_file_update,
            console=output_console,
        )
        if signal:
            yield signal

        # Call token update callback if provided
        if on_token_update:
            on_token_update(token_tracker)

        # Check thresholds
        if token_tracker.should_rotate():
            tokens_count = token_tracker.calculate_tokens()
            state.log_activity(workspace, f"ROTATE: Token threshold reached ({tokens_count} >= {tokens.ROTATE_THRESHOLD})")
            output_console.print(f"[yellow]↻ Token limit reached ({tokens_count} tokens) - rotating...[/yellow]")
            yield "ROTATE"
        
        if token_tracker.should_warn():
            tokens_count = token_tracker.calculate_tokens()
            state.log_activity(workspace, f"WARN: Approaching token limit ({tokens_count} >= {tokens.WARN_THRESHOLD})")
            output_console.print(f"[yellow]⚠ Approaching token limit: {tokens_count}/{tokens.ROTATE_THRESHOLD} tokens[/yellow]")
            yield "WARN"

        # Log token status every 30 seconds
        now = int(time.time())
        if now - last_token_log >= 30:
            log_token_status(workspace, token_tracker, console_output=True, console=output_console)
            last_token_log = now

    # Final token status
    log_token_status(workspace, token_tracker, console=output_console)
    
    # Log session end
    tokens_used = token_tracker.calculate_tokens()
    state.log_activity(workspace, f"SESSION END: ~{tokens_used} tokens used")


def process_line(
    workspace: Path,
    data: dict,
    token_tracker: tokens.TokenTracker,
    gutter_detector: gutter.GutterDetector,
    provider: BaseProvider,
    on_task_file_update: Optional[Callable[[Path], None]] = None,
    console: Optional[Console] = None,
) -> Optional[str]:
    """Process a single JSON line from stream. Returns signal if any.
    
    Args:
        workspace: Project directory path
        data: Parsed JSON data from stream line
        token_tracker: Token usage tracker
        gutter_detector: Gutter (stuck agent) detector
        console: Optional Rich Console for output (use Live.console when within Live context)
    """
    # Use provided console or default
    output_console = console or _default_console
    
    msg_type = data.get("type", "")
    subtype = data.get("subtype", "")

    if msg_type == "system" and subtype == "init":
        provider_name = provider.get_display_name()
        state.log_activity(workspace, f"SESSION START: provider={provider_name}")
        output_console.print(f"[dim]Agent started (provider: {provider_name})[/dim]")

    elif msg_type == "assistant":
        # Track assistant message
        content = data.get("message", {}).get("content", [])
        if content and isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    token_tracker.add_assistant(len(text))
                    
                    # Check for completion sigil
                    if "<ralph>COMPLETE</ralph>" in text:
                        state.log_activity(workspace, "✓ Agent signaled COMPLETE")
                        output_console.print("[green]✓ Agent signaled COMPLETE[/green]")
                        return "COMPLETE"
                    
                    # Check for gutter sigil
                    if "<ralph>GUTTER</ralph>" in text:
                        state.log_activity(workspace, "⚠ Agent signaled GUTTER (stuck)")
                        output_console.print("[yellow]⚠ Agent signaled GUTTER (stuck)[/yellow]")
                        return "GUTTER"
                    
                    # Check for question sigil
                    if "<ralph>QUESTION</ralph>" in text:
                        state.log_activity(workspace, "? Agent has a question for user")
                        output_console.print("[cyan]? Agent has a question for user[/cyan]")
                        return "QUESTION"
                    
                    # Check for verification pass sigil
                    if "<ralph>VERIFY_PASS</ralph>" in text:
                        state.log_activity(workspace, "✓ Verification PASSED")
                        output_console.print("[green]✓ Verification PASSED[/green]")
                        return "VERIFY_PASS"
                    
                    # Check for verification fail sigil
                    if "<ralph>VERIFY_FAIL</ralph>" in text:
                        state.log_activity(workspace, "✗ Verification FAILED")
                        output_console.print("[red]✗ Verification FAILED[/red]")
                        return "VERIFY_FAIL"

    elif msg_type == "tool_call":
        if subtype == "started":
            # Tool call started, nothing to track yet
            pass

        elif subtype == "completed":
            # Handle read tool
            tool_call = data.get("tool_call", {})
            
            # Read tool
            read_tool = tool_call.get("readToolCall")
            if read_tool:
                result = read_tool.get("result", {})
                success = result.get("success")
                if success:
                    path = read_tool.get("args", {}).get("path", "unknown")
                    lines = success.get("totalLines", 0)
                    content_size = success.get("contentSize", 0)
                    
                    if content_size > 0:
                        bytes_count = content_size
                    else:
                        bytes_count = lines * 100  # ~100 chars/line
                    
                    token_tracker.add_read(bytes_count)
                    
                    kb = bytes_count / 1024
                    health_symbol = token_tracker.get_health_symbol()
                    health_indicator = token_tracker.get_health_emoji()
                    state.log_activity(workspace, f"{health_symbol} READ {path} ({lines} lines, ~{kb:.1f}KB)")
                    # Show progress in console
                    output_console.print(f"[dim]Reading {path} ({lines} lines)[/dim]")

            # Write tool
            write_tool = tool_call.get("writeToolCall")
            if write_tool:
                result = write_tool.get("result", {})
                success = result.get("success")
                if success:
                    path = write_tool.get("args", {}).get("path", "unknown")
                    lines = success.get("linesCreated", 0)
                    bytes_count = success.get("fileSize", 0)
                    
                    token_tracker.add_write(bytes_count)
                    
                    kb = bytes_count / 1024
                    health_symbol = token_tracker.get_health_symbol()
                    health_indicator = token_tracker.get_health_emoji()
                    state.log_activity(workspace, f"{health_symbol} WRITE {path} ({lines} lines, {kb:.1f}KB)")
                    # Show progress in console
                    output_console.print(f"[cyan]Writing {path} ({lines} lines)[/cyan]")
                    
                    # Check if RALPH_TASK.md was written and trigger real-time criteria update
                    if on_task_file_update and path == "RALPH_TASK.md":
                        task_file_path = workspace / "RALPH_TASK.md"
                        on_task_file_update(task_file_path)
                    
                    # Track for thrashing detection
                    if gutter_detector.track_write(path):
                        state.log_error(workspace, f"⚠ THRASHING: {path} written 5x in 10 min")
                        return "GUTTER"

            # Shell tool
            shell_tool = tool_call.get("shellToolCall")
            if shell_tool:
                result = shell_tool.get("result", {})
                cmd = shell_tool.get("args", {}).get("command", "unknown")
                exit_code = result.get("exitCode", 0)
                
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                output_chars = len(stdout) + len(stderr)
                
                token_tracker.add_shell_output(output_chars)
                
                health_symbol = token_tracker.get_health_symbol()
                health_indicator = token_tracker.get_health_emoji()
                if exit_code == 0:
                    if output_chars > 1024:
                        state.log_activity(workspace, f"{health_symbol} SHELL {cmd} → exit 0 ({output_chars} chars output)")
                        output_console.print(f"[dim]Running: {cmd} → exit 0 ({output_chars} chars)[/dim]")
                    else:
                        state.log_activity(workspace, f"{health_symbol} SHELL {cmd} → exit 0")
                        output_console.print(f"[dim]Running: {cmd}[/dim]")
                else:
                    state.log_activity(workspace, f"{health_symbol} SHELL {cmd} → exit {exit_code}")
                    state.log_error(workspace, f"SHELL FAIL: {cmd} → exit {exit_code}")
                    output_console.print(f"[yellow]⚠ {health_indicator} Command failed: {cmd} → exit {exit_code}[/yellow]")
                    
                    # Track for failure detection
                    if gutter_detector.track_failure(cmd, exit_code):
                        state.log_error(workspace, f"⚠ GUTTER: same command failed 3x")
                        return "GUTTER"

    return None


def log_token_status(
    workspace: Path,
    token_tracker: tokens.TokenTracker,
    console_output: bool = False,
    console: Optional[Console] = None,
) -> None:
    """Log token status to activity.log and optionally console.
    
    Args:
        workspace: Project directory path
        token_tracker: Token usage tracker
        console_output: Whether to print to console (default False)
        console: Optional Rich Console for output (use Live.console when within Live context)
    """
    import time
    
    # Use provided console or default
    output_console = console or _default_console
    
    tokens_count = token_tracker.calculate_tokens()
    pct = (tokens_count * 100) // tokens.ROTATE_THRESHOLD
    health_symbol = token_tracker.get_health_symbol()
    health_indicator = token_tracker.get_health_emoji()
    timestamp = time.strftime("%H:%M:%S")
    
    status_msg = f"TOKENS: {tokens_count} / {tokens.ROTATE_THRESHOLD} ({pct}%)"
    
    if pct >= 90:
        status_msg += " - rotation imminent"
    elif pct >= 72:
        status_msg += " - approaching limit"
    
    breakdown = (
        f"[read:{token_tracker.bytes_read//1024}KB "
        f"write:{token_tracker.bytes_written//1024}KB "
        f"assist:{token_tracker.assistant_chars//1024}KB "
        f"shell:{token_tracker.shell_output_chars//1024}KB]"
    )
    
    log_line = f"{health_symbol} {status_msg} {breakdown}"
    state.log_activity(workspace, log_line)
    
    if console_output:
        # Use Rich markup version for console
        console_line = f"{health_indicator} {status_msg} {breakdown}"
        output_console.print(f"[dim]{timestamp} {console_line}[/dim]")
