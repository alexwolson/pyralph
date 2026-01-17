---
task: Trivial test tasks for Ralph test run
completion_criteria:
  - Add a module-level docstring to src/ralph/signals.py describing its purpose
  - Add a DESCRIPTION constant to src/ralph/__init__.py with a one-line project description
  - Add a comment at the top of main.py explaining it is the CLI entry point
max_iterations: 10
test_command: "uv run pytest -v"
---

# Task: Trivial Test Tasks

This is a test run of Ralph with simple tasks that require minimal file modifications.

## Success Criteria

The task is complete when ALL of the following are true:

- [x] Add a module-level docstring to `src/ralph/signals.py` describing its purpose (e.g., "Signal handling for Ralph agent communication")
- [x] Add a `DESCRIPTION` constant to `src/ralph/__init__.py` with a one-line project description string
- [x] Add a comment at the top of `main.py` (after any existing comments) explaining it is the CLI entry point for the ralph command

## Constraints

- Keep changes minimal and focused
- Do not modify any logic or functionality
- These are documentation/metadata changes only

---

## Ralph Instructions

You are an autonomous agent working on this task. Follow these steps:

1. **Read state files first**:
   - This file (`RALPH_TASK.md`) for task definition
   - `.ralph/progress.md` for what's been done
   - `.ralph/guardrails.md` for lessons learned

2. **Work on ONE unchecked criterion at a time**:
   - Find the first unchecked `- [ ]` criterion
   - Complete it fully
   - Check it off as `- [x]`
   - Commit your changes

3. **Git protocol**:
   - Commit after completing each criterion
   - Use descriptive commit messages
   - Always commit before signaling completion

4. **When all criteria are complete**:
   - Verify all checkboxes are checked
   - Run the test command if specified
   - Signal completion with: `<ralph>COMPLETE</ralph>`

5. **If you get stuck**:
   - Add what you learned to `.ralph/guardrails.md`
   - Signal for rotation with: `<ralph>GUTTER</ralph>`
