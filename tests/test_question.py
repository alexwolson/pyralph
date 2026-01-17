"""Unit tests for question mechanism - agent-to-user question/answer."""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph.interview_turns import wait_for_user_input_with_timeout
from ralph.loop import build_prompt
from ralph.ui import display_question_panel


class TestQuestionSignalDetection:
    """Tests for QUESTION signal detection in parser."""

    def test_question_signal_detected_in_text(self) -> None:
        """Test parser detects <ralph>QUESTION</ralph> signal."""
        from ralph import parser, tokens, gutter, state
        
        # Create a mock token tracker and gutter detector
        token_tracker = tokens.TokenTracker()
        gutter_detector = gutter.GutterDetector()
        
        # Create test data with QUESTION signal
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"text": "I have a question. <ralph>QUESTION</ralph>"}
                ]
            }
        }
        
        # Mock workspace
        workspace = Path("/tmp/test_workspace")
        
        # Patch state functions to avoid file writes
        with patch.object(state, "log_activity"):
            result = parser.process_line(workspace, data, token_tracker, gutter_detector)
        
        assert result == "QUESTION"

    def test_question_signal_not_detected_without_sigil(self) -> None:
        """Test parser doesn't detect QUESTION without sigil."""
        from ralph import parser, tokens, gutter, state
        
        token_tracker = tokens.TokenTracker()
        gutter_detector = gutter.GutterDetector()
        
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"text": "I have a question but no sigil"}
                ]
            }
        }
        
        workspace = Path("/tmp/test_workspace")
        
        with patch.object(state, "log_activity"):
            result = parser.process_line(workspace, data, token_tracker, gutter_detector)
        
        assert result is None


class TestDisplayQuestionPanel:
    """Tests for question panel display."""

    def test_display_question_panel_calls_print(self) -> None:
        """Test display_question_panel prints panel to console."""
        from rich.console import Console
        
        console = Console(file=io.StringIO(), force_terminal=True)
        
        question_text = "What database should I use?"
        display_question_panel(console, question_text)
        
        output = console.file.getvalue()
        assert "Agent Question" in output or "question" in output.lower()

    def test_display_question_panel_shows_question_text(self) -> None:
        """Test display_question_panel shows the question content."""
        from rich.console import Console
        
        console = Console(file=io.StringIO(), force_terminal=True)
        
        question_text = "What database should I use?"
        display_question_panel(console, question_text)
        
        output = console.file.getvalue()
        assert "database" in output


class TestWaitForUserInputWithTimeout:
    """Tests for wait_for_user_input_with_timeout function."""

    @patch("select.select")
    @patch("sys.stdin")
    def test_returns_input_when_available(self, mock_stdin, mock_select) -> None:
        """Test returns user input when available before timeout."""
        mock_select.return_value = ([mock_stdin], [], [])
        mock_stdin.readline.return_value = "postgresql\n"
        
        with patch("ralph.interview_turns.console"):
            result = wait_for_user_input_with_timeout(timeout=60)
        
        assert result == "postgresql"

    @patch("select.select")
    def test_returns_none_on_timeout(self, mock_select) -> None:
        """Test returns None when timeout reached."""
        mock_select.return_value = ([], [], [])  # No input ready
        
        with patch("ralph.interview_turns.console"):
            result = wait_for_user_input_with_timeout(timeout=1)
        
        assert result is None

    @patch("select.select")
    @patch("sys.stdin")
    def test_returns_none_for_empty_input(self, mock_stdin, mock_select) -> None:
        """Test returns None when user enters empty string."""
        mock_select.return_value = ([mock_stdin], [], [])
        mock_stdin.readline.return_value = "\n"  # Empty input
        
        with patch("ralph.interview_turns.console"):
            result = wait_for_user_input_with_timeout(timeout=60)
        
        assert result is None

    @patch("select.select")
    def test_returns_none_on_keyboard_interrupt(self, mock_select) -> None:
        """Test returns None on keyboard interrupt."""
        mock_select.side_effect = KeyboardInterrupt()
        
        with patch("ralph.interview_turns.console"):
            result = wait_for_user_input_with_timeout(timeout=60)
        
        assert result is None


class TestBuildPromptQuestionInstructions:
    """Tests for question mechanism instructions in build_prompt."""

    def test_prompt_includes_question_section(self, tmp_path: Path) -> None:
        """Test build_prompt includes question mechanism section."""
        # Create minimal required files
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [ ] Test criterion")
        
        ralph_dir = tmp_path / ".ralph"
        ralph_dir.mkdir()
        (ralph_dir / "guardrails.md").write_text("# Guardrails")
        (ralph_dir / "progress.md").write_text("# Progress")
        (ralph_dir / "errors.log").write_text("")
        
        prompt = build_prompt(tmp_path, iteration=1)
        
        assert "Asking Questions" in prompt

    def test_prompt_mentions_question_file(self, tmp_path: Path) -> None:
        """Test build_prompt mentions .ralph/question.md."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [ ] Test criterion")
        
        ralph_dir = tmp_path / ".ralph"
        ralph_dir.mkdir()
        (ralph_dir / "guardrails.md").write_text("# Guardrails")
        (ralph_dir / "progress.md").write_text("# Progress")
        (ralph_dir / "errors.log").write_text("")
        
        prompt = build_prompt(tmp_path, iteration=1)
        
        assert ".ralph/question.md" in prompt

    def test_prompt_mentions_answer_file(self, tmp_path: Path) -> None:
        """Test build_prompt mentions .ralph/answer.md."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [ ] Test criterion")
        
        ralph_dir = tmp_path / ".ralph"
        ralph_dir.mkdir()
        (ralph_dir / "guardrails.md").write_text("# Guardrails")
        (ralph_dir / "progress.md").write_text("# Progress")
        (ralph_dir / "errors.log").write_text("")
        
        prompt = build_prompt(tmp_path, iteration=1)
        
        assert ".ralph/answer.md" in prompt

    def test_prompt_mentions_question_signal(self, tmp_path: Path) -> None:
        """Test build_prompt mentions <ralph>QUESTION</ralph> signal."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [ ] Test criterion")
        
        ralph_dir = tmp_path / ".ralph"
        ralph_dir.mkdir()
        (ralph_dir / "guardrails.md").write_text("# Guardrails")
        (ralph_dir / "progress.md").write_text("# Progress")
        (ralph_dir / "errors.log").write_text("")
        
        prompt = build_prompt(tmp_path, iteration=1)
        
        assert "<ralph>QUESTION</ralph>" in prompt

    def test_prompt_emphasizes_sparse_usage(self, tmp_path: Path) -> None:
        """Test build_prompt emphasizes using questions sparingly."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [ ] Test criterion")
        
        ralph_dir = tmp_path / ".ralph"
        ralph_dir.mkdir()
        (ralph_dir / "guardrails.md").write_text("# Guardrails")
        (ralph_dir / "progress.md").write_text("# Progress")
        (ralph_dir / "errors.log").write_text("")
        
        prompt = build_prompt(tmp_path, iteration=1)
        
        assert "sparingly" in prompt.lower()
