---
task: Improve Ralph prompting to encourage regular guardrails.md updates without file bloat
completion_criteria:
  - Prompts encourage proactive guardrail updates (not just on failure)
  - Prompts encourage consolidation/refinement of existing guardrails
  - Clear triggers defined for when to add vs update guardrails
  - Verification agent also suggests guardrails when finding issues
  - Guardrails format supports easy consolidation
  - All existing tests pass
max_iterations: 15
test_command: "make test"
---

# Task: Improve Guardrails Update Prompting

Ralph agents should proactively update `.ralph/guardrails.md` with lessons learned, but the file shouldn't grow unbounded. The prompting needs to encourage both adding new guardrails AND consolidating/refining existing ones.

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] Main prompt (`build_prompt`) includes a dedicated section for guardrails management that encourages proactive updates
- [ ] Prompt defines clear triggers for guardrail updates: test failures, gotchas discovered, successful patterns worth remembering, approach changes
- [ ] Prompt encourages agents to consolidate similar guardrails (e.g., merge 3 similar signs into 1 comprehensive one)
- [ ] Prompt suggests reviewing guardrails.md periodically and removing/merging redundant entries
- [ ] Verification prompt (`build_verification_prompt`) encourages adding guardrails when verification fails
- [ ] All existing tests pass (`make test`)

## Context

Current state in `src/ralph/prompts.py`:
- Guardrails only mentioned in "Learning from Failures" section (lines 155-167)
- Only triggered "when something fails"
- No mention of consolidation or maintenance
- Format exists but doesn't encourage refinement

Desired behavior:
- Agents should add guardrails when they learn something useful (not just failures)
- Agents should consolidate similar guardrails to prevent bloat
- Verification agents should suggest guardrails when they find issues
- The guardrails format should support easy consolidation (maybe with tags or categories)

## Constraints

- Don't change the core Ralph flow or signals
- Keep prompts concise - don't add walls of text
- Maintain backward compatibility with existing guardrails.md format
- Focus on `src/ralph/prompts.py` - that's where the prompts live

---
## Ralph Instructions

**Read these files FIRST:**
1. `RALPH_TASK.md` - This file (your task)
2. `.ralph/guardrails.md` - Lessons from past failures
3. `.ralph/progress.md` - What's been done

**Git Protocol:**
- Commit after completing each criterion
- Use descriptive commit messages: `ralph: <what you did>`
- Push every 2-3 commits
- After committing, output `<ralph>ROTATE</ralph>` for fresh context

**Progress Tracking:**
- Mark criteria complete by changing `[ ]` to `[x]` in this file
- Update `.ralph/progress.md` with accomplishments

**Signals:**
- `<ralph>COMPLETE</ralph>` - All criteria checked
- `<ralph>ROTATE</ralph>` - After commits, get fresh context
- `<ralph>GUTTER</ralph>` - Stuck 3+ times on same issue
