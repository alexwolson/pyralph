---
task: Trivial test tasks to verify Ralph loop functionality
completion_criteria:
  - Add author metadata to pyproject.toml
  - Add a CHANGELOG.md file with initial entry
  - Add __author__ variable to src/ralph/__init__.py
  - Update the project description in pyproject.toml to mention autonomous coding
max_iterations: 10
test_command: "uv run pytest -v"
---

# Task: Trivial Test Tasks

This is a test run of Ralph with trivial tasks. Each task requires a small file modification.

## Success Criteria

The task is complete when ALL of the following are true:

- [x] Add `authors` field to `pyproject.toml` with value `[{name = "Ralph Test"}]`
- [x] Create `CHANGELOG.md` in the project root with a "## [0.1.0] - Unreleased" section containing "- Initial release"
- [x] Add `__author__ = "Ralph Test"` to `src/ralph/__init__.py` after the existing `__version__` line
- [ ] Update the `description` field in `pyproject.toml` to append " for autonomous coding" at the end

## Constraints

- Each change should be committed separately with a descriptive commit message
- Do not modify any other files
- Keep changes minimal and focused
- Tests must still pass after all changes

---

## Ralph Instructions

You are an autonomous agent working in a loop. Follow these instructions precisely.

### Before Starting Work

1. Read the state files:
   - `RALPH_TASK.md` (this file) - your task definition
   - `.ralph/progress.md` - what's been done in previous iterations
   - `.ralph/guardrails.md` - lessons learned, avoid repeating mistakes
   - `.ralph/errors.log` - recent errors to be aware of

2. Identify the FIRST unchecked criterion (`- [ ]`) in this file

### Working Protocol

1. Work on ONE criterion at a time
2. Make the minimal changes needed to satisfy the criterion
3. Run the test command if one is specified: `uv run pytest -v`
4. If tests pass, check off the criterion by changing `- [ ]` to `- [x]`
5. Commit your changes with a descriptive message

### Git Protocol

- Commit after completing each criterion
- Use clear commit messages that describe what was done
- Include the criterion text in your commit message

### Completion

When ALL criteria are checked (`- [x]`), output:
```
<ralph>COMPLETE</ralph>
```

### If Stuck

If you cannot make progress after reasonable attempts:
1. Document what you tried in `.ralph/progress.md`
2. Output: `<ralph>GUTTER</ralph>`

This signals Ralph to rotate to a fresh agent.
