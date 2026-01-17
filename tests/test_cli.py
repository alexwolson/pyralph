"""Integration tests for CLI help, version, and basic functionality."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from ralph.cli import main
from ralph import __version__


class TestCliVersion:
    """Tests for --version flag."""

    def test_version_flag_shows_version(self) -> None:
        """Test --version flag shows version."""
        runner = CliRunner()

        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output
        assert "ralph" in result.output.lower()


class TestCliHelp:
    """Tests for CLI help output."""

    def test_help_flag_shows_help(self) -> None:
        """Test --help flag shows help message."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Ralph Wiggum" in result.output
        assert "Autonomous development loop" in result.output

    def test_shows_available_commands(self) -> None:
        """Test help shows available commands."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert "run" in result.output
        assert "status" in result.output

    def test_shows_verbose_option(self) -> None:
        """Test help shows verbose option."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert "--verbose" in result.output or "-v" in result.output


class TestRunCommandHelp:
    """Tests for run command help."""

    def test_run_help_shows_options(self) -> None:
        """Test run --help shows all options."""
        runner = CliRunner()

        result = runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "--iterations" in result.output
        assert "--branch" in result.output
        assert "--pr" in result.output
        assert "--once" in result.output
        assert "PROJECT_DIR" in result.output


class TestStatusCommandHelp:
    """Tests for status command help."""

    def test_status_help_shows_usage(self) -> None:
        """Test status --help shows usage."""
        runner = CliRunner()

        result = runner.invoke(main, ["status", "--help"])

        assert result.exit_code == 0
        assert "PROJECT_DIR" in result.output
        assert "progress" in result.output.lower()


class TestRunCommandValidation:
    """Tests for run command input validation."""

    def test_run_requires_project_dir(self) -> None:
        """Test run command requires PROJECT_DIR argument."""
        runner = CliRunner()

        result = runner.invoke(main, ["run"])

        assert result.exit_code != 0

    def test_run_rejects_nonexistent_directory(self) -> None:
        """Test run rejects non-existent directory."""
        runner = CliRunner()

        result = runner.invoke(main, ["run", "/nonexistent/path/that/does/not/exist"])

        assert result.exit_code != 0

    @patch("ralph.cli.git_utils.is_git_repo")
    def test_run_requires_git_repo(self, mock_is_git_repo: MagicMock, tmp_path: Path) -> None:
        """Test run requires directory to be a git repo."""
        mock_is_git_repo.return_value = False
        runner = CliRunner()

        result = runner.invoke(main, ["run", str(tmp_path)])

        assert result.exit_code == 1
        assert "not a git repository" in result.output

    @patch("ralph.cli.git_utils.is_git_repo")
    @patch("ralph.cli.interview.create_task_file")
    @patch("ralph.cli.task.parse_task_file")
    def test_run_pr_flag_requires_branch(
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
        task_file.write_text("---\ntask: test\n---\n- [ ] Test", encoding="utf-8")

        runner = CliRunner()

        result = runner.invoke(main, ["run", str(tmp_path), "--pr"])

        assert result.exit_code == 1
        assert "--pr requires --branch" in result.output


class TestStatusCommand:
    """Tests for status command."""

    def test_status_requires_project_dir(self) -> None:
        """Test status command requires PROJECT_DIR argument."""
        runner = CliRunner()

        result = runner.invoke(main, ["status"])

        assert result.exit_code != 0

    @patch("ralph.cli.git_utils.is_git_repo")
    def test_status_requires_git_repo(self, mock_is_git_repo: MagicMock, tmp_path: Path) -> None:
        """Test status requires directory to be a git repo."""
        mock_is_git_repo.return_value = False
        runner = CliRunner()

        result = runner.invoke(main, ["status", str(tmp_path)])

        assert result.exit_code == 1
        assert "not a git repository" in result.output

    @patch("ralph.cli.git_utils.is_git_repo")
    def test_status_requires_task_file(self, mock_is_git_repo: MagicMock, tmp_path: Path) -> None:
        """Test status requires RALPH_TASK.md to exist."""
        mock_is_git_repo.return_value = True
        runner = CliRunner()

        result = runner.invoke(main, ["status", str(tmp_path)])

        assert result.exit_code == 1
        assert "No RALPH_TASK.md found" in result.output

    @patch("ralph.cli.git_utils.is_git_repo")
    @patch("ralph.providers.detect_available_providers")
    def test_status_shows_progress(
        self,
        mock_providers: MagicMock,
        mock_is_git_repo: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test status shows task progress."""
        mock_is_git_repo.return_value = True
        mock_providers.return_value = []

        # Create task file with some criteria
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """---
task: Test task
max_iterations: 10
---

# Task

- [x] First criterion
- [ ] Second criterion
- [ ] Third criterion
""",
            encoding="utf-8",
        )

        runner = CliRunner()

        result = runner.invoke(main, ["status", str(tmp_path)])

        assert result.exit_code == 0
        assert "Test task" in result.output
        assert "1/3" in result.output or "33%" in result.output
        assert "INCOMPLETE" in result.output


class TestVerboseFlag:
    """Tests for verbose flag."""

    def test_verbose_flag_accepted(self) -> None:
        """Test -v flag is accepted."""
        runner = CliRunner()

        # Just test that it doesn't error - we can't easily test the logging output
        result = runner.invoke(main, ["-v", "--help"])

        assert result.exit_code == 0

    def test_verbose_long_flag_accepted(self) -> None:
        """Test --verbose flag is accepted."""
        runner = CliRunner()

        result = runner.invoke(main, ["--verbose", "--help"])

        assert result.exit_code == 0


class TestCliDefaults:
    """Tests for CLI option defaults."""

    def test_default_iterations_is_20(self) -> None:
        """Test default iterations value is 20."""
        runner = CliRunner()

        result = runner.invoke(main, ["run", "--help"])

        assert "default: 20" in result.output.lower() or "[default: 20]" in result.output


class TestThresholdOptions:
    """Tests for threshold CLI options."""

    def test_warn_threshold_option_in_help(self) -> None:
        """Test --warn-threshold option appears in help."""
        runner = CliRunner()

        result = runner.invoke(main, ["run", "--help"])

        assert "--warn-threshold" in result.output
        assert "180000" in result.output  # Default value

    def test_rotate_threshold_option_in_help(self) -> None:
        """Test --rotate-threshold option appears in help."""
        runner = CliRunner()

        result = runner.invoke(main, ["run", "--help"])

        assert "--rotate-threshold" in result.output
        assert "200000" in result.output  # Default value

    def test_timeout_option_in_help(self) -> None:
        """Test --timeout option appears in help."""
        runner = CliRunner()

        result = runner.invoke(main, ["run", "--help"])

        assert "--timeout" in result.output
        assert "300" in result.output  # Default value
