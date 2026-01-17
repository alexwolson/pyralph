---
task: Add verification phase after RALPH COMPLETE
completion_criteria:
  - Add VERIFY_PASS and VERIFY_FAIL signals to parser.py
  - Create build_verification_prompt() function in loop.py
  - Add verification phase in run_ralph_loop() after COMPLETE detected
  - Verification agent uses different provider than completing agent
  - Verification agent runs test_command and checks results
  - Verification agent reviews code quality and completeness
  - On VERIFY_FAIL agent can uncheck criteria or add new ones to RALPH_TASK.md
  - On VERIFY_FAIL loop continues with fresh agent
  - On VERIFY_PASS task is archived and loop exits
  - Add max_verification_failures config (default 3) to prevent infinite loops
  - Add tests for verification signals in parser
  - Add tests for verification phase in loop
  - All existing tests pass
max_iterations: 25
test_command: "make test"
---

# Task: Add Verification Phase After RALPH COMPLETE

After an agent signals `<ralph>COMPLETE</ralph>` and checkboxes are verified, spin up an independent verification agent that double-checks whether the task is truly complete. If it disagrees, it updates RALPH_TASK.md and the loop continues.

## Context

Currently in `loop.py`:
- On COMPLETE signal + all checkboxes checked → immediately archive and exit
- No independent verification of actual task completion

The goal is to add a "trust but verify" step where a *different* provider reviews the work before finalizing.

## Success Criteria

The task is complete when ALL of the following are true:

- [x] Add VERIFY_PASS and VERIFY_FAIL signals to parser.py (detect `<ralph>VERIFY_PASS</ralph>` and `<ralph>VERIFY_FAIL</ralph>`)
- [x] Create `build_verification_prompt()` function in loop.py that instructs the verification agent to:
  - Run the test_command from RALPH_TASK.md frontmatter
  - Review code quality and completeness
  - Check that all requirements in the original task are actually met
  - Output `<ralph>VERIFY_PASS</ralph>` if satisfied, or `<ralph>VERIFY_FAIL</ralph>` if not
- [x] Add verification phase in `run_ralph_loop()` after COMPLETE is detected (before archiving)
- [x] Verification agent uses a **different** provider than the one that completed (call `provider_rotation.rotate()` before verification)
- [x] Verification agent runs test_command and checks results
- [x] Verification agent reviews code quality and completeness against original requirements
- [x] On VERIFY_FAIL: agent can uncheck criteria in RALPH_TASK.md (change `[x]` back to `[ ]`) or add new criteria if issues are found
- [x] On VERIFY_FAIL: loop continues with fresh agent iteration (increment iteration, continue loop)
- [x] On VERIFY_PASS: task is archived and loop exits normally (existing archive_completed_task flow)
- [x] Add `max_verification_failures` config (default 3) - if verification fails 3 times consecutively, give up and warn user
- [x] Add tests for VERIFY_PASS and VERIFY_FAIL signal detection in parser
- [x] Add tests for verification phase flow in loop
- [x] All existing tests pass (`make test`)

## Implementation Notes

### Signal Detection (parser.py)

Add to `process_line()` function, similar to existing COMPLETE/GUTTER/QUESTION detection:

```python
if "<ralph>VERIFY_PASS</ralph>" in text:
    state.log_activity(workspace, "✅ Verification PASSED")
    return "VERIFY_PASS"

if "<ralph>VERIFY_FAIL</ralph>" in text:
    state.log_activity(workspace, "❌ Verification FAILED")
    return "VERIFY_FAIL"
```

### Verification Prompt (loop.py)

Create `build_verification_prompt(workspace, iteration)` that:
1. Reads RALPH_TASK.md to get original requirements
2. Reads test_command from frontmatter
3. Instructs agent to independently verify completion
4. Tells agent to output VERIFY_PASS or VERIFY_FAIL
5. On VERIFY_FAIL, agent should explain why and update RALPH_TASK.md

### Verification Phase (loop.py)

After detecting COMPLETE + all checkboxes checked:
1. Don't archive yet
2. Rotate to different provider
3. Run verification iteration with verification prompt
4. Handle VERIFY_PASS → archive and exit
5. Handle VERIFY_FAIL → continue loop
6. Track verification_failure_count, give up after max_verification_failures

### Provider Rotation for Verification

```python
# Get a different provider for verification
completing_provider = provider_rotation.get_provider_name()
provider_rotation.rotate()
verification_provider = provider_rotation.get_current()
```

## Constraints

- Don't break existing functionality - all current tests must pass
- Keep the verification prompt concise but thorough
- Verification agent should have full context (read state files)
- Log verification attempts to progress.md for auditability

---
## Ralph Instructions

You are an autonomous agent using the Ralph methodology. Before starting:

1. **Read state files first:**
   - `RALPH_TASK.md` - this file, your task definition
   - `.ralph/guardrails.md` - lessons from past failures (FOLLOW THESE)
   - `.ralph/progress.md` - what's been accomplished
   - `.ralph/errors.log` - recent failures to avoid

2. **Git protocol:**
   - Commit after each criterion: `git add -A && git commit -m 'ralph: <description>'`
   - Push every 2-3 commits: `git push`
   - After committing, signal: `<ralph>ROTATE</ralph>` for fresh context

3. **Task execution:**
   - Work on the next unchecked `[ ]` criterion
   - Run tests after changes: `make test`
   - Mark completed: change `[ ]` to `[x]` in this file
   - Update `.ralph/progress.md` with what you did

4. **Signals:**
   - All criteria `[x]`: output `<ralph>COMPLETE</ralph>`
   - Stuck 3+ times: output `<ralph>GUTTER</ralph>`
   - Need clarification: write to `.ralph/question.md`, output `<ralph>QUESTION</ralph>`

5. **Learning from failures:**
   - Check `.ralph/errors.log` for patterns
   - Add guardrails to `.ralph/guardrails.md` when you learn something

Begin by reading the state files.
