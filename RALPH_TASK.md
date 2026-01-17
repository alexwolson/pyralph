---
task: Pass workspace directory to CLI providers to eliminate cd prefix commands
completion_criteria:
  - BaseProvider.get_command() accepts workspace parameter
  - All providers pass directory flag to their CLI tool
  - loop.py passes workspace to get_command()
  - Tests pass
max_iterations: 10
test_command: "pytest tests/ -v"
---

# Task: Pass Workspace Directory to CLI Providers

The agent currently has to prefix every shell command with `cd /path/to/project &&` because the CLI tools don't know which directory they're working in. Fix this by passing the workspace path to each provider so they can use their directory flag.

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] `BaseProvider.get_command()` signature updated to accept `workspace: Path` parameter
- [ ] `ClaudeProvider.get_command()` adds `--directory` flag with workspace path
- [ ] `CursorProvider.get_command()` adds appropriate directory flag (check cursor-agent docs)
- [ ] `CodexProvider.get_command()` adds `--cwd` flag with workspace path
- [ ] `GeminiProvider.get_command()` adds appropriate directory flag (check gemini CLI docs)
- [ ] `loop.py` updated to pass `workspace` when calling `provider.get_command()`
- [ ] All existing tests pass

## Constraints

- Keep changes minimal - this is a simple plumbing change
- Don't over-engineer - just add the directory flag to each provider
- If a CLI tool doesn't support a directory flag, document it and skip that provider

## Files to Modify

- `src/ralph/providers/base.py` - Update abstract method signature
- `src/ralph/providers/claude.py` - Add --directory flag
- `src/ralph/providers/cursor.py` - Add directory flag
- `src/ralph/providers/codex.py` - Add --cwd flag
- `src/ralph/providers/gemini.py` - Add directory flag
- `src/ralph/loop.py` - Pass workspace to get_command()

---
## Ralph Instructions

You are an autonomous development agent using the Ralph methodology.

### FIRST: Read State Files

Before doing anything:
1. Read `RALPH_TASK.md` - your task and completion criteria
2. Read `.ralph/guardrails.md` - lessons from past failures (FOLLOW THESE)
3. Read `.ralph/progress.md` - what's been accomplished

### Git Protocol (Critical)

Ralph's strength is state-in-git, not LLM memory. Commit early and often:

1. After completing each criterion, commit your changes
2. After any significant code change: commit with descriptive message
3. Push after every 2-3 commits: `git push`
4. After committing, signal for fresh context: output `<ralph>ROTATE</ralph>`

### Task Execution

1. Work on the next unchecked criterion (look for `[ ]`)
2. Run tests after changes: `pytest tests/ -v`
3. **Mark completed criteria**: Edit RALPH_TASK.md and change `[ ]` to `[x]`
4. Update `.ralph/progress.md` with what you accomplished
5. When ALL criteria show `[x]`: output `<ralph>COMPLETE</ralph>`
6. If stuck 3+ times on same issue: output `<ralph>GUTTER</ralph>`
