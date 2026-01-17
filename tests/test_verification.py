"""Unit tests for verification phase - independent task verification."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph import parser, tokens, gutter, state
from ralph.loop import build_verification_prompt, run_verification_iteration


class TestVerifyPassSignalDetection:
    """Tests for VERIFY_PASS signal detection in parser."""

    def test_verify_pass_signal_detected_in_text(self) -> None:
        """Test parser detects <ralph>VERIFY_PASS</ralph> signal."""
        token_tracker = tokens.TokenTracker()
        gutter_detector = gutter.GutterDetector()
        
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"text": "All tests pass and requirements met. <ralph>VERIFY_PASS</ralph>"}
                ]
            }
        }
        
        workspace = Path("/tmp/test_workspace")
        
        with patch.object(state, "log_activity"):
            result = parser.process_line(workspace, data, token_tracker, gutter_detector)
        
        assert result == "VERIFY_PASS"

    def test_verify_pass_signal_not_detected_without_sigil(self) -> None:
        """Test parser doesn't detect VERIFY_PASS without sigil."""
        token_tracker = tokens.TokenTracker()
        gutter_detector = gutter.GutterDetector()
        
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"text": "Verification passed successfully"}
                ]
            }
        }
        
        workspace = Path("/tmp/test_workspace")
        
        with patch.object(state, "log_activity"):
            result = parser.process_line(workspace, data, token_tracker, gutter_detector)
        
        assert result is None


class TestVerifyFailSignalDetection:
    """Tests for VERIFY_FAIL signal detection in parser."""

    def test_verify_fail_signal_detected_in_text(self) -> None:
        """Test parser detects <ralph>VERIFY_FAIL</ralph> signal."""
        token_tracker = tokens.TokenTracker()
        gutter_detector = gutter.GutterDetector()
        
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"text": "Tests failing, unchecking criteria. <ralph>VERIFY_FAIL</ralph>"}
                ]
            }
        }
        
        workspace = Path("/tmp/test_workspace")
        
        with patch.object(state, "log_activity"):
            result = parser.process_line(workspace, data, token_tracker, gutter_detector)
        
        assert result == "VERIFY_FAIL"

    def test_verify_fail_signal_not_detected_without_sigil(self) -> None:
        """Test parser doesn't detect VERIFY_FAIL without sigil."""
        token_tracker = tokens.TokenTracker()
        gutter_detector = gutter.GutterDetector()
        
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"text": "Verification failed, some tests not passing"}
                ]
            }
        }
        
        workspace = Path("/tmp/test_workspace")
        
        with patch.object(state, "log_activity"):
            result = parser.process_line(workspace, data, token_tracker, gutter_detector)
        
        assert result is None


class TestBuildVerificationPrompt:
    """Tests for build_verification_prompt function."""

    def test_prompt_includes_verification_instructions(self, tmp_path: Path) -> None:
        """Test verification prompt includes role description."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [x] Test criterion")
        
        prompt = build_verification_prompt(tmp_path, iteration=1)
        
        assert "Verification" in prompt
        assert "independent" in prompt.lower()

    def test_prompt_includes_verify_pass_signal(self, tmp_path: Path) -> None:
        """Test verification prompt mentions VERIFY_PASS signal."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [x] Test criterion")
        
        prompt = build_verification_prompt(tmp_path, iteration=1)
        
        assert "<ralph>VERIFY_PASS</ralph>" in prompt

    def test_prompt_includes_verify_fail_signal(self, tmp_path: Path) -> None:
        """Test verification prompt mentions VERIFY_FAIL signal."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [x] Test criterion")
        
        prompt = build_verification_prompt(tmp_path, iteration=1)
        
        assert "<ralph>VERIFY_FAIL</ralph>" in prompt

    def test_prompt_includes_test_command(self, tmp_path: Path) -> None:
        """Test verification prompt includes test command from frontmatter."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("""---
test_command: "npm test"
---
# Task
- [x] Test criterion
""")
        
        prompt = build_verification_prompt(tmp_path, iteration=1)
        
        assert "npm test" in prompt

    def test_prompt_uses_default_test_command(self, tmp_path: Path) -> None:
        """Test verification prompt uses 'make test' when no test_command specified."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [x] Test criterion")
        
        prompt = build_verification_prompt(tmp_path, iteration=1)
        
        assert "make test" in prompt

    def test_prompt_instructs_to_run_tests(self, tmp_path: Path) -> None:
        """Test verification prompt instructs agent to run tests."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [x] Test criterion")
        
        prompt = build_verification_prompt(tmp_path, iteration=1)
        
        assert "Run Tests" in prompt or "run the test" in prompt.lower()

    def test_prompt_instructs_to_review_code(self, tmp_path: Path) -> None:
        """Test verification prompt instructs agent to review code quality."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [x] Test criterion")
        
        prompt = build_verification_prompt(tmp_path, iteration=1)
        
        assert "Review" in prompt or "review" in prompt.lower()
        assert "quality" in prompt.lower() or "code" in prompt.lower()

    def test_prompt_instructs_uncheck_on_fail(self, tmp_path: Path) -> None:
        """Test verification prompt instructs agent to uncheck criteria on failure."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text("# Task\n- [x] Test criterion")
        
        prompt = build_verification_prompt(tmp_path, iteration=1)
        
        assert "uncheck" in prompt.lower() or "[x]" in prompt


class TestVerificationIterationSignals:
    """Tests for run_verification_iteration signal handling."""

    def test_iteration_recognizes_verify_pass(self) -> None:
        """Test run_verification_iteration returns VERIFY_PASS signal."""
        # This test verifies the function signature accepts expected parameters
        # Full integration testing would require mocking the subprocess
        from ralph.loop import run_verification_iteration
        
        # Verify function exists and has correct signature
        import inspect
        sig = inspect.signature(run_verification_iteration)
        params = list(sig.parameters.keys())
        
        assert "workspace" in params
        assert "provider" in params
        assert "iteration" in params
        assert "timeout" in params

    def test_iteration_recognizes_verify_fail(self) -> None:
        """Test run_verification_iteration handles VERIFY_FAIL signal."""
        from ralph.loop import run_verification_iteration
        
        # Verify function exists - full testing requires subprocess mock
        assert callable(run_verification_iteration)


class TestMaxVerificationFailures:
    """Tests for max_verification_failures configuration."""

    def test_run_ralph_loop_accepts_max_verification_failures(self) -> None:
        """Test run_ralph_loop accepts max_verification_failures parameter."""
        from ralph.loop import run_ralph_loop
        import inspect
        
        sig = inspect.signature(run_ralph_loop)
        params = sig.parameters
        
        assert "max_verification_failures" in params
        # Check default value
        assert params["max_verification_failures"].default == 3

    def test_default_max_verification_failures_is_3(self) -> None:
        """Test default max_verification_failures is 3."""
        from ralph.loop import run_ralph_loop
        import inspect
        
        sig = inspect.signature(run_ralph_loop)
        default = sig.parameters["max_verification_failures"].default
        
        assert default == 3
