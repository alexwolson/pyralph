---
task: Improve pyralph robustness and functionality
completion_criteria:
  - Remove hardcoded debug log paths and implement proper configurable logging
  - Add comprehensive test suite with pytest
  - Write complete README documentation
  - Add --version flag to CLI
  - Add --verbose/--debug flag for detailed output
  - Add status subcommand to check task progress
  - Extract duplicated debug logging code into shared module
  - Make token thresholds configurable via CLI or config
  - Improve error handling consistency across modules
  - Add timeout support for provider operations
  - Add retry logic for git operations
  - Improve graceful shutdown handling
  - Add type hints where missing
max_iterations: 25
test_command: "uv run pytest -v"
---

# Task: Improve pyralph Robustness and Functionality

Make pyralph more robust, maintainable, and user-friendly by addressing technical debt, adding missing features, and improving code quality.

## Success Criteria

The task is complete when ALL of the following are true:

### Phase 1: Critical Cleanup

- [x] Remove hardcoded debug log paths from `loop.py` and `rotation.py` - replace with proper configurable logging using Python's logging module or optional file output
- [x] Extract duplicated `_debug_log` function from `loop.py` and `rotation.py` into a shared `debug.py` module (or remove entirely if replaced with logging)

### Phase 2: Testing

- [ ] Create `tests/` directory with pytest configuration in `pyproject.toml`
- [ ] Add unit tests for `task.py` (parsing, checkbox counting, completion check)
- [ ] Add unit tests for `tokens.py` (threshold calculations, health emoji)
- [ ] Add unit tests for `gutter.py` (failure tracking, write thrashing detection)
- [ ] Add unit tests for `git_utils.py` (mocked subprocess calls)
- [ ] Add integration test for CLI help and version output
- [ ] All tests pass with `uv run pytest -v`

### Phase 3: CLI Improvements

- [ ] Add `--version` flag that displays package version from pyproject.toml
- [ ] Add `--verbose` / `-v` flag that enables detailed debug output
- [ ] Add `ralph status <project_dir>` subcommand that shows task progress without running the loop (displays criteria count, completion percentage, current provider availability)

### Phase 4: Configuration & Flexibility

- [ ] Make token thresholds (WARN_THRESHOLD, ROTATE_THRESHOLD) configurable via `--warn-threshold` and `--rotate-threshold` CLI options
- [ ] Add `--timeout` CLI option for provider operation timeout (default 300 seconds)
- [ ] Document all CLI options in README

### Phase 5: Robustness

- [ ] Add retry logic (3 attempts with exponential backoff) to git operations in `git_utils.py`
- [ ] Add timeout handling to subprocess calls in `loop.py` (terminate and rotate on timeout)
- [ ] Improve error handling: log errors before re-raising, don't silently swallow important exceptions
- [ ] Handle KeyboardInterrupt gracefully - commit current progress before exiting
- [ ] Add explicit UTF-8 encoding to all file operations

### Phase 6: Documentation

- [ ] Write comprehensive README.md with: project description, installation, quick start, CLI usage, how Ralph works, provider requirements, contributing guidelines

## Constraints

- Maintain Python 3.11+ compatibility
- Keep existing CLI interface backward-compatible (new flags are additive)
- Use `pytest` for testing (add to dev dependencies)
- Don't add heavy dependencies - keep the project lightweight
- Provider implementations should remain pluggable

## Technical Notes

- The project uses `uv` for package management and `hatchling` for builds
- Providers: cursor-agent, claude, gemini, codex
- State files: RALPH_TASK.md, .ralph/guardrails.md, .ralph/progress.md, .ralph/errors.log, .ralph/activity.log

---

## Ralph Instructions

### Before Each Work Session

1. Read `RALPH_TASK.md` to understand remaining criteria
2. Read `.ralph/guardrails.md` for lessons from past failures
3. Read `.ralph/progress.md` to see what's been done
4. Read `.ralph/errors.log` for recent issues to avoid

### Git Protocol

Ralph's memory is git. Commit frequently:

1. After completing each criterion: `git add -A && git commit -m "ralph: <what you did>"`
2. After any significant code change: commit immediately
3. Before risky changes: commit as checkpoint
4. Push every 2-3 commits: `git push`

### Working on Criteria

1. Find the next unchecked `- [ ]` criterion
2. Implement the change
3. Run tests: `uv run pytest -v`
4. If tests pass, mark criterion complete: change `[ ]` to `[x]`
5. Commit with descriptive message
6. Move to next criterion

### Signals

- When ALL criteria are `[x]`: output `<ralph>COMPLETE</ralph>`
- If stuck on same issue 3+ times: output `<ralph>GUTTER</ralph>`

### Adding Guardrails

When something fails, add a Sign to `.ralph/guardrails.md`:

```
### Sign: [Name]
- **Trigger**: When this happens
- **Instruction**: Do this instead
- **Added after**: Iteration N - what went wrong
```
