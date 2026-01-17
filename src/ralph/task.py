"""Task file parsing and management."""

import re
from pathlib import Path
from typing import Dict, List, Tuple

from ralph.parser import parse_frontmatter


def parse_task_file(task_file: Path) -> Dict:
    """Parse RALPH_TASK.md file (frontmatter + markdown)."""
    content = task_file.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    
    return {
        "frontmatter": frontmatter,
        "body": body,
        "path": task_file,
    }


def count_criteria(task_file: Path) -> Tuple[int, int]:
    """Count checkboxes in task file. Returns (done, total)."""
    content = task_file.read_text(encoding="utf-8")
    
    # Match checkbox list items: "- [ ]", "* [x]", "1. [ ]", etc.
    # Use \s instead of [[:space:]] to avoid nested character class warning
    checkbox_pattern = r"^\s*([-*]|[0-9]+\.)\s+\[([ x])\]"
    
    total = 0
    done = 0
    
    for line in content.splitlines():
        match = re.match(checkbox_pattern, line)
        if match:
            total += 1
            if match.group(2) == "x":
                done += 1
    
    return (done, total)


def check_completion(task_file: Path) -> str:
    """Check if task is complete. Returns 'COMPLETE' or 'INCOMPLETE:N'."""
    done, total = count_criteria(task_file)
    
    if total == 0:
        return "NO_CRITERIA"
    
    if done == total:
        return "COMPLETE"
    
    return f"INCOMPLETE:{total - done}"
