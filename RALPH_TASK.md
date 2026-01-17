---
task: General refactoring pass - extract modules, DRY up code, improve types
completion_criteria:
  - Extract signal constants into a signals.py module with an enum
  - Extract prompt building logic from loop.py into a prompts.py module
  - Extract archive functions from loop.py into an archive.py module
  - Consolidate run_single_iteration and run_verification_iteration shared logic
  - Add get_display_name() method to base provider class with default implementation
  - Consolidate YAML frontmatter parsing into a single utility function
  - Consolidate initial state file content into state.py only
  - Add comprehensive type hints to all public functions
  - Update all imports and usages after module extractions
  - All existing tests pass after refactoring
  - No regressions in CLI functionality
max_iterations: 25
test_command: "uv run pytest -v"
---

# Task: General Refactoring Pass

Perform a comprehensive refactoring of the pyralph codebase to improve code organization, reduce duplication, and enhance type safety.

## Success Criteria

The task is complete when ALL of the following are true:

- [x] Extract signal constants into a `src/ralph/signals.py` module with a `Signal` enum (COMPLETE, ROTATE, GUTTER, STUCK, etc.)
- [x] Extract prompt building logic from `loop.py` into a `src/ralph/prompts.py` module (build_prompt, build_verification_prompt, etc.)
- [x] Extract archive functions from `loop.py` into a `src/ralph/archive.py` module (archive_task, get_archive_path, etc.)
- [x] Consolidate `run_single_iteration` and `run_verification_iteration` shared logic into a common helper or unified function
- [x] Add `get_display_name()` method to `BaseProvider` class with default implementation, remove hasattr checks throughout codebase
- [x] Consolidate YAML frontmatter parsing into a single utility function in `parser.py`, update all call sites
- [x] Consolidate initial state file content (progress.md, guardrails.md templates) into `state.py` only, remove duplication in `loop.py`
- [ ] Add comprehensive type hints to all public functions in extracted modules
- [ ] Update all imports and usages throughout codebase after module extractions
- [ ] All existing tests pass after refactoring (`uv run pytest -v`)
- [ ] No regressions in CLI functionality (ralph commands still work)

## Constraints

- No need to maintain backwards API compatibility - internal function signatures can change
- Follow existing code style and patterns in the project
- Keep commits atomic and well-described (one logical change per commit)
- Update tests as needed to reflect refactored code structure

## Refactoring Details

### 1. Signals Module
Create `src/ralph/signals.py`:
- Define `Signal` enum with values: COMPLETE, ROTATE, GUTTER, STUCK, ABANDON
- Replace magic strings throughout codebase with enum values
- Update signal detection logic to use the enum

### 2. Prompts Module
Create `src/ralph/prompts.py`:
- Move `build_prompt()` from loop.py
- Move `build_verification_prompt()` from loop.py
- Move any prompt-related helper functions
- Keep prompt templates as module-level constants or in a templates dict

### 3. Archive Module
Create `src/ralph/archive.py`:
- Move `archive_task()` from loop.py
- Move `get_archive_path()` from loop.py
- Move any archive-related helpers

### 4. Iteration Consolidation
In `loop.py`:
- Identify shared code between `run_single_iteration` and `run_verification_iteration`
- Extract common logic into helper function(s) or unify into single parameterized function
- Target: reduce duplication by ~60%

### 5. Provider Display Name
In `src/ralph/providers/base.py`:
- Add `get_display_name()` method to `BaseProvider` with sensible default
- Remove all `hasattr(provider, 'get_display_name')` checks in codebase
- Update any provider subclasses as needed

### 6. YAML Parsing Consolidation
In `src/ralph/parser.py`:
- Ensure single `parse_frontmatter()` function handles all YAML parsing needs
- Update `build_verification_prompt()` and `task.py` to use this function
- Remove any duplicated parsing logic

### 7. State File Templates
In `src/ralph/state.py`:
- Consolidate all initial state file content (DEFAULT_PROGRESS_CONTENT, DEFAULT_GUARDRAILS_CONTENT)
- Remove duplicated template strings from `loop.py`
- Export templates for use by other modules

---
## Ralph Instructions

**Before each iteration:**
1. Read `.ralph/progress.md` to understand what's been done
2. Read `.ralph/guardrails.md` for any constraints or lessons learned
3. Read this file (RALPH_TASK.md) to find the next unchecked criterion

**During each iteration:**
1. Work on ONE unchecked criterion at a time
2. Make atomic commits with clear messages describing the change
3. Run tests frequently: `uv run pytest -v`
4. If tests fail, fix them before moving on

**After completing a criterion:**
1. Check off the completed criterion in this file (change `- [ ]` to `- [x]`)
2. Update `.ralph/progress.md` with what was accomplished
3. Commit all changes including the checkbox update

**If stuck:**
1. Add notes to `.ralph/guardrails.md` about what's blocking progress
2. Signal ROTATE to get a fresh perspective from another provider

**Completion:**
When ALL criteria are checked off, signal COMPLETE.
