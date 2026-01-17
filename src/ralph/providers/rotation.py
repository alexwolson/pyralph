"""Provider rotation manager."""

import json
import time
from pathlib import Path
from typing import Optional

from ralph.providers.base import BaseProvider

# #region debug log - Rotation method tracking
DEBUG_LOG_PATH = Path("/Users/alex/repos/pyralph/.cursor/debug.log")

def _debug_log(location: str, message: str, data: dict) -> None:
    """Helper to write debug logs."""
    try:
        log_entry = {
            "sessionId": "debug-session",
            "runId": "rotation-check",
            "hypothesisId": "D",
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000)
        }
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass  # Fail silently
# #endregion


class ProviderRotation:
    """Manages rotation between available providers on failure."""

    def __init__(self, providers: list[BaseProvider]):
        """Initialize with list of available providers."""
        self.providers = providers
        self.current_index = 0

    def get_current(self) -> BaseProvider:
        """Get current provider."""
        if not self.providers:
            raise ValueError("No providers available")
        return self.providers[self.current_index]

    def rotate(self) -> Optional[BaseProvider]:
        """Rotate to next provider. Returns None if no more providers."""
        # #region debug log - rotate() entry
        _debug_log(
            "rotation.py:32",
            "rotate() called",
            {
                "current_index_before": self.current_index,
                "total_providers": len(self.providers),
                "provider_count": len(self.providers)
            }
        )
        # #endregion
        
        if not self.providers:
            return None
        if len(self.providers) == 1:
            return self.get_current()  # Can't rotate if only one provider
        self.current_index = (self.current_index + 1) % len(self.providers)
        
        # #region debug log - rotate() after index update
        result = self.get_current()
        _debug_log(
            "rotation.py:47",
            "rotate() completed",
            {
                "current_index_after": self.current_index,
                "new_provider_cli": result.cli_tool if hasattr(result, 'cli_tool') else str(type(result).__name__),
                "next_index_calc": f"({self.current_index - 1} + 1) % {len(self.providers)} = {self.current_index}"
            }
        )
        # #endregion
        
        return result

    def has_next(self) -> bool:
        """Check if there are more providers to try."""
        return len(self.providers) > 1

    def get_provider_name(self) -> str:
        """Get name of current provider."""
        provider = self.get_current()
        return provider.cli_tool if hasattr(provider, 'cli_tool') else str(type(provider).__name__)
