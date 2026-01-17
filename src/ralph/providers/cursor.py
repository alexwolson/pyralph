"""cursor-agent provider."""

import json
from pathlib import Path
from typing import Optional

from ralph.providers.base import BaseProvider


class CursorProvider(BaseProvider):
    """Provider for cursor-agent CLI."""

    def get_cli_tool_name(self) -> str:
        """Return CLI tool name."""
        return "cursor-agent"

    def get_command(self, prompt: str, workspace: Path) -> list[str]:
        """Return command to run cursor-agent."""
        return [
            "cursor-agent",
            "-p",
            "--force",
            "--output-format",
            "stream-json",
            "--directory",
            str(workspace),
        ]

    def parse_stream_line(self, line: str) -> Optional[dict]:
        """Parse cursor-agent stream-json output (pass-through, already correct format)."""
        if not line.strip():
            return None
        
        try:
            data = json.loads(line)
            return data
        except json.JSONDecodeError:
            return None
