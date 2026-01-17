"""Base provider interface."""

from abc import ABC, abstractmethod
from typing import Optional

import shutil


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self):
        """Initialize provider with CLI tool name."""
        self.cli_tool = self.get_cli_tool_name()

    @abstractmethod
    def get_cli_tool_name(self) -> str:
        """Return the CLI tool name (e.g., 'cursor-agent', 'claude')."""
        pass

    @abstractmethod
    def get_command(self, prompt: str) -> list[str]:
        """Return command to run provider CLI.
        
        Each provider uses its own default model internally.
        No model parameter needed - provider knows its best default.
        """
        pass

    @abstractmethod
    def parse_stream_line(self, line: str) -> Optional[dict]:
        """Parse a line from provider output to standard format.
        
        Returns standardized dict matching cursor-agent stream-json format,
        or None if line should be ignored.
        """
        pass

    def is_available(self) -> bool:
        """Check if provider CLI is available on system."""
        return shutil.which(self.cli_tool) is not None
