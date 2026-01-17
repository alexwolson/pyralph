"""State management for Ralph."""

from pathlib import Path
from typing import Optional


def init_ralph_dir(workspace: Path) -> Path:
    """Initialize .ralph directory with default files."""
    ralph_dir = workspace / ".ralph"
    ralph_dir.mkdir(exist_ok=True)

    # Initialize progress.md
    progress_file = ralph_dir / "progress.md"
    if not progress_file.exists():
        progress_file.write_text(
            "# Progress Log\n\n"
            "> Updated by the agent after significant work.\n\n"
            "---\n\n"
            "## Session History\n\n"
        )

    # Initialize guardrails.md
    guardrails_file = ralph_dir / "guardrails.md"
    if not guardrails_file.exists():
        guardrails_file.write_text(
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

    # Initialize errors.log
    errors_file = ralph_dir / "errors.log"
    if not errors_file.exists():
        errors_file.write_text("# Error Log\n\n> Failures detected by parser. Use to update guardrails.\n\n")

    # Initialize activity.log
    activity_file = ralph_dir / "activity.log"
    if not activity_file.exists():
        activity_file.write_text("# Activity Log\n\n> Real-time tool call logging from parser.\n\n")

    return ralph_dir


def get_iteration(workspace: Path) -> int:
    """Get current iteration number."""
    iteration_file = workspace / ".ralph" / ".iteration"
    if iteration_file.exists():
        try:
            return int(iteration_file.read_text().strip())
        except ValueError:
            return 0
    return 0


def set_iteration(workspace: Path, iteration: int) -> None:
    """Set iteration number."""
    iteration_file = workspace / ".ralph" / ".iteration"
    iteration_file.parent.mkdir(parents=True, exist_ok=True)
    iteration_file.write_text(str(iteration))


def log_progress(workspace: Path, message: str) -> None:
    """Log progress to progress.md."""
    from datetime import datetime

    progress_file = workspace / ".ralph" / "progress.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with progress_file.open("a") as f:
        f.write(f"\n### {timestamp}\n")
        f.write(f"{message}\n")


def log_error(workspace: Path, message: str) -> None:
    """Log error to errors.log."""
    from datetime import datetime

    errors_file = workspace / ".ralph" / "errors.log"
    timestamp = datetime.now().strftime("%H:%M:%S")
    with errors_file.open("a") as f:
        f.write(f"[{timestamp}] {message}\n")


def log_activity(workspace: Path, message: str) -> None:
    """Log activity to activity.log."""
    from datetime import datetime

    activity_file = workspace / ".ralph" / "activity.log"
    timestamp = datetime.now().strftime("%H:%M:%S")
    with activity_file.open("a") as f:
        f.write(f"[{timestamp}] {message}\n")
