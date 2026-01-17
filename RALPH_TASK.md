---
task: Fix task archiving and rename cursor-agent to agent CLI
completion_criteria:
  - Archived task files are committed to git after being moved to .ralph/completed/
  - CursorProvider uses "agent" as CLI tool (not "cursor-agent")
  - BaseProvider has get_display_name() method returning user-facing name
  - CursorProvider.get_display_name() returns "cursor"
  - All user-facing output uses display name instead of CLI tool name
  - PROVIDERS dict in __init__.py uses "agent" key for CursorProvider
  - Error messages reference "agent" not "cursor-agent" for CLI installation
  - README.md updated to reflect "agent" command (if cursor-agent is mentioned)
  - All tests pass
max_iterations: 20
test_command: "pytest"
---

# Task: Fix task archiving and rename cursor-agent to agent CLI

Two separate improvements to Ralph:

## 1. Fix Task Archiving Git Commit

The `archive_completed_task()` function in `loop.py` moves completed RALPH_TASK.md files to `.ralph/completed/` but doesn't commit the change to git. Since Ralph's strength is state-in-git, the archived file should be committed.

**Current behavior**: Task file is moved locally but not committed
**Expected behavior**: After archiving, git commit the removal of RALPH_TASK.md and addition of the archived file

Location: `src/ralph/loop.py` - `archive_completed_task()` function and its call sites

## 2. Rename cursor-agent CLI to agent

The cursor-agent CLI tool has been renamed to just `agent` on the command line. Update Ralph to:
- Call `agent` instead of `cursor-agent` when invoking the CLI
- Display "cursor" (not "agent" or "cursor-agent") in user-facing output
- This requires adding a display name concept to providers

**Files to modify**:
- `src/ralph/providers/base.py` - Add `get_display_name()` method
- `src/ralph/providers/cursor.py` - Update CLI tool to "agent", display name to "cursor"
- `src/ralph/providers/__init__.py` - Update PROVIDERS dict key
- `src/ralph/providers/rotation.py` - Use display name for user output
- `src/ralph/loop.py` - Use display name for user output, keep CLI tool for debug logs
- `src/ralph/cli.py` - Use display name for user output
- `src/ralph/interview.py` - Use display name for user output
- Error messages that mention "cursor-agent" should say "agent"
- `README.md` - Update any cursor-agent references

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] Archived task files are committed to git after being moved to .ralph/completed/
- [ ] CursorProvider uses "agent" as CLI tool (not "cursor-agent")
- [ ] BaseProvider has get_display_name() method returning user-facing name
- [ ] CursorProvider.get_display_name() returns "cursor"
- [ ] All user-facing output uses display name instead of CLI tool name
- [ ] PROVIDERS dict in __init__.py uses "agent" key for CursorProvider
- [ ] Error messages reference "agent" not "cursor-agent" for CLI installation
- [ ] README.md updated to reflect "agent" command (if cursor-agent is mentioned)
- [ ] All tests pass

## Constraints

- Keep debug/log output using CLI tool names for technical accuracy
- User-facing console output should use friendly display names
- Don't break existing provider rotation logic
- Maintain backward compatibility for other providers (claude, gemini, codex)

---
## Ralph Instructions

Before doing anything:
1. Read `RALPH_TASK.md` - your task and completion criteria
2. Read `.ralph/guardrails.md` - lessons from past failures (FOLLOW THESE)
3. Read `.ralph/progress.md` - what's been accomplished
4. Read `.ralph/errors.log` - recent failures to avoid

## Git Protocol

Ralph's strength is state-in-git, not LLM memory. Commit early and often:

1. After completing each criterion, commit your changes
2. After any significant code change: commit with descriptive message
3. Before any risky refactor: commit current state as checkpoint
4. After committing, signal for fresh context: output `<ralph>ROTATE</ralph>`

## Task Execution

1. Work on the next unchecked criterion (look for `[ ]`)
2. Run tests after changes: `pytest`
3. Mark completed criteria: change `[ ]` to `[x]` in this file
4. Update `.ralph/progress.md` with what you accomplished
5. When ALL criteria show `[x]`: output `<ralph>COMPLETE</ralph>`
6. If stuck 3+ times on same issue: output `<ralph>GUTTER</ralph>`
