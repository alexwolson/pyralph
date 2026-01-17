"""Integration tests for CLI help and basic functionality."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from ralph.cli import main


class TestCliHelp:
    """Tests for CLI help output."""

    def test_help_flag_shows_help(self) -> None:
        """Test --help flag shows help message."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Ralph Wiggum" in result.output
        assert "Autonomous development loop" in result.output
        assert "--iterations" in result.output
        assert "--branch" in result.output
        assert "--pr" in result.output

    def test_help_shows_project_dir_argument(self) -> None:
        """Test help shows PROJECT_DIR argument."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert "PROJECT_DIR" in result.output


class TestCliValidation:
    """Tests for CLI input validation."""

    def test_requires_project_dir(self) -> None:
        """Test CLI requires PROJECT_DIR argument."""
        runner = CliRunner()

        result = runner.invoke(main, [])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_rejects_nonexistent_directory(self) -> None:
        """Test CLI rejects non-existent directory."""
        runner = CliRunner()

        result = runner.invoke(main, ["/nonexistent/path/that/does/not/exist"])

        assert result.exit_code != 0

    @patch("ralph.cli.git_utils.is_git_repo")
    def test_requires_git_repo(self, mock_is_git_repo: MagicMock, tmp_path: Path) -> None:
        """Test CLI requires directory to be a git repo."""
        mock_is_git_repo.return_value = False
        runner = CliRunner()

        result = runner.invoke(main, [str(tmp_path)])

        assert result.exit_code == 1
        assert "not a git repository" in result.output

    @patch("ralph.cli.git_utils.is_git_repo")
    @patch("ralph.cli.interview.create_task_file")
    @patch("ralph.cli.task.parse_task_file")
    def test_pr_flag_requires_branch(
        self,
        mock_parse: MagicMock,
        mock_interview: MagicMock,
        mock_is_git_repo: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test --pr flag requires --branch to be specified."""
        mock_is_git_repo.return_value = True
        mock_parse.return_value = {"frontmatter": {}, "body": "", "path": tmp_path / "RALPH_TASK.md"}

        # Create task file
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("---\ntask: test\n---\n- [ ] Test")

        runner = CliRunner()

        result = runner.invoke(main, [str(tmp_path), "--pr"])

        assert result.exit_code == 1
        assert "--pr requires --branch" in result.output


class TestCliOptions:
    """Tests for CLI option defaults."""

    def test_default_iterations_is_20(self) -> None:
        """Test default iterations value is 20."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert "default: 20" in result.output.lower() or "[default: 20]" in result.output
