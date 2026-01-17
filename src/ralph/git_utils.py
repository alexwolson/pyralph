"""Git utilities for Ralph."""

import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ralph")

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds


def _run_git_with_retry(
    args: list[str],
    cwd: str,
    capture_output: bool = True,
    check: bool = True,
    text: bool = False,
) -> subprocess.CompletedProcess:
    """Run a git command with retry logic and exponential backoff.
    
    Args:
        args: Command arguments (e.g., ["git", "-C", "/path", "status"])
        cwd: Working directory
        capture_output: Capture stdout/stderr
        check: Raise exception on non-zero exit
        text: Return output as text instead of bytes
        
    Returns:
        CompletedProcess result
        
    Raises:
        subprocess.CalledProcessError: If command fails after all retries
    """
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            result = subprocess.run(
                args,
                capture_output=capture_output,
                check=check,
                text=text,
                cwd=cwd,
            )
            return result
        except subprocess.CalledProcessError as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                backoff = INITIAL_BACKOFF * (2 ** attempt)
                logger.debug(
                    f"Git command failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                    f"retrying in {backoff}s: {' '.join(args)}"
                )
                time.sleep(backoff)
            else:
                logger.debug(
                    f"Git command failed after {MAX_RETRIES} attempts: {' '.join(args)}"
                )
    
    # Re-raise the last exception if all retries failed
    if last_exception:
        raise last_exception
    
    # This should never happen, but satisfy type checker
    raise RuntimeError("Unexpected state in git retry logic")


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
        # Try to create branch with retry
        _run_git_with_retry(
            ["git", "-C", str(directory), "checkout", "-b", branch_name],
            cwd=str(directory),
        )
    except subprocess.CalledProcessError:
        # Branch might already exist, try to checkout
        _run_git_with_retry(
            ["git", "-C", str(directory), "checkout", branch_name],
            cwd=str(directory),
        )


def commit_changes(directory: Path, message: str) -> None:
    """Commit all changes with given message."""
    try:
        # Stage all changes with retry
        _run_git_with_retry(
            ["git", "-C", str(directory), "add", "-A"],
            cwd=str(directory),
        )
        # Commit with retry
        _run_git_with_retry(
            ["git", "-C", str(directory), "commit", "-m", message],
            cwd=str(directory),
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
            _run_git_with_retry(
                ["git", "-C", str(directory), "push", "-u", "origin", branch_name],
                cwd=str(directory),
            )
        else:
            _run_git_with_retry(
                ["git", "-C", str(directory), "push"],
                cwd=str(directory),
            )
    except subprocess.CalledProcessError:
        # Ignore if push fails (no remote, etc.)
        logger.debug(f"Push failed for {directory}")


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
        logger.debug("gh CLI not available or PR creation failed")
