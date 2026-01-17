# Ralph Wiggum

**Python implementation of the Ralph autonomous development loop.**

Ralph is an autonomous development technique that runs LLM agents in a loop to complete coding tasks iteratively. It stores all state in git commits, enabling seamless context rotation between agents and robust failure recovery.

## How Ralph Works

Ralph operates on a simple but powerful principle: **state-in-git, not LLM memory**.

```
while iteration < max_iterations:
    agent = get_provider()
    agent.run(RALPH_TASK.md)
    if task_complete:
        break
```

### Core Concepts

1. **State Files**: Ralph maintains state in files that agents read and update:
   - `RALPH_TASK.md` - Task definition with checkboxes for completion criteria
   - `.ralph/progress.md` - Log of what's been accomplished
   - `.ralph/guardrails.md` - Lessons learned from failures ("signs")
   - `.ralph/errors.log` - Recent error messages

2. **Git as Memory**: Every agent iteration commits progress to git. If an agent fails or context runs out, the next agent picks up from the last commit.

3. **Provider Rotation**: Ralph automatically rotates between available LLM providers (Cursor, Claude, Gemini, Codex) on failure or when context limits are reached.

4. **Guardrails**: When something goes wrong, Ralph learns by adding "signs" to guardrails.md that prevent future agents from repeating the same mistakes.

## Installation

### Prerequisites

- Python 3.11 or higher
- Git
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- At least one supported LLM provider CLI tool installed

### Global Install with uv tool (recommended)

Install `ralph` globally so it's available from any directory:

```bash
# Clone the repository
git clone https://github.com/yourusername/pyralph.git
cd pyralph

# Install globally
make install
```

This uses `uv tool install` to create an isolated environment while making the `ralph` command available system-wide in `~/.local/bin/`.

**Note:** Make sure `~/.local/bin` is in your PATH. Add this to your shell config if needed:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

To update to the latest version:

```bash
cd pyralph
git pull
make update
```

To uninstall:

```bash
make uninstall
```

### Development Install with uv

For development (editable install):

```bash
# Clone the repository
git clone https://github.com/yourusername/pyralph.git
cd pyralph

# Install with uv (local development)
uv sync

# Run ralph (requires uv run prefix)
uv run ralph --help
```

### Install with pip

```bash
pip install -e .
ralph --help
```

## Quick Start

1. **Navigate to your project directory** (must be a git repository):

```bash
cd /path/to/your/project
```

2. **Run Ralph**:

```bash
ralph run .
```

3. **If no RALPH_TASK.md exists**, Ralph will interview you to create one:
   - Answer the AI's questions about your task
   - It will generate a task file with completion criteria

4. **Watch Ralph work**:
   - Ralph runs iterations, checking off criteria as they're completed
   - Progress is committed to git after each significant change
   - When all criteria are checked, Ralph signals completion

## CLI Usage

### Main Commands

```bash
# Run the Ralph loop on a project
ralph run <project_dir>

# Check task status without running the loop
ralph status <project_dir>
```

### Global Options

```bash
ralph --version              # Show version
ralph --verbose / -v         # Enable verbose debug output
ralph --help                 # Show help
```

### Run Command Options

```bash
ralph run <project_dir> [OPTIONS]

Options:
  --iterations INTEGER       Maximum number of iterations [default: 20]
  --branch TEXT              Create and work on a new branch
  --pr                       Open PR when complete (requires --branch)
  --once                     Run single iteration only (for testing)
  --instruction TEXT         Initial instruction for task creation
  --warn-threshold INTEGER   Token count for context warning [default: 72000]
  --rotate-threshold INTEGER Token count to trigger rotation [default: 80000]
  --timeout INTEGER          Provider operation timeout in seconds [default: 300]
```

### Examples

```bash
# Run with custom iteration limit
ralph run ./my-project --iterations 50

# Create a feature branch and open PR when done
ralph run ./my-project --branch feature/add-auth --pr

# Run a single iteration for testing
ralph run ./my-project --once

# Start with an initial task instruction
ralph run ./my-project --instruction "Add user authentication with JWT tokens"

# Use custom token thresholds
ralph run ./my-project --warn-threshold 60000 --rotate-threshold 72000

# Check task progress without running
ralph status ./my-project
```

## Provider Requirements

Ralph supports multiple LLM providers. Install at least one:

### Cursor Agent (agent)

The Cursor IDE agent. Must have Cursor installed with agent mode enabled.

```bash
# Verify installation
which agent
```

### Claude (claude)

Anthropic's Claude CLI.

```bash
# Install via npm
npm install -g @anthropic-ai/claude-cli

# Or via pip
pip install anthropic
```

### Gemini (gemini)

Google's Gemini CLI.

```bash
# Install
pip install google-generativeai
```

### Codex (codex)

OpenAI's Codex CLI.

```bash
# Install
pip install openai
```

## RALPH_TASK.md Format

The task file defines what Ralph should accomplish:

```markdown
---
task: Brief description of the task
completion_criteria:
  - First criterion
  - Second criterion
max_iterations: 20
test_command: "pytest -v"
---

# Task: Task Name

Detailed task description.

## Success Criteria

The task is complete when ALL of the following are true:

- [ ] First criterion (checkboxes track progress)
- [ ] Second criterion
- [ ] Third criterion

## Constraints

- Any constraints or notes for the agent
```

## Configuration

### Token Thresholds

Control when Ralph warns about context size and rotates to fresh context:

- `--warn-threshold`: Token count at which to warn (default: 72,000)
- `--rotate-threshold`: Token count to trigger rotation (default: 80,000)

### Timeout

Control how long to wait for provider operations:

- `--timeout`: Seconds before timing out (default: 300)

### Verbose Mode

Enable detailed debug output:

```bash
ralph -v run ./my-project
```

## State Files

Ralph maintains state in the `.ralph/` directory:

| File | Purpose |
|------|---------|
| `progress.md` | Log of completed work and session history |
| `guardrails.md` | Lessons learned - "signs" that guide future iterations |
| `errors.log` | Recent error messages for debugging |
| `activity.log` | Real-time tool call logging |

## Signals

Agents can emit signals to communicate with Ralph:

- `<ralph>COMPLETE</ralph>` - Task is complete
- `<ralph>GUTTER</ralph>` - Agent is stuck, rotate to next provider
- `ROTATE` - Context limit reached, rotate to fresh context

## Contributing

Contributions are welcome! Here's how to get started:

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/pyralph.git
cd pyralph

# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest -v
```

### Running Tests

```bash
# Run all tests
uv run pytest -v

# Run specific test file
uv run pytest tests/test_cli.py -v

# Run with coverage
uv run pytest --cov=ralph
```

### Code Style

- Use type hints for all function signatures
- Follow PEP 8 style guidelines
- Add docstrings to public functions
- Keep the codebase lightweight - avoid heavy dependencies

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`uv run pytest -v`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Based on the Ralph Wiggum technique for autonomous development loops.
