---
task: Trivial test tasks to verify Ralph loop functionality
completion_criteria:
  - Add a comment to main.py noting it's the CLI entry point
  - Create a .ralph/test_marker.txt file containing "Ralph was here"
  - Add a docstring to the main() function in main.py if missing
max_iterations: 10
test_command: ""
---

# Task: Trivial Test Run

This is a test run of Ralph with simple tasks to verify the loop is working correctly.

## Success Criteria

The task is complete when ALL of the following are true:

- [x] Add a comment to `main.py` at the top (after the docstring) noting this file is the CLI entry point
- [x] Create a file `.ralph/test_marker.txt` containing the text "Ralph was here"
- [x] Ensure the `main()` function call in `main.py` has a brief inline comment explaining what it does

## Constraints

- Keep changes minimal - these are test tasks
- Each task should take only a few seconds to complete
- Commit after completing each criterion

---

## Ralph Instructions

You are an autonomous agent working on this task. Follow these rules:

### Before Starting
1. Read `.ralph/progress.md` to see what's been done
2. Read `.ralph/guardrails.md` for lessons learned (signs to follow)
3. Check which criteria are already marked `[x]` complete

### Working Protocol
1. Work on ONE unchecked criterion at a time
2. After completing a criterion, mark it `[x]` in this file
3. Commit your changes with a descriptive message
4. Update `.ralph/progress.md` with what you accomplished

### Git Protocol
- Commit after each meaningful change
- Use clear commit messages describing what was done
- Never amend commits - always create new ones

### Signals
- Output `<ralph>COMPLETE</ralph>` when ALL criteria are checked
- Output `<ralph>GUTTER</ralph>` if you're stuck and need rotation
- Output `ROTATE` if context is getting too long

### Important
- Don't skip criteria - work through them in order
- If a criterion is unclear, make a reasonable interpretation
- Check your work before marking complete
