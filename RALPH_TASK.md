---
task: Update branding and color scheme to yellow-forward "Ralph"
completion_criteria:
  - "THEME primary color changed from cyan to yellow in ui.py"
  - "All \"Ralph Wiggum\" references replaced with \"Ralph\" throughout codebase"
  - "\"AI Assistant\" replaced with \"Ralph\" in interview_turns.py"
  - "Tests pass after branding changes"
max_iterations: 10
test_command: "python -m pytest tests/ -v"
---

# Task: Update Branding and Color Scheme

Rebrand the pyralph project to use:
1. **Yellow-forward color scheme** instead of cyan
2. **"Ralph"** branding instead of "Ralph Wiggum"
3. **"Ralph"** instead of "AI Assistant" in UI panels

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] THEME primary color changed from cyan to yellow in ui.py
- [ ] All "Ralph Wiggum" references replaced with "Ralph" throughout codebase
- [ ] "AI Assistant" replaced with "Ralph" in interview_turns.py
- [ ] Tests pass after branding changes

## Files to Update

1. **src/ralph/ui.py**
   - Change `"primary": "cyan"` to `"primary": "yellow"` in THEME dict
   - Update `print_header` default title from "Ralph Wiggum" to "Ralph"

2. **src/ralph/cli.py**
   - Line 64: CLI help text docstring
   - Line 209: Console output header

3. **src/ralph/interview.py**
   - Lines 51-53: Prompt text references to "Ralph Wiggum"

4. **src/ralph/interview_turns.py**
   - Line 85: Change "AI Assistant" to "Ralph" in panel title

5. **src/ralph/__init__.py**
   - Line 1: Module docstring

6. **tests/test_cli.py**
   - Line 37: Update test assertion from "Ralph Wiggum" to "Ralph"

7. **README.md**
   - Line 1: Title
   - Line 351: Reference text

8. **pyproject.toml**
   - Line 4: Package description

## Constraints

- Keep the yellow color readable (use bold styling where needed for visibility)
- Maintain consistency across all files
- Ensure tests still pass after changes

---

## Ralph Instructions

You are an autonomous agent working through this task. Follow these steps:

1. **Read state files first**:
   - Read `.ralph/guardrails.md` for lessons learned
   - Read `.ralph/progress.md` for previous progress
   - Read this file (RALPH_TASK.md) for current criteria status

2. **Work on ONE unchecked criterion at a time**:
   - Find the first unchecked `- [ ]` criterion
   - Complete all work needed for that criterion
   - Mark it complete by changing `- [ ]` to `- [x]`

3. **Commit after each criterion**:
   - Stage your changes with `git add`
   - Commit with a descriptive message
   - Push if on a branch

4. **Run tests after changes**:
   - Run `python -m pytest tests/ -v` to verify changes
   - Fix any failing tests before marking criterion complete

5. **If stuck or context is high**:
   - Commit current progress
   - Add notes to `.ralph/progress.md`
   - The next agent will continue from your commit
