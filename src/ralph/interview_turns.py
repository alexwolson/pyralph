"""Helper functions for turn-based interview using conversation file."""

import readline  # Enables up-arrow history in input
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from ralph.ui import THEME

console = Console()


def run_single_turn(
    provider,
    conversation_file: Path,
    project_dir: Path,
) -> tuple[bool, Optional[str]]:
    """Run a single turn: send conversation file to provider, parse response.
    
    Returns: (task_file_created, last_ai_message)
    """
    # Read current conversation
    conversation_text = conversation_file.read_text(encoding="utf-8")
    
    # Build provider command (use conversation as prompt)
    cmd = provider.get_command(conversation_text, project_dir)
    
    # Run provider with conversation file as stdin
    agent_process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(project_dir),
        text=False,
    )
    
    # Send conversation to stdin and close
    agent_process.stdin.write(conversation_text.encode("utf-8"))
    agent_process.stdin.close()
    
    # Parse output stream
    last_ai_message = None
    task_file_created = False
    ai_response_parts = []
    
    while True:
        line = agent_process.stdout.readline()
        if not line:
            if agent_process.poll() is not None:
                break
            continue
        
        line_text = line.decode("utf-8", errors="ignore").strip()
        if not line_text:
            continue
        
        # Parse line using provider adapter
        data = provider.parse_stream_line(line_text)
        if data is None:
            continue
        
        msg_type = data.get("type", "")
        subtype = data.get("subtype", "")
        
        # Collect assistant messages
        if msg_type == "assistant":
            content = data.get("message", {}).get("content", [])
            if content and isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        text = item["text"]
                        ai_response_parts.append(text)
                        
                        # Display to user with styled panel and markdown rendering
                        if text.strip():
                            console.print()
                            console.print(Panel(
                                Markdown(text),
                                title="[bold cyan]AI Assistant[/]",
                                border_style=THEME["primary"],
                                padding=(1, 2),
                            ))
                        
                        last_ai_message = text
                        
                        # Check for completion sigil
                        if "<ralph>DONE</ralph>" in text:
                            task_file_created = True
                            console.print("[green]✓[/green] Interview complete! Task file generated.\n")
        
        # Detect task file write via tool call
        elif msg_type == "tool_call" and subtype == "completed":
            tool_call = data.get("tool_call", {})
            write_tool = tool_call.get("writeToolCall")
            
            if write_tool:
                result = write_tool.get("result", {})
                success = result.get("success")
                if success:
                    path = write_tool.get("args", {}).get("path", "")
                    if "RALPH_TASK.md" in path:
                        if path.startswith("/"):
                            written_file = Path(path)
                        else:
                            written_file = project_dir / path
                        
                        if written_file.exists() and written_file.name == "RALPH_TASK.md":
                            task_file_created = True
                            console.print(f"[green]✓[/green] RALPH_TASK.md created at {written_file}\n")
    
    # Wait for process
    agent_process.wait()
    
    # Append AI response to conversation file if we got one
    if ai_response_parts:
        ai_response = "\n\n".join(ai_response_parts)
        current_conversation = conversation_file.read_text(encoding="utf-8")
        conversation_file.write_text(current_conversation + "\n\n" + ai_response, encoding="utf-8")
    
    return task_file_created, last_ai_message


def wait_for_user_input() -> str:
    """Wait for user to type a response and return it.
    
    Uses rich.prompt.Prompt for styled input with readline history support
    (up-arrow to recall previous responses within the session).
    """
    try:
        console.print()  # Add spacing
        user_input = Prompt.ask(
            f"[bold {THEME['accent']}]Your response[/]",
            console=console,
        )
        return user_input
    except (EOFError, KeyboardInterrupt):
        return ""


def wait_for_user_input_with_timeout(timeout: int = 60) -> Optional[str]:
    """Wait for user input with a timeout.
    
    Args:
        timeout: Seconds to wait for input (default 60)
        
    Returns:
        User's input string, or None if timeout reached or cancelled.
    """
    import select
    import sys
    
    console.print()  # Add spacing
    console.print(f"[{THEME['muted']}]You have {timeout} seconds to respond (press Enter to skip)...[/]")
    console.print(f"[bold {THEME['accent']}]Your answer:[/] ", end="")
    
    try:
        # Use select to implement timeout on stdin
        # This works on Unix-like systems
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        
        if rlist:
            # Input available
            user_input = sys.stdin.readline().strip()
            return user_input if user_input else None
        else:
            # Timeout reached
            console.print()  # New line after timeout
            console.print(f"[{THEME['warning']}]Timeout reached - continuing without answer[/]")
            return None
            
    except (EOFError, KeyboardInterrupt):
        console.print()  # New line after interrupt
        return None
    except Exception:
        # select may not work on Windows - fall back to blocking input
        # with a warning
        console.print(f"[{THEME['warning']}]Note: timeout not supported on this platform[/]")
        try:
            user_input = input().strip()
            return user_input if user_input else None
        except (EOFError, KeyboardInterrupt):
            return None


def append_user_response(conversation_file: Path, user_response: str) -> None:
    """Append user's response to the conversation file."""
    current = conversation_file.read_text(encoding="utf-8")
    conversation_file.write_text(current + "\n\n" + f"User: {user_response}", encoding="utf-8")
