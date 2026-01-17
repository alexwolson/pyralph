---
task: Implement agent-to-user question mechanism via file-based communication
completion_criteria:
  - Agent can write questions to .ralph/question.md and emit <ralph>QUESTION</ralph> signal
  - Loop detects QUESTION signal and pauses execution
  - Loop reads and displays question from .ralph/question.md using Rich panel
  - Loop prompts user for answer using wait_for_user_input() with timeout
  - User's answer is written to .ralph/answer.md
  - On timeout, loop continues without answer (agent proceeds with best guess)
  - Agent prompt includes instructions about question mechanism and using it sparingly
  - Question/answer files are cleaned up appropriately between iterations
  - All new code has corresponding tests
max_iterations: 20
test_command: "make test"
---

# Task: Agent-to-User Question Mechanism

Implement a file-based mechanism that allows the agent to ask questions of the user during execution. This reuses the interview infrastructure but operates during agent runs rather than before them.

## Success Criteria

The task is complete when ALL of the following are true:

- [x] Agent can write questions to `.ralph/question.md` and emit `<ralph>QUESTION</ralph>` signal
- [x] Loop detects QUESTION signal in agent output and pauses execution
- [x] Loop reads and displays question from `.ralph/question.md` using Rich panel (similar to interview display)
- [x] Loop prompts user for answer using `wait_for_user_input()` with timeout
- [x] User's answer is written to `.ralph/answer.md` for the agent to read
- [x] On timeout without user answer, loop continues (agent proceeds with best guess - no failure/rotation)
- [x] Agent prompt in `loop.py:build_prompt()` includes instructions about the question mechanism and emphasizes using it sparingly
- [x] Question/answer files are cleaned up appropriately (e.g., question.md removed after answer written, or both cleaned at iteration start)
- [x] All new code has corresponding tests

## Implementation Notes

### Signal Flow
1. Agent writes question to `.ralph/question.md`
2. Agent outputs `<ralph>QUESTION</ralph>` signal
3. `loop.py` detects signal (similar to existing `<ralph>DONE</ralph>` detection)
4. Loop pauses, reads `.ralph/question.md`, displays with Rich
5. Loop calls `wait_for_user_input()` (from `interview_turns.py`) with timeout
6. Answer written to `.ralph/answer.md`
7. Agent continues and can read answer file

### Key Files to Modify
- `src/ralph/loop.py` - Add QUESTION signal detection and handling
- `src/ralph/parser.py` - May need to parse QUESTION signal (check existing signal parsing)
- `src/ralph/ui.py` - May need new display function for questions (or reuse interview panels)
- `src/ralph/interview_turns.py` - Reuse `wait_for_user_input()` 

### Reuse from Interview
- `wait_for_user_input()` for prompting
- Rich panel styling for display
- Timeout handling patterns

## Constraints

- Do NOT use stdin/stdout for the question content - only for the answer prompt
- Question mechanism should be non-blocking on timeout (continue, don't fail)
- Keep the interface simple - single question/answer, not multi-turn conversation
- Prompt instructions should emphasize sparingly (e.g., "only ask when genuinely stuck and human input would significantly help")

---
## Ralph Instructions

Read these files at the start of each iteration:
- `RALPH_TASK.md` (this file) - for task definition and unchecked criteria
- `.ralph/progress.md` - for what was accomplished in previous iterations
- `.ralph/guardrails.md` - for mistakes to avoid

### Git Protocol
1. Make small, focused commits as you work
2. Commit message should describe what was done
3. Update `.ralph/progress.md` with what you accomplished
4. Check off completed criteria in this file

### Working Style
1. Focus on ONE unchecked criterion at a time
2. Write tests for new functionality
3. Run `make test` to verify changes
4. If stuck for more than 2-3 attempts on the same issue, note it in progress.md

### Completion
When all criteria are checked, output: `<ralph>DONE</ralph>`
