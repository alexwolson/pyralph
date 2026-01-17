---
task: Enhance CLI with comprehensive Rich features
completion_criteria:
  - Live progress display for ralph run command with spinner, iteration count, provider, token usage, elapsed time
  - Live-updating criteria checklist during ralph run
  - Status command shows Rich table for completion criteria with checkmarks/crosses
  - Status command shows progress bar with percentage
  - Status command shows panel with task summary and metadata
  - Interview experience uses styled panels for AI questions
  - Interview renders markdown in responses
  - Interview uses rich.prompt with history support
  - Log viewing has syntax-highlighted code blocks
  - Log viewing has colored log levels
  - Log viewing has paginated output for long logs
  - Provider display shows table of available providers and status
  - Provider display shows visual indicator for current/next provider in rotation
  - Error handling uses Rich tracebacks
  - Error handling shows styled error panels with helpful messages
  - Visual polish with rule separators between sections
  - Consistent color theme across all commands
  - All existing tests pass
max_iterations: 30
test_command: "make test"
---

# Task: Enhance CLI with Comprehensive Rich Features

Transform the pyralph CLI from functional to polished using Rich library features. The goal is to create a beautiful, informative, and professional command-line experience.

## Success Criteria

The task is complete when ALL of the following are true:

### Live Progress Display (`ralph run`)
- [x] Live progress display for ralph run command with spinner, iteration count, provider, token usage, elapsed time
- [x] Live-updating criteria checklist during ralph run

### Status Command Upgrade
- [x] Status command shows Rich table for completion criteria with checkmarks/crosses
- [x] Status command shows progress bar with percentage
- [x] Status command shows panel with task summary and metadata

### Interview Experience
- [x] Interview experience uses styled panels for AI questions
- [x] Interview renders markdown in responses
- [x] Interview uses rich.prompt with history support

### Log Viewing
- [x] Log viewing has syntax-highlighted code blocks
- [x] Log viewing has colored log levels
- [x] Log viewing has paginated output for long logs

### Provider Display
- [x] Provider display shows table of available providers and status
- [x] Provider display shows visual indicator for current/next provider in rotation

### Error Handling
- [x] Error handling uses Rich tracebacks
- [x] Error handling shows styled error panels with helpful messages

### Visual Polish
- [ ] Visual polish with rule separators between sections
- [ ] Consistent color theme across all commands

### Tests
- [ ] All existing tests pass

## Constraints

- Do NOT add typing animation effects for AI responses
- Use Rich library features already available (Rich is already a dependency)
- Maintain backward compatibility with existing CLI commands
- Keep the code clean and well-organized - consider creating a `ui.py` or `display.py` module for Rich components
- Ensure the UI degrades gracefully if terminal doesn't support Rich features

## Key Files to Modify

- `src/ralph/cli.py` - Main CLI commands
- `src/ralph/loop.py` - Main execution loop (for live display)
- `src/ralph/interview.py` - Interview flow
- `src/ralph/interview_turns.py` - Interview turn handling
- `src/ralph/providers/` - Provider display enhancements

## Rich Features to Use

- `rich.progress.Progress` - For progress bars and spinners
- `rich.live.Live` - For live-updating displays
- `rich.table.Table` - For tabular data
- `rich.panel.Panel` - For boxed content
- `rich.prompt.Prompt` - For styled prompts with history
- `rich.syntax.Syntax` - For syntax-highlighted code
- `rich.traceback` - For beautiful tracebacks
- `rich.rule.Rule` - For visual separators
- `rich.markdown.Markdown` - For markdown rendering (already imported)
- `rich.console.Console` - Central console instance (already used)

---

## Ralph Instructions

### Before Starting Work

1. Read `.ralph/guardrails.md` for rules and constraints
2. Read `.ralph/progress.md` for what's been done
3. Check this file for the next unchecked criterion

### Working Protocol

1. Work on ONE criterion at a time (the first unchecked one)
2. Make changes, test them, and verify they work
3. Run the test command: `make test`
4. Commit your changes with a descriptive message
5. Update `.ralph/progress.md` with what you did
6. Check off the completed criterion in this file
7. Commit the progress update

### Git Commit Protocol

- Commit after completing each criterion
- Use descriptive commit messages that explain what was done
- Include the criterion text in the commit message

### If You Get Stuck

- Document the issue in `.ralph/progress.md`
- Add any learnings to `.ralph/guardrails.md`
- The next agent (or provider rotation) will pick up from your commits

### Important Notes

- State is stored in git, not in your memory
- Each iteration should make incremental progress
- If tests fail, fix them before moving on
- Keep changes focused on the current criterion
