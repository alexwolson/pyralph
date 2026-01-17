"""CLI entry point for Ralph."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ralph import git_utils, interview, loop, state, task

console = Console()


@click.command()
@click.argument(
    "project_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--iterations",
    type=int,
    default=20,
    help="Maximum number of iterations",
    show_default=True,
)
@click.option(
    "--branch",
    type=str,
    default=None,
    help="Create and work on a new branch",
)
@click.option(
    "--pr",
    is_flag=True,
    default=False,
    help="Open PR when complete (requires --branch)",
)
@click.option(
    "--once",
    is_flag=True,
    default=False,
    help="Run single iteration only (for testing)",
)
@click.option(
    "--instruction",
    type=str,
    default=None,
    help="Initial instruction for task creation (if RALPH_TASK.md doesn't exist)",
)
def main(
    project_dir: Path,
    iterations: int,
    branch: Optional[str],
    pr: bool,
    once: bool,
    instruction: Optional[str],
) -> None:
    """Ralph Wiggum - Autonomous development loop.

    Runs LLM providers in a loop on the specified project directory.
    If RALPH_TASK.md is missing, will interview you to create it.
    Automatically rotates between available providers on failure or gutter.
    """
    # Validate prerequisites
    if not git_utils.is_git_repo(project_dir):
        console.print(
            f"[red]❌[/red] {project_dir} is not a git repository. "
            "Ralph requires git for state persistence."
        )
        sys.exit(1)

    task_file = project_dir / "RALPH_TASK.md"

    # Interview user if task file missing
    if not task_file.exists():
        interview.create_task_file(project_dir, initial_instruction=instruction)

    # Validate task file
    try:
        task_data = task.parse_task_file(task_file)
    except Exception as e:
        console.print(f"[red]❌[/red] Error parsing {task_file}: {e}")
        sys.exit(1)

    # Initialize .ralph directory
    state.init_ralph_dir(project_dir)

    # Check if already complete
    completion_status = task.check_completion(task_file)
    if completion_status == "COMPLETE":
        console.print("[green]🎉[/green] Task already complete! All criteria are checked.")
        sys.exit(0)

    # Validate PR flag
    if pr and not branch:
        console.print(
            "[red]❌[/red] --pr requires --branch. Please specify a branch name."
        )
        sys.exit(1)

    # Show summary
    from ralph.providers import detect_available_providers
    
    available_providers = detect_available_providers()
    provider_names = [p.cli_tool if hasattr(p, 'cli_tool') else str(type(p).__name__) for p in available_providers]
    
    console.print("\n[bold]🐛 Ralph Wiggum: Autonomous Development Loop[/bold]")
    console.print("")
    console.print(f"Workspace: {project_dir}")
    console.print(f"Providers: {', '.join(provider_names) if provider_names else 'None'}")
    console.print(f"Max iter:  {iterations}")
    if branch:
        console.print(f"Branch:    {branch}")
    if pr:
        console.print("Open PR:   Yes")
    if once:
        console.print("Mode:      Single iteration")
    console.print("")

    # Count criteria
    criteria_counts = task.count_criteria(task_file)
    done, total = criteria_counts
    remaining = total - done
    console.print(f"Progress: {done} / {total} criteria complete ({remaining} remaining)")
    console.print("")

    # Run loop
    if once:
        from ralph.providers import get_provider_rotation
        
        provider_rotation = get_provider_rotation()
        if not provider_rotation.providers:
            console.print("[red]❌[/red] No LLM providers available. Please install cursor-agent, claude, gemini, or codex.")
            sys.exit(1)
        
        provider = provider_rotation.get_current()
        signal = loop.run_single_iteration(project_dir, provider, 1)
        completion_status = task.check_completion(task_file)
        if completion_status == "COMPLETE":
            console.print("\n[green]🎉[/green] Task completed in single iteration!")
        else:
            console.print(f"\n📋 Single iteration complete. {remaining} criteria remaining.")
    else:
        try:
            loop.run_ralph_loop(
                project_dir=project_dir,
                max_iterations=iterations,
                branch=branch,
                open_pr=pr,
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️[/yellow] Interrupted by user.")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]❌[/red] Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
