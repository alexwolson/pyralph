"""Archive functions for completed Ralph tasks and state files."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from ralph import git_utils
from ralph.debug import debug_log


def archive_completed_task(workspace: Path) -> Optional[Path]:
    """Archive completed RALPH_TASK.md to .ralph/completed/ with timestamp.
    
    Also archives state files (progress.md, activity.log, errors.log) with
    matching timestamp and resets them to initial state. guardrails.md is
    NOT touched as it contains cross-task learnings.
    
    Args:
        workspace: Project directory path
    
    Returns:
        The path to the archived task file, or None if no task file exists.
        Commits the archive operation to git for state persistence.
    """
    task_file = workspace / "RALPH_TASK.md"
    if not task_file.exists():
        return None
    
    # Create completed directory if needed
    completed_dir = workspace / ".ralph" / "completed"
    completed_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp - used for all archives for correlation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"RALPH_TASK_{timestamp}.md"
    archive_path = completed_dir / archive_name
    
    # Move task file to archive
    task_file.rename(archive_path)
    
    debug_log(
        "archive.py:archive_completed_task",
        "Task archived",
        {"archive_path": str(archive_path)},
    )
    
    # Archive state files with matching timestamp
    _archive_state_files(workspace, timestamp)
    
    # Commit the archive operation to git
    git_utils.commit_changes(
        workspace, 
        f"ralph: archive completed task to {archive_name}"
    )
    
    return archive_path


def _archive_state_files(workspace: Path, timestamp: str) -> None:
    """Archive state files and reset them to initial state.
    
    Archives progress.md, activity.log, and errors.log to .ralph/completed/
    with the provided timestamp for correlation with the task archive.
    Then resets each file to its initial empty state.
    
    Note: guardrails.md is NOT archived as it contains cross-task learnings.
    
    Args:
        workspace: Project directory path
        timestamp: Timestamp string to use in archive filenames
    """
    ralph_dir = workspace / ".ralph"
    completed_dir = ralph_dir / "completed"
    completed_dir.mkdir(parents=True, exist_ok=True)
    
    # Define state files to archive with their initial content
    state_files = {
        "progress.md": (
            "# Progress Log\n\n"
            "> Updated by the agent after significant work.\n\n"
            "---\n\n"
            "## Session History\n\n"
        ),
        "activity.log": (
            "# Activity Log\n\n> Real-time tool call logging from parser.\n\n"
        ),
        "errors.log": (
            "# Error Log\n\n> Failures detected by parser. Use to update guardrails.\n\n"
        ),
    }
    
    archived_files = []
    
    for filename, initial_content in state_files.items():
        source_file = ralph_dir / filename
        
        if source_file.exists():
            # Generate archive name with matching timestamp
            base_name = filename.rsplit(".", 1)[0]  # e.g., "progress" from "progress.md"
            extension = filename.rsplit(".", 1)[1]   # e.g., "md" or "log"
            archive_name = f"{base_name}_{timestamp}.{extension}"
            archive_path = completed_dir / archive_name
            
            # Copy content to archive (don't move, we'll reset in place)
            content = source_file.read_text(encoding="utf-8")
            archive_path.write_text(content, encoding="utf-8")
            
            # Reset to initial state
            source_file.write_text(initial_content, encoding="utf-8")
            
            archived_files.append(archive_name)
            
            debug_log(
                "archive.py:_archive_state_files",
                f"State file archived and reset: {filename}",
                {"archive_path": str(archive_path)},
            )
    
    if archived_files:
        debug_log(
            "archive.py:_archive_state_files",
            "State files archived",
            {"archived_files": archived_files, "timestamp": timestamp},
        )
