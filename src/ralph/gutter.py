"""Gutter detection for Ralph."""

import time
from collections import defaultdict
from typing import Dict, List, Tuple


class GutterDetector:
    """Detect stuck patterns (gutter conditions)."""

    def __init__(self):
        self.failures: Dict[str, int] = defaultdict(int)
        self.writes: List[Tuple[int, str]] = []  # (timestamp, filepath)

    def track_failure(self, command: str, exit_code: int) -> bool:
        """Track shell command failure. Returns True if gutter detected."""
        if exit_code != 0:
            self.failures[command] += 1
            count = self.failures[command]
            
            if count >= 3:
                return True  # Gutter: same command failed 3x
        return False

    def track_write(self, filepath: str) -> bool:
        """Track file write. Returns True if gutter detected."""
        now = int(time.time())
        self.writes.append((now, filepath))

        # Remove writes older than 10 minutes
        cutoff = now - 600
        self.writes = [(ts, path) for ts, path in self.writes if ts >= cutoff]

        # Count writes to this file in last 10 minutes
        count = sum(1 for ts, path in self.writes if path == filepath)

        if count >= 5:
            return True  # Gutter: same file written 5x in 10 min

        return False

    def reset(self) -> None:
        """Reset gutter detection state."""
        self.failures.clear()
        self.writes.clear()
