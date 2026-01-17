"""Codex provider."""

import json
from pathlib import Path
from typing import Optional

from ralph.providers.base import BaseProvider


class CodexProvider(BaseProvider):
    """Provider for Codex CLI."""

    def get_cli_tool_name(self) -> str:
        """Return CLI tool name."""
        return "codex"

    def get_command(self, prompt: str, workspace: Path) -> list[str]:
        """Return command to run Codex CLI."""
        # Workspace is handled via subprocess cwd parameter, not command flag
        return [
            "codex",
            "exec",
            "--json",
        ]

    def parse_stream_line(self, line: str) -> Optional[dict]:
        """Parse Codex JSONL output and normalize to cursor-agent format."""
        if not line.strip():
            return None
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        
        # Codex uses item.completed structure - convert to cursor-agent format
        msg_type = data.get("type", "")
        
        # Map thread.started to system init
        if msg_type == "thread.started":
            return {
                "type": "system",
                "subtype": "init",
                "thread_id": data.get("thread_id", ""),
            }
        
        # Map turn.started to system message
        if msg_type == "turn.started":
            return {
                "type": "system",
                "subtype": "turn_started",
            }
        
        # Map item.completed with agent_message to assistant
        if msg_type == "item.completed":
            item = data.get("item", {})
            item_type = item.get("type", "")
            
            if item_type == "agent_message":
                text = item.get("text", "")
                return {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": text}],
                    },
                }
            
            # Map other item types (tool calls, etc.) - structure TBD
            # For now, pass through and let parser handle it
            return data
        
        # Map turn.completed to result
        if msg_type == "turn.completed":
            usage = data.get("usage", {})
            return {
                "type": "result",
                "subtype": "success",
                "usage": usage,
            }
        
        # Pass through unknown types
        return data
