"""Unit tests for gutter.py - failure tracking, write thrashing detection."""

import time
from unittest.mock import patch

import pytest

from ralph.gutter import GutterDetector


class TestGutterDetector:
    """Tests for GutterDetector class."""

    def test_initial_state(self) -> None:
        """Test initial gutter detector state."""
        detector = GutterDetector()

        assert len(detector.failures) == 0
        assert len(detector.writes) == 0


class TestFailureTracking:
    """Tests for command failure tracking."""

    def test_track_failure_returns_false_on_first_failure(self) -> None:
        """Test first failure doesn't trigger gutter."""
        detector = GutterDetector()

        result = detector.track_failure("npm test", 1)

        assert result is False

    def test_track_failure_returns_false_on_second_failure(self) -> None:
        """Test second failure doesn't trigger gutter."""
        detector = GutterDetector()

        detector.track_failure("npm test", 1)
        result = detector.track_failure("npm test", 1)

        assert result is False

    def test_track_failure_returns_true_on_third_failure(self) -> None:
        """Test third failure of same command triggers gutter."""
        detector = GutterDetector()

        detector.track_failure("npm test", 1)
        detector.track_failure("npm test", 1)
        result = detector.track_failure("npm test", 1)

        assert result is True

    def test_track_failure_counts_separately_by_command(self) -> None:
        """Test different commands are tracked separately."""
        detector = GutterDetector()

        # Fail "npm test" twice
        detector.track_failure("npm test", 1)
        detector.track_failure("npm test", 1)

        # Fail "npm build" once - should not trigger gutter
        result = detector.track_failure("npm build", 1)

        assert result is False

    def test_track_failure_ignores_success(self) -> None:
        """Test successful commands (exit code 0) are not tracked."""
        detector = GutterDetector()

        # Success doesn't count
        result = detector.track_failure("npm test", 0)

        assert result is False
        assert detector.failures["npm test"] == 0

    def test_track_failure_counts_after_success(self) -> None:
        """Test failures still count after success."""
        detector = GutterDetector()

        detector.track_failure("npm test", 1)  # Fail
        detector.track_failure("npm test", 0)  # Success - ignored
        detector.track_failure("npm test", 1)  # Fail
        result = detector.track_failure("npm test", 1)  # Fail - 3rd

        assert result is True


class TestWriteThrashing:
    """Tests for write thrashing detection."""

    def test_track_write_returns_false_on_first_write(self) -> None:
        """Test first write doesn't trigger gutter."""
        detector = GutterDetector()

        result = detector.track_write("/path/to/file.py")

        assert result is False

    def test_track_write_returns_false_under_threshold(self) -> None:
        """Test writes under 5 don't trigger gutter."""
        detector = GutterDetector()

        for _ in range(4):
            result = detector.track_write("/path/to/file.py")

        assert result is False

    def test_track_write_returns_true_at_threshold(self) -> None:
        """Test 5th write to same file triggers gutter."""
        detector = GutterDetector()

        for _ in range(4):
            detector.track_write("/path/to/file.py")

        result = detector.track_write("/path/to/file.py")

        assert result is True

    def test_track_write_counts_separately_by_file(self) -> None:
        """Test different files are tracked separately."""
        detector = GutterDetector()

        # Write to file A 4 times
        for _ in range(4):
            detector.track_write("/path/to/file_a.py")

        # Write to file B once - should not trigger gutter
        result = detector.track_write("/path/to/file_b.py")

        assert result is False

    @patch("time.time")
    def test_track_write_expires_after_10_minutes(self, mock_time) -> None:
        """Test writes expire after 10 minutes."""
        detector = GutterDetector()

        # First write at time 0
        mock_time.return_value = 0
        detector.track_write("/path/to/file.py")
        detector.track_write("/path/to/file.py")
        detector.track_write("/path/to/file.py")
        detector.track_write("/path/to/file.py")

        # 11 minutes later (660 seconds)
        mock_time.return_value = 660
        # This should be the 1st write in the window, not the 5th
        result = detector.track_write("/path/to/file.py")

        assert result is False

    @patch("time.time")
    def test_track_write_counts_within_window(self, mock_time) -> None:
        """Test writes within 10 minute window are counted."""
        detector = GutterDetector()

        # Writes spread over 9 minutes
        mock_time.return_value = 0
        detector.track_write("/path/to/file.py")
        mock_time.return_value = 180  # 3 minutes
        detector.track_write("/path/to/file.py")
        mock_time.return_value = 300  # 5 minutes
        detector.track_write("/path/to/file.py")
        mock_time.return_value = 420  # 7 minutes
        detector.track_write("/path/to/file.py")
        mock_time.return_value = 540  # 9 minutes
        result = detector.track_write("/path/to/file.py")

        assert result is True


class TestReset:
    """Tests for reset functionality."""

    def test_reset_clears_failures(self) -> None:
        """Test reset clears failure counts."""
        detector = GutterDetector()
        detector.track_failure("npm test", 1)
        detector.track_failure("npm test", 1)

        detector.reset()

        assert len(detector.failures) == 0

    def test_reset_clears_writes(self) -> None:
        """Test reset clears write history."""
        detector = GutterDetector()
        detector.track_write("/path/to/file.py")
        detector.track_write("/path/to/file.py")

        detector.reset()

        assert len(detector.writes) == 0

    def test_reset_allows_fresh_tracking(self) -> None:
        """Test tracking works fresh after reset."""
        detector = GutterDetector()

        # Get to 2 failures
        detector.track_failure("npm test", 1)
        detector.track_failure("npm test", 1)

        detector.reset()

        # After reset, should need 3 more failures to trigger
        detector.track_failure("npm test", 1)
        detector.track_failure("npm test", 1)
        result = detector.track_failure("npm test", 1)

        assert result is True
