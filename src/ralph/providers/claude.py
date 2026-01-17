"""Claude provider."""

import json
from pathlib import Path
from typing import Optional

from ralph.providers.base import BaseProvider


class ClaudeProvider(BaseProvider):
    """Provider for Claude CLI."""

    def get_cli_tool_name(self) -> str:
        """Return CLI tool name."""
        return "claude"

    def get_command(self, prompt: str, workspace: Path) -> list[str]:
        """Return command to run Claude CLI."""
        # Workspace is handled via subprocess cwd parameter, not command flag
        # --verbose is required for stream-json
        return [
            "claude",
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
        ]

    def parse_stream_line(self, line: str) -> Optional[dict]:
        """Parse Claude stream-json output and normalize to cursor-agent format."""
        if not line.strip():
            return None
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        
        # Claude format is very similar to cursor-agent, but tool calls are nested differently
        msg_type = data.get("type", "")
        
        # Pass through most types as-is (assistant, system, result)
        if msg_type in ("assistant", "system", "result", "user", "thinking"):
            return data
        
        # Note: Tool calls in claude are in message.content as tool_use objects,
        # not as top-level tool_call. The parser will need to handle this.
        # For now, pass through everything and let the parser handle extraction.
        return data
