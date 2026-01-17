---
task: Make pyralph globally installable on macOS via uv tool
completion_criteria:
  - Makefile exists with install target that uses uv tool install
  - Makefile has update target that reinstalls/upgrades the tool
  - Running make install installs ralph command globally
  - Running make update updates to latest version from repo
  - ralph command works from any directory after installation
  - README documents the global installation method
max_iterations: 10
test_command: "make install && which ralph && ralph --help"
---

# Task: Make pyralph globally installable on macOS

Make the `ralph` CLI installable system-wide on macOS so it can be run from any directory. Use `uv tool install` for isolated global installation. Provide Makefile targets for easy install and update.

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] Makefile exists at project root with `install` target using `uv tool install`
- [ ] Makefile has `update` target that reinstalls/upgrades the tool
- [ ] Running `make install` successfully installs `ralph` command globally
- [ ] Running `make update` updates to the latest version from the repo
- [ ] `ralph` command is accessible from any directory after installation
- [ ] README.md documents the global installation method with uv tool

## Technical Context

- Package is already properly configured in `pyproject.toml` with entry point `ralph = "ralph.cli:main"`
- Use `uv tool install` which installs into an isolated environment but makes CLI available globally
- `uv tool install .` installs from local repo
- `uv tool install . --force` or `uv tool upgrade` for updates
- uv tools go to `~/.local/bin` by default (ensure this is in PATH)

## Constraints

- Use `uv` tooling (not pipx)
- Command name should remain `ralph`
- Keep existing development install methods (pip install -e ., uv sync) working
- Makefile targets should be simple and self-documenting

---
## Ralph Instructions

**Before starting work:**
1. Read `.ralph/guardrails.md` if it exists for project-specific rules
2. Read `.ralph/progress.md` if it exists for context on previous work
3. Check which criteria are already marked complete above

**Working protocol:**
- Work on ONE unchecked criterion at a time
- After completing a criterion, check it off: `- [ ]` → `- [x]`
- Commit changes with descriptive message referencing the criterion
- Update `.ralph/progress.md` with what was done

**Git protocol:**
- Commit after each meaningful change
- Use clear commit messages: "feat: add Makefile with install target"
- Never force push or rewrite history

**If stuck:**
- Document the blocker in `.ralph/progress.md`
- Move to the next criterion if possible
- The next agent iteration will pick up from your commits
