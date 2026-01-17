"""Unit tests for git_utils.py - mocked subprocess calls."""

from pathlib import Path
from unittest.mock import MagicMock, patch, call
import subprocess

import pytest

from ralph.git_utils import (
    is_git_repo,
    create_branch,
    commit_changes,
    has_uncommitted_changes,
    push_branch,
    open_pr,
)


class TestIsGitRepo:
    """Tests for is_git_repo function."""

    @patch("subprocess.run")
    def test_returns_true_for_git_repo(self, mock_run: MagicMock) -> None:
        """Test returns True for valid git repository."""
        mock_run.return_value = MagicMock(returncode=0)

        result = is_git_repo(Path("/some/repo"))

        assert result is True
        mock_run.assert_called_once()
        assert "rev-parse" in mock_run.call_args[0][0]

    @patch("subprocess.run")
    def test_returns_false_for_non_git_directory(self, mock_run: MagicMock) -> None:
        """Test returns False for non-git directory."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = is_git_repo(Path("/not/a/repo"))

        assert result is False

    @patch("subprocess.run")
    def test_returns_false_when_git_not_installed(self, mock_run: MagicMock) -> None:
        """Test returns False when git is not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = is_git_repo(Path("/some/path"))

        assert result is False


class TestCreateBranch:
    """Tests for create_branch function."""

    @patch("subprocess.run")
    def test_creates_new_branch(self, mock_run: MagicMock) -> None:
        """Test creates and checks out new branch."""
        mock_run.return_value = MagicMock(returncode=0)

        create_branch(Path("/repo"), "feature-branch")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "checkout" in call_args
        assert "-b" in call_args
        assert "feature-branch" in call_args

    @patch("subprocess.run")
    def test_checks_out_existing_branch(self, mock_run: MagicMock) -> None:
        """Test checks out existing branch if creation fails."""
        # First call (create) fails, second call (checkout) succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "git"),
            MagicMock(returncode=0),
        ]

        create_branch(Path("/repo"), "existing-branch")

        assert mock_run.call_count == 2
        # Second call should be checkout without -b
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "checkout" in second_call_args
        assert "-b" not in second_call_args


class TestCommitChanges:
    """Tests for commit_changes function."""

    @patch("subprocess.run")
    def test_stages_and_commits(self, mock_run: MagicMock) -> None:
        """Test stages all changes and commits."""
        mock_run.return_value = MagicMock(returncode=0)

        commit_changes(Path("/repo"), "Test commit message")

        assert mock_run.call_count == 2
        # First call: git add -A
        first_call = mock_run.call_args_list[0][0][0]
        assert "add" in first_call
        assert "-A" in first_call
        # Second call: git commit -m
        second_call = mock_run.call_args_list[1][0][0]
        assert "commit" in second_call
        assert "-m" in second_call
        assert "Test commit message" in second_call

    @patch("subprocess.run")
    def test_handles_nothing_to_commit(self, mock_run: MagicMock) -> None:
        """Test handles case when there's nothing to commit."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Should not raise exception
        commit_changes(Path("/repo"), "Message")


class TestHasUncommittedChanges:
    """Tests for has_uncommitted_changes function."""

    @patch("subprocess.run")
    def test_returns_true_with_changes(self, mock_run: MagicMock) -> None:
        """Test returns True when there are uncommitted changes."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=" M file.py\n?? new_file.py\n"
        )

        result = has_uncommitted_changes(Path("/repo"))

        assert result is True

    @patch("subprocess.run")
    def test_returns_false_without_changes(self, mock_run: MagicMock) -> None:
        """Test returns False when working tree is clean."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = has_uncommitted_changes(Path("/repo"))

        assert result is False

    @patch("subprocess.run")
    def test_returns_false_on_error(self, mock_run: MagicMock) -> None:
        """Test returns False on git error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = has_uncommitted_changes(Path("/repo"))

        assert result is False


class TestPushBranch:
    """Tests for push_branch function."""

    @patch("subprocess.run")
    def test_pushes_named_branch(self, mock_run: MagicMock) -> None:
        """Test pushes named branch with upstream tracking."""
        mock_run.return_value = MagicMock(returncode=0)

        push_branch(Path("/repo"), "feature-branch")

        call_args = mock_run.call_args[0][0]
        assert "push" in call_args
        assert "-u" in call_args
        assert "origin" in call_args
        assert "feature-branch" in call_args

    @patch("subprocess.run")
    def test_pushes_current_branch(self, mock_run: MagicMock) -> None:
        """Test pushes current branch without specifying name."""
        mock_run.return_value = MagicMock(returncode=0)

        push_branch(Path("/repo"))

        call_args = mock_run.call_args[0][0]
        assert "push" in call_args
        assert "-u" not in call_args

    @patch("subprocess.run")
    def test_handles_push_failure(self, mock_run: MagicMock) -> None:
        """Test handles push failure gracefully."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Should not raise exception
        push_branch(Path("/repo"), "branch")


class TestOpenPr:
    """Tests for open_pr function."""

    @patch("subprocess.run")
    def test_opens_pr_with_gh_cli(self, mock_run: MagicMock) -> None:
        """Test opens PR using gh CLI."""
        mock_run.return_value = MagicMock(returncode=0)

        open_pr(Path("/repo"), "feature-branch")

        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "pr" in call_args
        assert "create" in call_args

    @patch("subprocess.run")
    def test_handles_gh_not_installed(self, mock_run: MagicMock) -> None:
        """Test handles gh CLI not being installed."""
        mock_run.side_effect = FileNotFoundError()

        # Should not raise exception
        open_pr(Path("/repo"), "branch")

    @patch("subprocess.run")
    def test_handles_pr_creation_failure(self, mock_run: MagicMock) -> None:
        """Test handles PR creation failure gracefully."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "gh")

        # Should not raise exception
        open_pr(Path("/repo"), "branch")
