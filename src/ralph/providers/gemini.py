"""Gemini provider."""

import json
from typing import Optional

from ralph.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    """Provider for Gemini CLI."""

    def get_cli_tool_name(self) -> str:
        """Return CLI tool name."""
        return "gemini"

    def get_command(self, prompt: str) -> list[str]:
        """Return command to run Gemini CLI."""
        return [
            "gemini",
            "--output-format",
            "stream-json",
        ]

    def parse_stream_line(self, line: str) -> Optional[dict]:
        """Parse Gemini stream-json output and normalize to cursor-agent format."""
        if not line.strip():
            return None
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        
        # Gemini uses flat message structure - convert to nested cursor-agent format
        msg_type = data.get("type", "")
        
        # Map init to system
        if msg_type == "init":
            return {
                "type": "system",
                "subtype": "init",
                "model": data.get("model", "unknown"),
                "session_id": data.get("session_id", ""),
            }
        
        # Map message to assistant format
        if msg_type == "message":
            role = data.get("role", "")
            if role == "assistant":
                content = data.get("content", "")
                return {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": content}],
                    },
                }
            elif role == "user":
                return {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": data.get("content", "")}],
                    },
                }
        
        # Map tool_use to tool_call
        if msg_type == "tool_use":
            return {
                "type": "tool_call",
                "subtype": "started",  # Gemini doesn't have completed, approximate
                "tool_call": {
                    # Map gemini tool format to cursor-agent format
                    # This is approximate - may need adjustment based on actual structure
                    "tool": data.get("tool_name", ""),
                    "args": data.get("parameters", {}),
                },
            }
        
        # Map tool_result
        if msg_type == "tool_result":
            return {
                "type": "tool_call",
                "subtype": "completed",
                "tool_call": {
                    "result": {
                        "success": data.get("status") == "success",
                        "output": data.get("output", ""),
                    },
                },
            }
        
        # Map result
        if msg_type == "result":
            return {
                "type": "result",
                "subtype": "success" if data.get("status") == "success" else "error",
                "duration_ms": data.get("stats", {}).get("duration_ms", 0),
            }
        
        # Pass through unknown types
        return data
