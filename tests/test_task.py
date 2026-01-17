"""Unit tests for task.py - parsing, checkbox counting, completion check."""

import tempfile
from pathlib import Path

import pytest

from ralph.task import count_criteria, check_completion, parse_task_file


class TestParseTaskFile:
    """Tests for parse_task_file function."""

    def test_parses_frontmatter_and_body(self, tmp_path: Path) -> None:
        """Test parsing task file with frontmatter."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """---
task: Test task
max_iterations: 10
---

# Task Content

- [ ] First criterion
- [ ] Second criterion
""",
            encoding="utf-8",
        )

        result = parse_task_file(task_file)

        assert result["frontmatter"]["task"] == "Test task"
        assert result["frontmatter"]["max_iterations"] == 10
        assert "# Task Content" in result["body"]
        assert result["path"] == task_file

    def test_parses_file_without_frontmatter(self, tmp_path: Path) -> None:
        """Test parsing task file without frontmatter."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """# Task Content

- [ ] First criterion
""",
            encoding="utf-8",
        )

        result = parse_task_file(task_file)

        assert result["frontmatter"] == {}
        assert "# Task Content" in result["body"]

    def test_handles_empty_frontmatter(self, tmp_path: Path) -> None:
        """Test parsing task file with empty frontmatter."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """---
---

# Task Content
""",
            encoding="utf-8",
        )

        result = parse_task_file(task_file)

        assert result["frontmatter"] == {}


class TestCountCriteria:
    """Tests for count_criteria function."""

    def test_counts_unchecked_checkboxes(self, tmp_path: Path) -> None:
        """Test counting unchecked checkboxes."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """# Task

- [ ] First criterion
- [ ] Second criterion
- [ ] Third criterion
""",
            encoding="utf-8",
        )

        done, total = count_criteria(task_file)

        assert done == 0
        assert total == 3

    def test_counts_checked_checkboxes(self, tmp_path: Path) -> None:
        """Test counting checked checkboxes."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """# Task

- [x] First criterion
- [x] Second criterion
- [ ] Third criterion
""",
            encoding="utf-8",
        )

        done, total = count_criteria(task_file)

        assert done == 2
        assert total == 3

    def test_handles_mixed_list_markers(self, tmp_path: Path) -> None:
        """Test handling different list markers."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """# Task

- [x] Dash marker done
* [ ] Asterisk marker pending
1. [x] Numbered marker done
2. [ ] Numbered marker pending
""",
            encoding="utf-8",
        )

        done, total = count_criteria(task_file)

        assert done == 2
        assert total == 4

    def test_handles_indented_checkboxes(self, tmp_path: Path) -> None:
        """Test handling indented checkboxes."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """# Task

- [x] Main criterion
  - [ ] Sub criterion 1
  - [x] Sub criterion 2
""",
            encoding="utf-8",
        )

        done, total = count_criteria(task_file)

        assert done == 2
        assert total == 3

    def test_handles_no_checkboxes(self, tmp_path: Path) -> None:
        """Test handling file with no checkboxes."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """# Task

Just some text without checkboxes.
""",
            encoding="utf-8",
        )

        done, total = count_criteria(task_file)

        assert done == 0
        assert total == 0


class TestCheckCompletion:
    """Tests for check_completion function."""

    def test_returns_complete_when_all_done(self, tmp_path: Path) -> None:
        """Test COMPLETE status when all criteria are checked."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """# Task

- [x] First criterion
- [x] Second criterion
""",
            encoding="utf-8",
        )

        result = check_completion(task_file)

        assert result == "COMPLETE"

    def test_returns_incomplete_with_remaining_count(self, tmp_path: Path) -> None:
        """Test INCOMPLETE status shows remaining count."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """# Task

- [x] First criterion
- [ ] Second criterion
- [ ] Third criterion
""",
            encoding="utf-8",
        )

        result = check_completion(task_file)

        assert result == "INCOMPLETE:2"

    def test_returns_no_criteria_when_empty(self, tmp_path: Path) -> None:
        """Test NO_CRITERIA status when no checkboxes present."""
        task_file = tmp_path / "RALPH_TASK.md"
        task_file.write_text(
            """# Task

No criteria here.
""",
            encoding="utf-8",
        )

        result = check_completion(task_file)

        assert result == "NO_CRITERIA"
