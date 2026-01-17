---
task: Add commit-based rotation and completed task archival
completion_criteria:
  - Add ROTATE signal instruction after git commits in build_prompt()
  - Archive completed RALPH_TASK.md to .ralph/completed/ with timestamp
  - Ensure .ralph/completed/ directory is created if it doesn't exist
  - Update tests if existing tests cover affected functionality
max_iterations: 20
test_command: "pytest"
---

# Task: Add Commit-Based Rotation and Completed Task Archival

Implement two enhancements to the Ralph loop:

1. **Rotation after commits**: Instruct agents via the prompt to signal ROTATE after successfully committing changes. This ensures fresh context after each meaningful checkpoint.

2. **Archive completed tasks**: When a task completes successfully, rename `RALPH_TASK.md` to `.ralph/completed/RALPH_TASK_<timestamp>.md` so a new task file can be provided.

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] Add instruction in `build_prompt()` (src/ralph/loop.py) telling agents to output `<ralph>ROTATE</ralph>` after making a git commit
- [ ] Modify completion handling in `run_ralph_loop()` to rename RALPH_TASK.md to `.ralph/completed/RALPH_TASK_<timestamp>.md` (format: `RALPH_TASK_20260116_143052.md`)
- [ ] Create `.ralph/completed/` directory if it doesn't exist before archiving
- [ ] Update any existing tests that may be affected by these changes (check tests/ directory)

## Implementation Details

### Criterion 1: Prompt update in build_prompt()
Location: `src/ralph/loop.py`, function `build_prompt()`, around line 58

Add to the "Git Protocol" section:
```
5. After committing, signal for fresh context: output `<ralph>ROTATE</ralph>`
   This ensures each commit checkpoint gets a fresh agent context.
```

### Criterion 2 & 3: Archive completed tasks
Location: `src/ralph/loop.py`, function `run_ralph_loop()`, around lines 268-292 (completion handling)

When task is complete:
1. Create `.ralph/completed/` directory if needed
2. Generate timestamp string (format: `YYYYMMDD_HHMMSS`)
3. Rename `RALPH_TASK.md` to `.ralph/completed/RALPH_TASK_<timestamp>.md`
4. Log the archival action

## Constraints

- Use Python's `datetime` module for timestamp generation
- Use `Path.mkdir(parents=True, exist_ok=True)` for directory creation
- Use `Path.rename()` for file moving
- Keep existing completion logic (PR opening, etc.) working

---
## Ralph Instructions

Read these state files before starting:
- `RALPH_TASK.md` - this file, your task definition
- `.ralph/guardrails.md` - lessons from past failures
- `.ralph/progress.md` - what's been accomplished

**Git Protocol:**
1. Commit after completing each criterion
2. Use descriptive commit messages: `ralph: <what you did>`
3. Push after every 2-3 commits
4. After committing, output `<ralph>ROTATE</ralph>` for fresh context

**Progress tracking:**
- Mark criteria complete by changing `[ ]` to `[x]` in this file
- Update `.ralph/progress.md` with accomplishments
- When ALL criteria show `[x]`: output `<ralph>COMPLETE</ralph>`
- If stuck 3+ times on same issue: output `<ralph>GUTTER</ralph>`
