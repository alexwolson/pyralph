"""Unit tests for tokens.py - threshold calculations, health emoji."""

import pytest

from ralph.tokens import TokenTracker, WARN_THRESHOLD, ROTATE_THRESHOLD


class TestTokenTracker:
    """Tests for TokenTracker class."""

    def test_initial_state(self) -> None:
        """Test initial token tracker state."""
        tracker = TokenTracker()

        assert tracker.bytes_read == 0
        assert tracker.bytes_written == 0
        assert tracker.assistant_chars == 0
        assert tracker.shell_output_chars == 0
        assert tracker.prompt_chars == 3000  # Initial estimate
        assert tracker.warn_sent is False

    def test_add_read(self) -> None:
        """Test adding bytes from file read."""
        tracker = TokenTracker()

        tracker.add_read(1000)
        tracker.add_read(500)

        assert tracker.bytes_read == 1500

    def test_add_write(self) -> None:
        """Test adding bytes from file write."""
        tracker = TokenTracker()

        tracker.add_write(2000)

        assert tracker.bytes_written == 2000

    def test_add_assistant(self) -> None:
        """Test adding characters from assistant message."""
        tracker = TokenTracker()

        tracker.add_assistant(5000)

        assert tracker.assistant_chars == 5000

    def test_add_shell_output(self) -> None:
        """Test adding characters from shell output."""
        tracker = TokenTracker()

        tracker.add_shell_output(1000)

        assert tracker.shell_output_chars == 1000


class TestCalculateTokens:
    """Tests for token calculation."""

    def test_calculate_tokens_initial(self) -> None:
        """Test token calculation with only initial prompt."""
        tracker = TokenTracker()

        tokens = tracker.calculate_tokens()

        # 3000 prompt_chars / 4 = 750
        assert tokens == 750

    def test_calculate_tokens_with_activity(self) -> None:
        """Test token calculation with various activities."""
        tracker = TokenTracker()
        tracker.add_read(4000)
        tracker.add_write(2000)
        tracker.add_assistant(8000)
        tracker.add_shell_output(1000)

        tokens = tracker.calculate_tokens()

        # Total: 3000 + 4000 + 2000 + 8000 + 1000 = 18000
        # Tokens: 18000 / 4 = 4500
        assert tokens == 4500


class TestHealthEmoji:
    """Tests for health emoji display."""

    def test_green_emoji_under_60_percent(self) -> None:
        """Test green emoji when under 60% of rotate threshold."""
        tracker = TokenTracker()
        # ROTATE_THRESHOLD = 200_000
        # 60% of that = 120_000 tokens = 480_000 bytes
        # We start with 3000 (750 tokens), so add minimal to stay under

        emoji = tracker.get_health_emoji()

        assert emoji == "🟢"

    def test_yellow_emoji_between_60_and_80_percent(self) -> None:
        """Test yellow emoji when between 60-80% of rotate threshold."""
        tracker = TokenTracker()
        # Need 60-80% of 80_000 = 48_000 to 64_000 tokens
        # 56_000 tokens (70%) = 224_000 bytes
        # Subtract prompt (3000), need 221_000 more bytes
        tracker.add_read(221_000)

        emoji = tracker.get_health_emoji()

        assert emoji == "🟡"

    def test_red_emoji_over_80_percent(self) -> None:
        """Test red emoji when over 80% of rotate threshold."""
        tracker = TokenTracker()
        # Need 80%+ of 200_000 = 160_000+ tokens
        # 180_000 tokens = 720_000 bytes
        # Subtract prompt (3000), need 717_000 more bytes
        tracker.add_read(717_000)

        emoji = tracker.get_health_emoji()

        assert emoji == "🔴"


class TestThresholdWarnings:
    """Tests for threshold warning logic."""

    def test_should_warn_returns_true_at_threshold(self) -> None:
        """Test warning triggers at WARN_THRESHOLD."""
        tracker = TokenTracker()
        # WARN_THRESHOLD = 180_000 tokens = 720_000 bytes
        # Subtract prompt (3000), need 717_000 more bytes
        tracker.add_read(717_000)

        result = tracker.should_warn()

        assert result is True
        assert tracker.warn_sent is True

    def test_should_warn_only_once(self) -> None:
        """Test warning only triggers once."""
        tracker = TokenTracker()
        tracker.add_read(717_000)

        first_call = tracker.should_warn()
        second_call = tracker.should_warn()

        assert first_call is True
        assert second_call is False

    def test_should_warn_returns_false_below_threshold(self) -> None:
        """Test no warning when below threshold."""
        tracker = TokenTracker()

        result = tracker.should_warn()

        assert result is False
        assert tracker.warn_sent is False

    def test_should_rotate_at_threshold(self) -> None:
        """Test rotation triggers at ROTATE_THRESHOLD."""
        tracker = TokenTracker()
        # ROTATE_THRESHOLD = 200_000 tokens = 800_000 bytes
        # Subtract prompt (3000), need 797_000 more bytes
        tracker.add_read(797_000)

        result = tracker.should_rotate()

        assert result is True

    def test_should_rotate_returns_false_below_threshold(self) -> None:
        """Test no rotation when below threshold."""
        tracker = TokenTracker()
        tracker.add_read(100_000)

        result = tracker.should_rotate()

        assert result is False


class TestThresholdConstants:
    """Tests for threshold constants."""

    def test_warn_threshold_is_defined(self) -> None:
        """Test WARN_THRESHOLD is defined and reasonable."""
        assert WARN_THRESHOLD == 72_000

    def test_rotate_threshold_is_defined(self) -> None:
        """Test ROTATE_THRESHOLD is defined and reasonable."""
        assert ROTATE_THRESHOLD == 80_000

    def test_warn_is_less_than_rotate(self) -> None:
        """Test WARN_THRESHOLD is less than ROTATE_THRESHOLD."""
        assert WARN_THRESHOLD < ROTATE_THRESHOLD


class TestConfigurableThresholds:
    """Tests for configurable thresholds."""

    def test_custom_warn_threshold(self) -> None:
        """Test custom warn threshold is used."""
        tracker = TokenTracker(warn_threshold=100_000, rotate_threshold=200_000)
        # Add enough to pass 100_000 tokens (400_000 bytes - 3000 prompt = 397_000)
        tracker.add_read(397_000)

        result = tracker.should_warn()

        assert result is True

    def test_custom_rotate_threshold(self) -> None:
        """Test custom rotate threshold is used."""
        tracker = TokenTracker(warn_threshold=100_000, rotate_threshold=150_000)
        # Add enough to pass 150_000 tokens (600_000 bytes - 3000 prompt = 597_000)
        tracker.add_read(597_000)

        result = tracker.should_rotate()

        assert result is True

    def test_custom_thresholds_in_health_emoji(self) -> None:
        """Test custom thresholds affect health emoji calculation."""
        # Use a small rotate_threshold so we can easily test percentages
        tracker = TokenTracker(warn_threshold=8_000, rotate_threshold=10_000)
        # 10_000 tokens = 40_000 bytes
        # 80% of 10_000 = 8_000 tokens = 32_000 bytes
        # Subtract prompt (3000), need 29_000 more bytes
        tracker.add_read(29_000)

        emoji = tracker.get_health_emoji()

        assert emoji == "🔴"

    def test_defaults_match_constants(self) -> None:
        """Test default thresholds match module constants."""
        tracker = TokenTracker()

        assert tracker.warn_threshold == WARN_THRESHOLD
        assert tracker.rotate_threshold == ROTATE_THRESHOLD
