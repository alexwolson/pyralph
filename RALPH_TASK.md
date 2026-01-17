---
task: Fix infinite verification loop
completion_criteria:
  - Verification failure triggers a cooldown or state flag to prevent immediate re-verification
  - After VERIFY_FAIL, the loop runs at least one regular work iteration before allowing another verification
  - If verification agent doesn't uncheck criteria, the loop doesn't infinitely re-verify
  - Add test coverage for the verification loop behavior
  - All existing tests pass
max_iterations: 20
test_command: "make test"
---

# Task: Fix Infinite Verification Loop

## Problem

The Ralph loop enters an infinite verification cycle when:
1. All criteria are checked → triggers verification
2. Verification fails (VERIFY_FAIL) but agent doesn't uncheck any criteria
3. Next iteration sees all criteria still checked → triggers verification again
4. Repeat forever

## Root Cause

In `loop.py`, after a `VERIFY_FAIL`:
- The loop increments iteration and continues
- On next iteration, `run_single_iteration` runs
- But if criteria are still all checked, `completion_status == "COMPLETE"` 
- This immediately triggers another verification (line 629-631)

The verification prompt asks the agent to uncheck criteria, but there's no enforcement. If the agent doesn't comply, we loop forever.

## Solution Approach

Add a state variable (e.g., `just_failed_verification`) that:
1. Gets set to `True` after a `VERIFY_FAIL`
2. Prevents `should_verify` from being set on the next iteration
3. Gets reset to `False` after a regular work iteration completes
4. Ensures at least one work iteration between verification attempts

Alternative: Force uncheck at least one criterion programmatically when verification fails (but this changes semantics - agent should control criteria).

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] Verification failure triggers a cooldown or state flag to prevent immediate re-verification
- [ ] After VERIFY_FAIL, the loop runs at least one regular work iteration before allowing another verification
- [ ] If verification agent doesn't uncheck criteria, the loop doesn't infinitely re-verify
- [ ] Add test coverage for the verification loop behavior
- [ ] All existing tests pass

## Files to Modify

- `src/ralph/loop.py` - Main loop logic with verification handling

## Constraints

- Keep the existing verification behavior intact (VERIFY_PASS completes, VERIFY_FAIL continues)
- Don't change the signal detection logic in parser.py
- Maintain the `max_verification_failures` limit functionality
- Solution should be minimal and targeted

---
## Ralph Instructions

Before doing anything:
1. Read `RALPH_TASK.md` - your task and completion criteria
2. Read `.ralph/guardrails.md` - lessons from past failures (FOLLOW THESE)
3. Read `.ralph/progress.md` - what's been accomplished

### Git Protocol

1. After completing each criterion, commit your changes
2. Before any risky refactor: commit current state as checkpoint
3. After committing, signal for fresh context: output `<ralph>ROTATE</ralph>`

### Task Execution

1. Work on the next unchecked criterion in RALPH_TASK.md (look for `[ ]`)
2. Run tests after changes: `make test`
3. Mark completed criteria: Edit RALPH_TASK.md and change `[ ]` to `[x]`
4. Update `.ralph/progress.md` with what you accomplished
5. When ALL criteria show `[x]`: output `<ralph>COMPLETE</ralph>`
6. If stuck 3+ times on same issue: output `<ralph>GUTTER</ralph>`
