---
task: Trivial test tasks for Ralph test run
completion_criteria:
  - Add a MASCOT_NAME constant to src/ralph/__init__.py with value "Ralph the Robot"
  - Add a one-line docstring to the top of src/ralph/signals.py if missing
  - Create a file .ralph/test_marker.txt containing "Ralph test run successful"
max_iterations: 10
test_command: "python -c \"from ralph import MASCOT_NAME; print(MASCOT_NAME)\""
---

# Task: Trivial Test Tasks

This is a test run of Ralph with intentionally simple tasks to verify the loop works correctly. Each task requires a small file modification.

## Success Criteria

The task is complete when ALL of the following are true:

- [x] Add a `MASCOT_NAME` constant to `src/ralph/__init__.py` with value `"Ralph the Robot"`
- [x] Add a one-line docstring to the top of `src/ralph/signals.py` if it doesn't already have one (e.g., `"""Signal handling for Ralph agents."""`)
- [x] Create a file `.ralph/test_marker.txt` containing the text `Ralph test run successful`

## Constraints

- These are trivial tasks - do not overthink them
- Make minimal changes to complete each criterion
- Each criterion should take only a few seconds to implement

---

## Ralph Instructions

You are an autonomous coding agent working through this task iteratively.

### Before Starting Each Iteration

1. Read these state files to understand context:
   - `RALPH_TASK.md` (this file) - Task definition and criteria
   - `.ralph/progress.md` - What has been accomplished
   - `.ralph/guardrails.md` - Important lessons and constraints
   - `.ralph/errors.log` - Recent errors (if any)

2. Check which criteria are already marked complete (with `[x]`)

3. Work on the NEXT unchecked criterion only

### Working Protocol

1. **One criterion at a time**: Focus on completing one checkbox before moving to the next
2. **Commit after each criterion**: Make a git commit after completing each criterion
3. **Update the checkbox**: Mark the criterion as complete by changing `- [ ]` to `- [x]`
4. **Update progress**: Add a brief note to `.ralph/progress.md` about what was done

### Git Commit Protocol

After completing work on a criterion:
```bash
git add -A
git commit -m "Complete: [brief description of what was done]"
```

### Completion

When ALL criteria are checked off:
1. Run the test command if specified: `python -c "from ralph import MASCOT_NAME; print(MASCOT_NAME)"`
2. If tests pass, signal completion with: `<ralph>COMPLETE</ralph>`

### If Stuck

If you encounter issues you cannot resolve:
1. Document the problem in `.ralph/errors.log`
2. Add a guardrail to `.ralph/guardrails.md` to help future iterations
3. Signal for rotation with: `<ralph>GUTTER</ralph>`
