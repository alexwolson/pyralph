"""Token tracking for Ralph."""

# Default token thresholds
WARN_THRESHOLD = 72_000
ROTATE_THRESHOLD = 80_000


class TokenTracker:
    """Track context token usage."""

    def __init__(
        self,
        warn_threshold: int = WARN_THRESHOLD,
        rotate_threshold: int = ROTATE_THRESHOLD,
    ):
        """Initialize token tracker with configurable thresholds.
        
        Args:
            warn_threshold: Token count at which to warn about context size
            rotate_threshold: Token count at which to trigger rotation
        """
        self.bytes_read = 0
        self.bytes_written = 0
        self.assistant_chars = 0
        self.shell_output_chars = 0
        self.prompt_chars = 3000  # Initial prompt estimate
        self.warn_sent = False
        self.warn_threshold = warn_threshold
        self.rotate_threshold = rotate_threshold

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

    def get_health_symbol(self) -> str:
        """Get health indicator symbol (plain Unicode) for log files.
        
        Returns a plain Unicode symbol without Rich markup.
        """
        tokens = self.calculate_tokens()
        pct = (tokens * 100) // self.rotate_threshold

        if pct < 60:
            return "●"
        elif pct < 80:
            return "●"
        else:
            return "●"

    def get_health_emoji(self) -> str:
        """Get health indicator symbol based on token percentage.
        
        Returns a Unicode symbol with Rich color markup for display.
        """
        tokens = self.calculate_tokens()
        pct = (tokens * 100) // self.rotate_threshold

        if pct < 60:
            return "[green]●[/]"
        elif pct < 80:
            return "[yellow]●[/]"
        else:
            return "[red]●[/]"

    def should_warn(self) -> bool:
        """Check if warning threshold reached (only once)."""
        tokens = self.calculate_tokens()
        if tokens >= self.warn_threshold and not self.warn_sent:
            self.warn_sent = True
            return True
        return False

    def should_rotate(self) -> bool:
        """Check if rotation threshold reached."""
        return self.calculate_tokens() >= self.rotate_threshold
