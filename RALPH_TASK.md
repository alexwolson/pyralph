---
task: Trivial test tasks for Ralph test run
completion_criteria:
  - Add a PROJECT_URL constant to src/ralph/__init__.py
  - Add a module-level docstring to src/ralph/tokens.py if missing
  - Add a RALPH_EMOJI constant set to a robot emoji in src/ralph/__init__.py
max_iterations: 10
test_command: "python -c \"from ralph import PROJECT_URL, RALPH_EMOJI; print(PROJECT_URL, RALPH_EMOJI)\""
---

# Task: Trivial Test Tasks

This is a test run to verify Ralph is working correctly. Complete these simple file modification tasks.

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] Add a `PROJECT_URL` constant to `src/ralph/__init__.py` with value `"https://github.com/pyralph/pyralph"`
- [ ] Add a module-level docstring to `src/ralph/tokens.py` describing what the module does (if one doesn't already exist)
- [ ] Add a `RALPH_EMOJI` constant to `src/ralph/__init__.py` with value `"🤖"`

## Constraints

- Keep changes minimal and focused
- Do not modify any existing functionality
- All changes should be additive only

---

## Ralph Instructions

You are an autonomous agent working on a coding task. Follow these instructions carefully:

### Before Starting Work

1. Read `.ralph/progress.md` to understand what has been accomplished
2. Read `.ralph/guardrails.md` for important lessons and constraints
3. Check which criteria in this file are already marked complete

### Working Protocol

1. Work on ONE unchecked criterion at a time
2. Make the minimal changes needed to satisfy the criterion
3. After completing a criterion, mark it with `[x]` in this file
4. Commit your changes with a descriptive message
5. Update `.ralph/progress.md` with what you accomplished

### Git Protocol

- Commit after completing each criterion
- Use clear commit messages describing the change
- Never amend commits or rewrite history

### Completion

When ALL criteria are checked:
1. Verify the test command passes (if provided)
2. Output: `<ralph>COMPLETE</ralph>`

### If Stuck

If you cannot make progress:
1. Document the issue in `.ralph/progress.md`
2. Output: `<ralph>GUTTER</ralph>`
