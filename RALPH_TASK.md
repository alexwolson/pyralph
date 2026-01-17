---
task: Fix Rich UI integration and implement comprehensive terminal display
completion_criteria:
  - Live progress display with spinner, iteration count, provider, tokens, elapsed time works correctly during ralph run
  - Live-updating criteria checklist updates in real-time as criteria are completed
  - Parser console output integrates with Live display without conflicts
  - Rich table for completion criteria in status command works
  - Progress bar with percentage works in status command
  - Task summary panel displays correctly
  - Styled panels for AI questions in interview work
  - Markdown rendering in interview responses works
  - Rich.prompt with history support for interview input
  - Syntax-highlighted code blocks in logs command
  - Colored log levels display correctly
  - Paginated log output works
  - Provider table with availability status works
  - Visual indicator for current/next provider in rotation works
  - Rich tracebacks for errors work
  - Styled error panels with helpful messages work
  - Rule separators between sections work
  - Consistent color theme across all commands
max_iterations: 30
test_command: "python -m pytest tests/ -v && ralph status . && ralph providers"
---

# Task: Fix Rich UI Integration and Implement Terminal Display

The Ralph CLI has Rich UI components defined in `ui.py` but they're not working correctly in practice due to integration issues.

## Root Cause (Already Identified)

The main bug is in `parser.py` which has a global `console = Console()` and makes direct `console.print()` calls. These conflict with `RalphLiveDisplay` which uses `rich.live.Live`. Direct console prints during a Live context cause display interference.

**Solution approach:**
1. Pass the live display or a callback to the parser so it can route output through the live display
2. Use `Live.console.print()` for output during live display, or
3. Batch console output and emit through the live display's update mechanism
4. Consider using `Live(console=console, redirect_stdout=True, redirect_stderr=True)` options

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] Live progress display with spinner, iteration count, provider, tokens, elapsed time works correctly during ralph run
- [ ] Live-updating criteria checklist updates in real-time as criteria are completed
- [ ] Parser console output integrates with Live display without conflicts
- [ ] Rich table for completion criteria in status command works
- [ ] Progress bar with percentage works in status command
- [ ] Task summary panel displays correctly
- [ ] Styled panels for AI questions in interview work
- [ ] Markdown rendering in interview responses works
- [ ] Rich.prompt with history support for interview input
- [ ] Syntax-highlighted code blocks in logs command
- [ ] Colored log levels display correctly
- [ ] Paginated log output works
- [ ] Provider table with availability status works
- [ ] Visual indicator for current/next provider in rotation works
- [ ] Rich tracebacks for errors work
- [ ] Styled error panels with helpful messages work
- [ ] Rule separators between sections work
- [ ] Consistent color theme across all commands

## Key Files

- `src/ralph/ui.py` - RalphLiveDisplay class and UI components
- `src/ralph/parser.py` - Stream parser with conflicting console.print() calls
- `src/ralph/loop.py` - Main loop that creates and uses RalphLiveDisplay
- `src/ralph/cli.py` - CLI commands (status, providers, logs, run)
- `src/ralph/interview.py` - Interview flow for task creation
- `src/ralph/interview_turns.py` - Interview turn handling

## Implementation Notes

1. **Fix parser.py console conflict**: Either:
   - Remove the global console and pass output through callbacks
   - Use the Live display's console for prints during live context
   - Queue messages and display them in the Live update

2. **Test manually**: After changes, run `ralph run .` on a test project to verify the live display works

3. **Interview Rich.prompt**: Look at `rich.prompt.Prompt` for history support

4. **Syntax highlighting in logs**: Use `rich.syntax.Syntax` for code blocks

## Constraints

- Maintain backward compatibility with existing CLI behavior
- Don't break the core loop functionality while fixing UI
- Use the existing THEME dict for consistent colors
- Keep the codebase clean - don't add unnecessary dependencies

---
## Ralph Instructions

You are an autonomous development agent. Before doing anything:

1. Read `RALPH_TASK.md` - your task and completion criteria
2. Read `.ralph/guardrails.md` - lessons from past failures (FOLLOW THESE)
3. Read `.ralph/progress.md` - what's been accomplished
4. Read `.ralph/errors.log` - recent failures to avoid

## Git Protocol

Ralph's strength is state-in-git, not LLM memory. Commit early and often:

1. After completing each criterion, commit:
   `git add -A && git commit -m 'ralph: <description>'`
2. After any significant code change: commit with descriptive message
3. Before any risky refactor: commit current state as checkpoint
4. Push after every 2-3 commits: `git push`
5. After committing, signal for fresh context: output `<ralph>ROTATE</ralph>`

## Task Execution

1. Work on the next unchecked criterion (look for `[ ]`)
2. Run tests after changes: `python -m pytest tests/ -v`
3. **Mark completed criteria**: Edit RALPH_TASK.md and change `[ ]` to `[x]`
4. Update `.ralph/progress.md` with what you accomplished
5. When ALL criteria show `[x]`: output `<ralph>COMPLETE</ralph>`
6. If stuck 3+ times on same issue: output `<ralph>GUTTER</ralph>`

## Signals

- `<ralph>ROTATE</ralph>` - Request fresh context (after commits)
- `<ralph>COMPLETE</ralph>` - All criteria done
- `<ralph>GUTTER</ralph>` - Stuck, need provider rotation
- `<ralph>QUESTION</ralph>` - Need human input (use sparingly)
