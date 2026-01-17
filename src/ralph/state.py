"""State management for Ralph."""

from pathlib import Path
from typing import Optional


# Initial content templates for state files
DEFAULT_PROGRESS_CONTENT = (
    "# Progress Log\n\n"
    "> Updated by the agent after significant work.\n\n"
    "---\n\n"
    "## Session History\n\n"
)

DEFAULT_GUARDRAILS_CONTENT = (
    "# Ralph Guardrails (Signs)\n\n"
    "> Lessons learned from past failures. READ THESE BEFORE ACTING.\n\n"
    "## Core Signs\n\n"
    "### Sign: Read Before Writing\n"
    "- **Trigger**: Before modifying any file\n"
    "- **Instruction**: Always read the existing file first\n"
    "- **Added after**: Core principle\n\n"
    "### Sign: Test After Changes\n"
    "- **Trigger**: After any code change\n"
    "- **Instruction**: Run tests to verify nothing broke\n"
    "- **Added after**: Core principle\n\n"
    "### Sign: Commit Checkpoints\n"
    "- **Trigger**: Before risky changes\n"
    "- **Instruction**: Commit current working state first\n"
    "- **Added after**: Core principle\n\n"
    "---\n\n"
    "## Learned Signs\n\n"
)

DEFAULT_ERRORS_CONTENT = (
    "# Error Log\n\n> Failures detected by parser. Use to update guardrails.\n\n"
)

DEFAULT_ACTIVITY_CONTENT = (
    "# Activity Log\n\n> Real-time tool call logging from parser.\n\n"
)


def init_ralph_dir(workspace: Path) -> Path:
    """Initialize .ralph directory with default files."""
    ralph_dir = workspace / ".ralph"
    ralph_dir.mkdir(exist_ok=True)

    # Initialize progress.md
    progress_file = ralph_dir / "progress.md"
    if not progress_file.exists():
        progress_file.write_text(DEFAULT_PROGRESS_CONTENT, encoding="utf-8")

    # Initialize guardrails.md
    guardrails_file = ralph_dir / "guardrails.md"
    if not guardrails_file.exists():
        guardrails_file.write_text(DEFAULT_GUARDRAILS_CONTENT, encoding="utf-8")

    # Initialize errors.log
    errors_file = ralph_dir / "errors.log"
    if not errors_file.exists():
        errors_file.write_text(DEFAULT_ERRORS_CONTENT, encoding="utf-8")

    # Initialize activity.log
    activity_file = ralph_dir / "activity.log"
    if not activity_file.exists():
        activity_file.write_text(DEFAULT_ACTIVITY_CONTENT, encoding="utf-8")

    return ralph_dir


def get_iteration(workspace: Path) -> int:
    """Get current iteration number."""
    iteration_file = workspace / ".ralph" / ".iteration"
    if iteration_file.exists():
        try:
            return int(iteration_file.read_text(encoding="utf-8").strip())
        except ValueError:
            return 0
    return 0


def set_iteration(workspace: Path, iteration: int) -> None:
    """Set iteration number."""
    iteration_file = workspace / ".ralph" / ".iteration"
    iteration_file.parent.mkdir(parents=True, exist_ok=True)
    iteration_file.write_text(str(iteration), encoding="utf-8")


def log_progress(workspace: Path, message: str) -> None:
    """Log progress to progress.md."""
    from datetime import datetime

    progress_file = workspace / ".ralph" / "progress.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with progress_file.open("a", encoding="utf-8") as f:
        f.write(f"\n### {timestamp}\n")
        f.write(f"{message}\n")


def log_error(workspace: Path, message: str) -> None:
    """Log error to errors.log."""
    from datetime import datetime

    errors_file = workspace / ".ralph" / "errors.log"
    timestamp = datetime.now().strftime("%H:%M:%S")
    with errors_file.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def log_activity(workspace: Path, message: str) -> None:
    """Log activity to activity.log."""
    from datetime import datetime

    activity_file = workspace / ".ralph" / "activity.log"
    timestamp = datetime.now().strftime("%H:%M:%S")
    with activity_file.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def compress_progress_file(
    workspace: Path, 
    max_lines: int = 2000, 
    keep_recent_lines: int = 500
) -> bool:
    """Compress progress.md if it exceeds size limits.
    
    If the file is too large, keeps the header and recent entries,
    removing older entries to reduce file size.
    
    Args:
        workspace: Project directory path
        max_lines: Maximum lines before compression triggers (default 2000)
        keep_recent_lines: Number of recent lines to preserve (default 500)
    
    Returns:
        True if compression occurred, False otherwise
    """
    from datetime import datetime
    
    progress_file = workspace / ".ralph" / "progress.md"
    
    # Check if file exists
    if not progress_file.exists():
        return False
    
    # Read all lines
    try:
        with progress_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        # If we can't read it, skip compression
        log_activity(workspace, f"⚠ Failed to read progress.md for compression: {e}")
        return False
    
    # Check if compression is needed
    total_lines = len(lines)
    
    # Also estimate token count (bytes / 4, where bytes ≈ lines * 100)
    # Compress if either line count or estimated tokens exceed thresholds
    estimated_bytes = total_lines * 100
    estimated_tokens = estimated_bytes // 4
    max_tokens = 20000  # ~20k tokens for progress.md (leaves room for other context)
    
    # Compress if lines exceed threshold OR estimated tokens exceed threshold
    if total_lines <= max_lines and estimated_tokens <= max_tokens:
        return False
    
    # Log that compression will occur
    log_activity(
        workspace,
        f"Compressing progress.md: {total_lines} lines (~{estimated_tokens} tokens) "
        f"exceeds threshold ({max_lines} lines or {max_tokens} tokens)"
    )
    
    # Extract header (everything before first timestamp entry)
    # Look for first line starting with "### " followed by a date pattern
    header_end = 0
    for i, line in enumerate(lines):
        # Check if this looks like a timestamp entry (### YYYY-MM-DD HH:MM:SS)
        if line.startswith("### ") and len(line.strip()) > 10:
            # Check if it matches timestamp pattern (rough check)
            rest = line[4:].strip()
            if len(rest) >= 19 and rest[4] == "-" and rest[7] == "-" and rest[10] == " ":
                header_end = i
                break
    
    # If no timestamp found, keep everything up to "## Session History" or similar
    if header_end == 0:
        for i, line in enumerate(lines):
            if line.strip().startswith("## ") and "Session" in line:
                header_end = i + 1
                break
    
    # If still no header found, keep first 10 lines as header (fallback)
    if header_end == 0:
        header_end = min(10, total_lines)
    
    # Extract header lines
    header_lines = lines[:header_end]
    
    # Get recent lines (last keep_recent_lines)
    # Make sure we don't overlap with header
    if total_lines > keep_recent_lines:
        recent_lines = lines[-keep_recent_lines:]
        # If header and recent lines overlap, adjust
        if header_end > total_lines - keep_recent_lines:
            recent_lines = lines[header_end:]
    else:
        # File is smaller than keep_recent_lines, but we're compressing anyway
        # (edge case - shouldn't happen, but handle it)
        recent_lines = lines[header_end:]
    
    # Build compressed content
    compressed_lines = []
    
    # Add header
    compressed_lines.extend(header_lines)
    
    # Add compression note
    compression_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    compressed_lines.append(f"\n### [Compressed] {compression_timestamp}\n")
    compressed_lines.append("> Older entries compressed to reduce file size. Recent entries preserved above.\n")
    compressed_lines.append("\n")
    
    # Add recent lines
    compressed_lines.extend(recent_lines)
    
    # Write compressed content back
    try:
        with progress_file.open("w", encoding="utf-8") as f:
            f.writelines(compressed_lines)
        
        # Log compression activity
        old_size = total_lines
        new_size = len(compressed_lines)
        log_activity(
            workspace, 
            f"Compressed progress.md: {old_size} → {new_size} lines "
            f"(kept {keep_recent_lines} recent lines)"
        )
        
        return True
    except Exception:
        # If write fails, return False
        return False
