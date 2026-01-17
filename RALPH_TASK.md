---
task: Clean up .ralph state files upon task completion to prevent context bloat
completion_criteria:
  - Archive progress.md to .ralph/completed/ alongside task archive
  - Archive activity.log to .ralph/completed/ alongside task archive
  - Archive errors.log to .ralph/completed/ alongside task archive
  - Guardrails.md is NOT touched (persists across tasks)
  - Archives use matching timestamp with the task archive
  - Original files are reset to empty/initial state after archiving
  - Cleanup runs automatically after archive_completed_task()
  - Tests pass
max_iterations: 15
test_command: "uv run pytest -v"
---

# Task: Clean Up .ralph State Files on Task Completion

## Problem

When `.ralph/` state files (`progress.md`, `activity.log`, `errors.log`) become too large, new agent iterations immediately consume their context window and trigger rotations. This creates a feedback loop where no progress can be made.

## Solution

Upon successful task completion (after `archive_completed_task()` runs), archive the accumulated state files to `.ralph/completed/` and reset them to their initial empty state.

## Success Criteria

The task is complete when ALL of the following are true:

- [x] Archive `progress.md` to `.ralph/completed/` alongside task archive
- [x] Archive `activity.log` to `.ralph/completed/` alongside task archive  
- [x] Archive `errors.log` to `.ralph/completed/` alongside task archive
- [x] `guardrails.md` is NOT touched (persists across tasks - contains learned lessons)
- [x] Archives use matching timestamp with the task archive for easy correlation
- [x] Original files are reset to empty/initial state after archiving
- [x] Cleanup runs automatically after `archive_completed_task()` completes
- [x] All existing tests pass (`uv run pytest -v`)

## Implementation Notes

- Look at `archive_completed_task()` in `src/ralph/state.py` for the existing archive pattern
- The function already archives `RALPH_TASK.md` with a timestamp - reuse that timestamp
- Consider creating a helper function for archiving state files, or extending the existing archive function
- Empty/initial state for logs is just empty files; for progress.md check if there's a template

## Constraints

- Do not modify or archive `guardrails.md` - it contains valuable cross-task learnings
- Maintain backward compatibility with existing archive structure
- Follow existing code patterns and style

---

## Ralph Instructions

### Before Starting Work

1. Read `.ralph/guardrails.md` for project-specific rules and lessons learned
2. Read `.ralph/progress.md` to understand what's already been done
3. Check git log for recent commits and context

### Working Protocol

1. Work on ONE unchecked criterion at a time
2. Make small, focused commits with descriptive messages
3. After completing a criterion, check it off in this file
4. If you encounter an issue that future agents should avoid, add it to `.ralph/guardrails.md`

### Git Protocol

- Commit after each meaningful change
- Use clear commit messages that explain what and why
- Never force push or rewrite history

### When Stuck

- If you're stuck on a criterion, document what you tried in `.ralph/progress.md`
- The next agent iteration will pick up from your commits
