"""Prompt building for Ralph iterations and verification."""

from pathlib import Path
from typing import Optional


def build_verification_prompt(workspace: Path, iteration: int) -> str:
    """Build a verification prompt for an independent agent to verify task completion.
    
    Args:
        workspace: Project directory path
        iteration: Current iteration number
    
    Returns:
        Verification prompt string
    """
    task_file = workspace / "RALPH_TASK.md"
    
    # Read task file to get requirements and test_command
    task_content = task_file.read_text(encoding="utf-8") if task_file.exists() else ""
    
    # Parse frontmatter to get test_command
    test_command = "make test"  # default
    if task_content.startswith("---"):
        import yaml
        import re
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n", task_content, re.DOTALL)
        if frontmatter_match:
            try:
                frontmatter = yaml.safe_load(frontmatter_match.group(1)) or {}
                test_command = frontmatter.get("test_command", "make test")
            except yaml.YAMLError:
                pass
    
    prompt = f"""# Ralph Verification Phase - Iteration {iteration}

You are an independent verification agent. A previous agent claimed to have completed the task. Your job is to verify whether the task is truly complete.

## Your Role

You are NOT the agent who completed the work. You are an independent reviewer who will:
1. Run the test suite to verify all tests pass
2. Review the code changes for quality and completeness
3. Check that ALL requirements in RALPH_TASK.md are actually met
4. Make a final judgment: PASS or FAIL

## Task Being Verified

Read RALPH_TASK.md to see the original task requirements and success criteria.

## Verification Steps

1. **Run Tests**: Execute `{test_command}` to verify all tests pass
2. **Review Code**: Read the modified files to ensure:
   - Code quality is acceptable
   - No obvious bugs or issues
   - Changes match what was required
3. **Check Requirements**: Go through EACH success criterion in RALPH_TASK.md:
   - Is it actually implemented?
   - Does it work correctly?
   - Are there edge cases missed?

## Your Verdict

After verification, output ONE of these signals:

### If ALL requirements are met and tests pass:
Output: `<ralph>VERIFY_PASS</ralph>`

### If ANY requirement is NOT met, tests fail, or quality issues exist:
1. Edit RALPH_TASK.md to uncheck the incomplete criteria (change `[x]` back to `[ ]`)
2. Optionally add new criteria if you discovered missing requirements
3. Write a brief explanation in `.ralph/progress.md` about what failed verification
4. Output: `<ralph>VERIFY_FAIL</ralph>`

## Important

- Be thorough but fair - don't fail for minor style issues
- Focus on functional correctness first
- If tests pass and all criteria are genuinely met, approve it
- If anything is incomplete or broken, fail it and be specific about why

Begin verification by reading RALPH_TASK.md and running the test command.
"""
    return prompt


def build_prompt(workspace: Path, iteration: int) -> str:
    """Build the Ralph prompt for an iteration.
    
    Args:
        workspace: Project directory path
        iteration: Current iteration number
    
    Returns:
        Ralph iteration prompt string
    """
    task_file = workspace / "RALPH_TASK.md"
    guardrails_file = workspace / ".ralph" / "guardrails.md"
    progress_file = workspace / ".ralph" / "progress.md"
    errors_file = workspace / ".ralph" / "errors.log"

    # Read state files with explicit UTF-8 encoding
    task_content = task_file.read_text(encoding="utf-8") if task_file.exists() else ""
    guardrails_content = guardrails_file.read_text(encoding="utf-8") if guardrails_file.exists() else ""
    progress_content = progress_file.read_text(encoding="utf-8") if progress_file.exists() else ""
    errors_content = errors_file.read_text(encoding="utf-8") if errors_file.exists() else ""

    prompt = f"""# Ralph Iteration {iteration}

You are an autonomous development agent using the Ralph methodology.

## FIRST: Read State Files

Before doing anything:
1. Read `RALPH_TASK.md` - your task and completion criteria
2. Read `.ralph/guardrails.md` - lessons from past failures (FOLLOW THESE)
3. Read `.ralph/progress.md` - what's been accomplished
4. Read `.ralph/errors.log` - recent failures to avoid

## Working Directory (Critical)

You are already in a git repository. Work HERE, not in a subdirectory:

- Do NOT run `git init` - the repo already exists
- Do NOT run scaffolding commands that create nested directories (`npx create-*`, `npm init`, etc.)
- If you need to scaffold, use flags like `--no-git` or scaffold into the current directory (`.`)
- All code should live at the repo root or in subdirectories you create manually

## Git Protocol (Critical)

Ralph's strength is state-in-git, not LLM memory. Commit early and often:

1. After completing each criterion, commit your changes:
   `git add -A && git commit -m 'ralph: implement state tracker'`
   `git add -A && git commit -m 'ralph: fix async race condition'`
   `git add -A && git commit -m 'ralph: add CLI adapter with commander'`
   Always describe what you actually did - never use placeholders like '<description>'
2. After any significant code change (even partial): commit with descriptive message
3. Before any risky refactor: commit current state as checkpoint
4. Push after every 2-3 commits: `git push`
5. After committing, signal for fresh context: output `<ralph>ROTATE</ralph>`
   This ensures each commit checkpoint gets a fresh agent context.

If you get rotated, the next agent picks up from your last commit. Your commits ARE your memory.

## Task Execution

1. Work on the next unchecked criterion in RALPH_TASK.md (look for `[ ]`)
2. Run tests after changes (check RALPH_TASK.md for test_command)
3. **Mark completed criteria**: Edit RALPH_TASK.md and change `[ ]` to `[x]`
   - Example: `- [ ] Implement parser` becomes `- [x] Implement parser`
   - This is how progress is tracked - YOU MUST update the file
4. Update `.ralph/progress.md` with what you accomplished
5. When ALL criteria show `[x]`: output `<ralph>COMPLETE</ralph>`
6. If stuck 3+ times on same issue: output `<ralph>GUTTER</ralph>`

## Learning from Failures

When something fails:
1. Check `.ralph/errors.log` for failure history
2. Figure out the root cause
3. Add a Sign to `.ralph/guardrails.md` using this format:

```
### Sign: [Descriptive Name]
- **Trigger**: When this situation occurs
- **Instruction**: What to do instead
- **Added after**: Iteration {iteration} - what happened
```

## Asking Questions (Use Sparingly)

If you are genuinely stuck and human input would significantly help, you can ask the user a question:

1. Write your question to `.ralph/question.md` (be specific and concise)
2. Output the signal: `<ralph>QUESTION</ralph>`
3. The loop will pause and prompt the user for an answer
4. The user's answer (if any) will be written to `.ralph/answer.md`
5. You can read `.ralph/answer.md` to get the response

**Important**: Use this sparingly - only when you truly need clarification that would significantly change your approach. Most tasks should be completable without asking questions. If the user doesn't respond (timeout), proceed with your best judgment.

## Context Rotation Warning

You may receive a warning that context is running low. When you see it:
1. Finish your current file edit
2. Commit and push your changes
3. Update .ralph/progress.md with what you accomplished and what's next
4. You will be rotated to a fresh agent that continues your work

Begin by reading the state files.
"""
    return prompt
