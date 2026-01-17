"""LLM-based interview to create RALPH_TASK.md."""

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown

from ralph.providers import get_provider_rotation

console = Console()


def analyze_project_context(project_dir: Path) -> str:
    """Analyze project directory to understand context."""
    context_lines = []
    
    # List important files
    key_files = []
    for pattern in ["package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Makefile", "README.md"]:
        files = list(project_dir.glob(pattern))
        key_files.extend(files)
    
    # List top-level directories
    dirs = [d.name for d in project_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    
    context_lines.append(f"Project directory: {project_dir}")
    context_lines.append(f"Key files found: {[f.name for f in key_files]}")
    context_lines.append(f"Top-level directories: {dirs}")
    
    # Read README if available
    readme = project_dir / "README.md"
    if readme.exists():
        readme_preview = readme.read_text(encoding="utf-8")[:500]  # First 500 chars
        context_lines.append(f"\nREADME.md preview:\n{readme_preview}")
    
    return "\n".join(context_lines)


def build_interview_prompt(project_dir: Path) -> str:
    """Build the interview prompt for cursor-agent."""
    context = analyze_project_context(project_dir)
    
    prompt = f"""You are helping create a RALPH_TASK.md file for autonomous development using the Ralph Wiggum technique.

## What is Ralph Wiggum?

Ralph is an autonomous development technique. In its purest form, Ralph is a Bash loop that continuously feeds prompts to an LLM agent:

```
while :; do cat PROMPT.md | claude-code ; done
```

**Key principles of Ralph:**

1. **State-in-Git, not LLM memory**: Ralph's strength comes from storing all state in git commits. Each agent iteration reads state files (RALPH_TASK.md, .ralph/guardrails.md, .ralph/progress.md) and commits progress back to git. Commits ARE memory - if an agent fails or is rotated, the next agent picks up from the last commit.

2. **Deterministically bad in an undeterministic world**: Ralph has known defects, but these are identifiable and resolvable through prompt engineering and guardrails. When Ralph makes a mistake, you add a "sign" (guardrail) that teaches future agents what to avoid.

3. **Iterative refinement**: Ralph works in iterations. Each iteration:
   - Reads state files to understand the task and previous progress
   - Works on the next unchecked criterion in RALPH_TASK.md
   - Commits changes with descriptive messages
   - Updates progress tracking
   - Can be rotated to a fresh agent if stuck or context runs low

4. **Provider rotation**: If an agent gets stuck or hits issues, Ralph automatically rotates to a different LLM provider to continue the work.

5. **Learning from failures**: When something goes wrong, Ralph learns by adding guardrails (".ralph/guardrails.md") that prevent future agents from repeating the same mistakes. This is like "tuning a guitar" - each failure makes Ralph better.

6. **Requires faith and eventual consistency**: Building with Ralph requires patience and belief in eventual consistency. It may take wrong turns, but through guardrails and iteration, it eventually succeeds.

**What you're creating:**

The RALPH_TASK.md file you create will be the central task definition that Ralph agents read and update. It must have:
- Clear, testable completion criteria (as checkboxes)
- A test command (if applicable)
- All the information an autonomous agent needs to work independently

The agent will read this file, work through criteria one by one, check them off as complete, and commit progress back to git.

**Important: Ralph handles large tasks autonomously**

- **DO NOT** refuse to create a task file because it seems "too large" or complex
- **DO NOT** ask the user to break down tasks into smaller phases - Ralph works iteratively through large tasks
- **DO create** the task file even if it has many criteria (10, 20, or more)
- **DO include** multiple phases or sub-tasks as separate checkboxes if helpful, but don't require the user to define phases
- Large refactors, rewrites, and migrations are exactly what Ralph is designed for - the iterative process with guardrails handles complexity
- If a task has logical phases, you can organize criteria by phase, but still create ONE task file that covers everything

The user wants a task file created, not consultation on task scoping. Create it based on their requirements.

---

Context:
{context}

Your job:
1. **Analyze the project context first** - Read key files (package.json, pyproject.toml, README.md, etc.) to understand:
   - Language/framework being used
   - Project structure and patterns
   - Existing code style and conventions
   - Test setup (if any)

2. **Start the conversation** - Summarize what you found and ask the user targeted questions to understand:
   - What they want to accomplish (task goal)
   - Success criteria (specific, testable checkboxes)
   - Test command (if applicable)
   - Technology constraints
   - Any additional context

3. **Adapt your questions** - Based on their responses, ask follow-up questions to clarify:
   - Ensure criteria are specific and testable
   - Verify understanding of the project structure
   - Confirm any constraints or preferences

**CRITICAL: Do NOT refuse large tasks**
- **NEVER** say a task is "too large" or "too complex" for a single Ralph task
- **NEVER** ask the user to break down tasks into phases before creating a task file
- **ALWAYS** create the task file even if it has 10, 20, or 30+ criteria - Ralph works iteratively through large tasks
- Large refactors, rewrites, migrations, and architectural changes are exactly what Ralph is designed for
- If the task has natural phases, you can organize criteria by phase, but still create ONE comprehensive task file
- Ralph's iterative approach with guardrails and git commits handles complexity - that's its strength
- The user expects autonomy - create the task file based on their requirements, not consultation on scoping

4. **Generate the task file** - When you have enough information (don't wait for "perfect" scoping):
   - Write RALPH_TASK.md to the project root
   - Include frontmatter YAML with: task, completion_criteria (list), max_iterations (default 20), test_command (if applicable)
   - Include markdown body with task description and checkboxes for each criterion
   - Add standard Ralph instructions section
   - After writing the file, output: `<ralph>DONE</ralph>`

Format for RALPH_TASK.md:
```yaml
---
task: [Brief description]
completion_criteria:
  - [Criterion 1]
  - [Criterion 2]
max_iterations: 20
test_command: "[command if applicable]"
---

# Task: [Task Name]

[Task description]

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Constraints

[Any constraints or notes]

---
## Ralph Instructions

[Standard instructions about reading state files, git protocol, etc.]
```

Start by analyzing the project context and then ask your first question to the user.
"""
    return prompt


def extract_task_file_from_message(text: str, project_dir: Path) -> Optional[Path]:
    """Extract task file content from LLM message if it contains it."""
    # Look for markdown code blocks with RALPH_TASK.md content
    # This is a fallback - ideally the LLM will use writeToolCall
    
    # Check if text contains frontmatter pattern
    if "---" in text and "task:" in text.lower():
        # Try to extract the content between markdown code blocks
        lines = text.split("\n")
        in_code_block = False
        content_lines = []
        
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or (not in_code_block and ("---" in line or line.strip().startswith("#") or "- [ ]" in line)):
                content_lines.append(line)
        
        if content_lines:
            task_file = project_dir / "RALPH_TASK.md"
            task_file.write_text("\n".join(content_lines), encoding="utf-8")
            return task_file
    
    return None


def create_task_file(project_dir: Path, initial_instruction: Optional[str] = None) -> None:
    """Conduct LLM-based interview and create RALPH_TASK.md with provider rotation.
    
    Uses a temporary markdown file to accumulate the conversation, running each
    turn as a fresh subprocess to avoid stdin/stdout synchronization issues.
    
    Args:
        project_dir: Project directory to create task file in
        initial_instruction: Optional initial instruction from user to start the interview
    """
    task_file = project_dir / "RALPH_TASK.md"
    
    if task_file.exists():
        console.print("[yellow]⚠️[/yellow] RALPH_TASK.md already exists. Skipping interview.")
        return
    
    # Detect available providers and create rotation manager
    provider_rotation = get_provider_rotation()
    if not provider_rotation.providers:
        console.print("[red]❌[/red] No LLM providers available. Please install cursor-agent, claude, gemini, or codex.")
        raise Exception("No LLM providers available for interview")
    
    console.print("\n[bold cyan]🤖 Starting LLM interview to create RALPH_TASK.md...[/bold cyan]")
    console.print("[dim]The AI will analyze your project and ask questions to understand your task.[/dim]\n")
    
    console.print("[dim]📋 Analyzing project structure and context...[/dim]")
    initial_prompt = build_interview_prompt(project_dir)
    console.print("[dim]✓ Project context analyzed[/dim]\n")
    
    # Create temporary conversation file in .ralph directory
    ralph_dir = project_dir / ".ralph"
    ralph_dir.mkdir(exist_ok=True)
    conversation_file = ralph_dir / "interview.md"
    
    # Initialize conversation file with initial prompt
    # If user provided an initial instruction, add it as the user's first message
    conversation_content = initial_prompt
    if initial_instruction:
        conversation_content = initial_prompt + "\n\n---\n\nUser: " + initial_instruction + "\n\nYou now have the user's task description. Please proceed to create the RALPH_TASK.md file based on this instruction. Ask any clarifying questions if needed, but remember: create the task file even for large tasks - Ralph works iteratively."
    
    conversation_file.write_text(conversation_content, encoding="utf-8")
    
    # Try providers until one succeeds
    max_attempts = len(provider_rotation.providers)
    attempt = 0
    
    while attempt < max_attempts:
        provider = provider_rotation.get_current()
        provider_name = provider_rotation.get_provider_name()
        
        if attempt == 0:
            console.print(f"[dim]🔌 Using LLM provider: {provider_name}[/dim]")
        else:
            console.print(f"[cyan]🔄 Trying LLM provider: {provider_name}[/cyan]")
        
        try:
            console.print("[bold green]💬 Interview started! The AI will ask questions...[/bold green]\n")
            
            # Import turn-based helpers
            from ralph.interview_turns import run_single_turn, wait_for_user_input, append_user_response
            
            # Conversation loop using temporary file
            turn = 0
            max_turns = 20  # Prevent infinite loops
            
            while turn < max_turns:
                turn += 1
                
                # Run one turn: send conversation to provider, get response
                task_file_created, last_message = run_single_turn(
                    provider, conversation_file, project_dir
                )
                
                # Check if task file was created
                if task_file.exists():
                    console.print(f"[green]✓[/green] Task file ready: {task_file}")
                    # Clean up conversation file
                    if conversation_file.exists():
                        conversation_file.unlink()
                    return
                
                # If task file created via tool call, check again
                if task_file_created:
                    if task_file.exists():
                        console.print(f"[green]✓[/green] Task file ready: {task_file}")
                        if conversation_file.exists():
                            conversation_file.unlink()
                        return
                
                # If we got a completion sigil but no file, check for extraction
                if last_message and ("---" in last_message and "task:" in last_message.lower()):
                    extracted = extract_task_file_from_message(last_message, project_dir)
                    if extracted and extracted.exists():
                        console.print(f"[green]✅[/green] Task file extracted from conversation.\n")
                        if conversation_file.exists():
                            conversation_file.unlink()
                        return
                
                # Process exited, task file not created - wait for user input
                # Only wait if we got a message (AI asked a question)
                if last_message:
                    # Wait for user response
                    user_response = wait_for_user_input()
                    
                    if not user_response.strip():
                        console.print("[yellow]⚠️[/yellow] Empty response. Continuing...")
                        continue
                    
                    # Append user response to conversation file
                    append_user_response(conversation_file, user_response)
                else:
                    # No response from AI, break and try next provider
                    break
            
            # Conversation ended without creating task file
            console.print(f"[yellow]⚠️[/yellow] Provider {provider_name} did not create task file after {turn} turns. Rotating...")
            
        except Exception as e:
            # Provider error - rotate to next provider
            console.print(f"[yellow]⚠️[/yellow] Provider {provider_name} failed: {e}. Rotating...")
            
            # Clean up conversation file on error
            if conversation_file.exists():
                conversation_file.unlink()
        
        # Rotate to next provider
        next_provider = provider_rotation.rotate()
        attempt += 1
        
        if next_provider and attempt < max_attempts:
            next_name = provider_rotation.get_provider_name()
            console.print(f"[cyan]🔄[/cyan] Trying provider: {next_name}\n")
        else:
            break
    
    # Clean up conversation file
    if conversation_file.exists():
        conversation_file.unlink()
    
    # All providers exhausted
    if not task_file.exists():
        console.print("[red]❌[/red] Interview completed but RALPH_TASK.md was not created.")
        console.print("[yellow]⚠️[/yellow] All providers were tried. Please create RALPH_TASK.md manually.")
        raise Exception("RALPH_TASK.md was not created during interview with any provider")