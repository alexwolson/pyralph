"""Helper functions for turn-based interview using conversation file."""

import json
import os
import readline  # Enables up-arrow history in input
import subprocess
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from ralph.ui import THEME

console = Console()

# #region agent log
_DEBUG_LOG_PATH = Path("/Users/alex/repos/pyralph/.cursor/debug.log")
# #endregion


def run_single_turn(
    provider,
    conversation_file: Path,
    project_dir: Path,
) -> tuple[bool, Optional[str]]:
    """Run a single turn: send conversation file to provider, parse response.
    
    Returns: (task_file_created, last_ai_message)
    """
    # #region agent log
    provider_name = provider.get_display_name() if hasattr(provider, 'get_display_name') else provider.cli_tool
    log_entry = {
        "id": f"log_{int(time.time() * 1000)}",
        "timestamp": int(time.time() * 1000),
        "location": "interview_turns.py:28",
        "message": "run_single_turn entry",
        "data": {
            "provider": provider_name,
            "conversation_file": str(conversation_file),
            "conversation_file_exists": conversation_file.exists(),
            "conversation_file_size": conversation_file.stat().st_size if conversation_file.exists() else 0,
            "project_dir": str(project_dir)
        },
        "sessionId": "debug-session",
        "runId": "interview",
        "hypothesisId": "A"
    }
    try:
        with open(_DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
    # #endregion
    
    # Read current conversation
    conversation_text = conversation_file.read_text(encoding="utf-8")
    
    # #region agent log
    log_entry = {
        "id": f"log_{int(time.time() * 1000)}",
        "timestamp": int(time.time() * 1000),
        "location": "interview_turns.py:35",
        "message": "conversation read",
        "data": {
            "provider": provider_name,
            "conversation_length": len(conversation_text),
            "conversation_preview": conversation_text[:200]
        },
        "sessionId": "debug-session",
        "runId": "interview",
        "hypothesisId": "A"
    }
    try:
        with open(_DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
    # #endregion
    
    # Build provider command (use conversation as prompt)
    cmd = provider.get_command(conversation_text, project_dir)
    
    # #region agent log
    log_entry = {
        "id": f"log_{int(time.time() * 1000)}",
        "timestamp": int(time.time() * 1000),
        "location": "interview_turns.py:40",
        "message": "command built",
        "data": {
            "provider": provider_name,
            "cmd": cmd,
            "cmd_string": " ".join(cmd)
        },
        "sessionId": "debug-session",
        "runId": "interview",
        "hypothesisId": "B"
    }
    try:
        with open(_DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
    # #endregion
    
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
    raw_line_count = 0
    parsed_line_count = 0
    stdout_lines = []
    
    while True:
        line = agent_process.stdout.readline()
        if not line:
            if agent_process.poll() is not None:
                break
            continue
        
        raw_line_count += 1
        line_text = line.decode("utf-8", errors="ignore").strip()
        stdout_lines.append(line_text[:200] if len(line_text) > 200 else line_text)
        if not line_text:
            continue
        
        # Parse line using provider adapter
        data = provider.parse_stream_line(line_text)
        if data is None:
            continue
        
        parsed_line_count += 1
        
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
                                title="[bold]🤖 AI Assistant[/bold]",
                                border_style=THEME["primary"],
                                padding=(1, 2),
                            ))
                        
                        last_ai_message = text
                        
                        # Check for completion sigil
                        if "<ralph>DONE</ralph>" in text:
                            task_file_created = True
                            console.print("[green]✅[/green] Interview complete! Task file generated.\n")
        
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
                            console.print(f"[green]✅[/green] RALPH_TASK.md created at {written_file}\n")
    
    # Wait for process
    exit_code = agent_process.wait()
    stderr_output = agent_process.stderr.read().decode("utf-8", errors="ignore")[:500] if agent_process.stderr else ""
    
    # #region agent log
    log_entry = {
        "id": f"log_{int(time.time() * 1000)}",
        "timestamp": int(time.time() * 1000),
        "location": "interview_turns.py:200",
        "message": "process completed",
        "data": {
            "provider": provider_name,
            "exit_code": exit_code,
            "raw_line_count": raw_line_count,
            "parsed_line_count": parsed_line_count,
            "ai_response_parts_count": len(ai_response_parts),
            "task_file_created": task_file_created,
            "has_last_message": last_ai_message is not None,
            "stderr_preview": stderr_output,
            "stdout_sample": stdout_lines[:5] if stdout_lines else []
        },
        "sessionId": "debug-session",
        "runId": "interview",
        "hypothesisId": "C"
    }
    try:
        with open(_DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
    # #endregion
    
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


def append_user_response(conversation_file: Path, user_response: str) -> None:
    """Append user's response to the conversation file."""
    current = conversation_file.read_text(encoding="utf-8")
    conversation_file.write_text(current + "\n\n" + f"User: {user_response}", encoding="utf-8")
