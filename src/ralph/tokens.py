"""Token tracking for Ralph."""

# Token thresholds
WARN_THRESHOLD = 180_000
ROTATE_THRESHOLD = 200_000


class TokenTracker:
    """Track context token usage."""

    def __init__(self):
        self.bytes_read = 0
        self.bytes_written = 0
        self.assistant_chars = 0
        self.shell_output_chars = 0
        self.prompt_chars = 3000  # Initial prompt estimate
        self.warn_sent = False

    def add_read(self, bytes_count: int) -> None:
        """Add bytes from file read."""
        self.bytes_read += bytes_count

    def add_write(self, bytes_count: int) -> None:
        """Add bytes from file write."""
        self.bytes_written += bytes_count

    def add_assistant(self, chars: int) -> None:
        """Add characters from assistant message."""
        self.assistant_chars += chars

    def add_shell_output(self, chars: int) -> None:
        """Add characters from shell output."""
        self.shell_output_chars += chars

    def calculate_tokens(self) -> int:
        """Calculate approximate token count (bytes / 4)."""
        total_bytes = (
            self.prompt_chars
            + self.bytes_read
            + self.bytes_written
            + self.assistant_chars
            + self.shell_output_chars
        )
        return total_bytes // 4

    def get_health_emoji(self) -> str:
        """Get health emoji based on token percentage."""
        tokens = self.calculate_tokens()
        pct = (tokens * 100) // ROTATE_THRESHOLD

        if pct < 60:
            return "🟢"
        elif pct < 80:
            return "🟡"
        else:
            return "🔴"

    def should_warn(self) -> bool:
        """Check if warning threshold reached (only once)."""
        tokens = self.calculate_tokens()
        if tokens >= WARN_THRESHOLD and not self.warn_sent:
            self.warn_sent = True
            return True
        return False

    def should_rotate(self) -> bool:
        """Check if rotation threshold reached."""
        return self.calculate_tokens() >= ROTATE_THRESHOLD
