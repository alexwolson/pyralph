"""Git utilities for Ralph."""

import subprocess
from pathlib import Path
from typing import Optional


def is_git_repo(directory: Path) -> bool:
    """Check if directory is a git repository."""
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--git-dir"],
            capture_output=True,
            check=True,
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_branch(directory: Path, branch_name: str) -> None:
    """Create and checkout a new branch."""
    try:
        # Try to create branch
        subprocess.run(
            ["git", "-C", str(directory), "checkout", "-b", branch_name],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        # Branch might already exist, try to checkout
        subprocess.run(
            ["git", "-C", str(directory), "checkout", branch_name],
            check=True,
            capture_output=True,
        )


def commit_changes(directory: Path, message: str) -> None:
    """Commit all changes with given message."""
    try:
        # Stage all changes
        subprocess.run(
            ["git", "-C", str(directory), "add", "-A"],
            check=True,
            capture_output=True,
        )
        # Commit
        subprocess.run(
            ["git", "-C", str(directory), "commit", "-m", message],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        # Ignore if nothing to commit
        pass


def has_uncommitted_changes(directory: Path) -> bool:
    """Check if there are uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def push_branch(directory: Path, branch_name: Optional[str] = None) -> None:
    """Push current branch to remote."""
    try:
        if branch_name:
            subprocess.run(
                ["git", "-C", str(directory), "push", "-u", "origin", branch_name],
                check=True,
                capture_output=True,
            )
        else:
            subprocess.run(
                ["git", "-C", str(directory), "push"],
                check=True,
                capture_output=True,
            )
    except subprocess.CalledProcessError:
        # Ignore if push fails (no remote, etc.)
        pass


def open_pr(directory: Path, branch_name: str) -> None:
    """Open a PR using gh CLI if available."""
    try:
        subprocess.run(
            ["gh", "pr", "create", "--fill"],
            cwd=str(directory),
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # gh CLI not available or failed
        pass
