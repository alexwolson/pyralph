"""Cursor agent provider."""

import json
from pathlib import Path
from typing import Optional

from ralph.providers.base import BaseProvider


class CursorProvider(BaseProvider):
    """Provider for Cursor agent CLI."""

    def get_cli_tool_name(self) -> str:
        """Return CLI tool name."""
        return "agent"

    def get_display_name(self) -> str:
        """Return user-facing display name."""
        return "cursor"

    def get_command(self, prompt: str, workspace: Path) -> list[str]:
        """Return command to run agent CLI."""
        return [
            "agent",
            "-p",
            "--force",
            "--output-format",
            "stream-json",
            "--directory",
            str(workspace),
        ]

    def parse_stream_line(self, line: str) -> Optional[dict]:
        """Parse agent stream-json output (pass-through, already correct format)."""
        if not line.strip():
            return None
        
        try:
            data = json.loads(line)
            return data
        except json.JSONDecodeError:
            return None
