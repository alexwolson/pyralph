"""Provider rotation manager."""

from typing import Optional

from ralph.debug import debug_log
from ralph.providers.base import BaseProvider


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
        debug_log(
            "rotation.py:rotate",
            "rotate() called",
            {
                "current_index_before": self.current_index,
                "total_providers": len(self.providers),
                "provider_count": len(self.providers)
            },
            "D"
        )
        
        if not self.providers:
            return None
        if len(self.providers) == 1:
            return self.get_current()  # Can't rotate if only one provider
        self.current_index = (self.current_index + 1) % len(self.providers)
        
        result = self.get_current()
        debug_log(
            "rotation.py:rotate",
            "rotate() completed",
            {
                "current_index_after": self.current_index,
                "new_provider_cli": result.cli_tool if hasattr(result, 'cli_tool') else str(type(result).__name__),
                "next_index_calc": f"({self.current_index - 1} + 1) % {len(self.providers)} = {self.current_index}"
            },
            "D"
        )
        
        return result

    def has_next(self) -> bool:
        """Check if there are more providers to try."""
        return len(self.providers) > 1

    def get_provider_name(self) -> str:
        """Get name of current provider."""
        provider = self.get_current()
        return provider.cli_tool if hasattr(provider, 'cli_tool') else str(type(provider).__name__)
