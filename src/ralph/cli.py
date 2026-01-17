"""CLI entry point for Ralph."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ralph import __version__, git_utils, interview, loop, state, task
from ralph.debug import setup_logging

console = Console()


def print_version(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """Print version and exit."""
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"ralph {__version__}")
    ctx.exit()


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show version and exit.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose debug output.",
)
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Ralph Wiggum - Autonomous development loop.

    Runs LLM providers in a loop to complete coding tasks autonomously.
    """
    # Store verbose flag in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    
    # Setup logging based on verbose flag
    setup_logging(verbose=verbose)
    
    # If no subcommand is given, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
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
@click.option(
    "--warn-threshold",
    type=int,
    default=72_000,
    help="Token count at which to warn about context size",
    show_default=True,
)
@click.option(
    "--rotate-threshold",
    type=int,
    default=80_000,
    help="Token count at which to trigger context rotation",
    show_default=True,
)
@click.option(
    "--timeout",
    type=int,
    default=300,
    help="Timeout in seconds for provider operations",
    show_default=True,
)
@click.pass_context
def run(
    ctx: click.Context,
    project_dir: Path,
    iterations: int,
    branch: Optional[str],
    pr: bool,
    once: bool,
    instruction: Optional[str],
    warn_threshold: int,
    rotate_threshold: int,
    timeout: int,
) -> None:
    """Run the Ralph development loop on PROJECT_DIR.

    If RALPH_TASK.md is missing, will interview you to create it.
    Automatically rotates between available providers on failure or gutter.
    """
    verbose = ctx.obj.get("verbose", False)
    
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
    if verbose:
        console.print("Verbose:   Yes")
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
        signal = loop.run_single_iteration(
            project_dir, provider, 1,
            warn_threshold=warn_threshold,
            rotate_threshold=rotate_threshold,
            timeout=timeout,
        )
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
                warn_threshold=warn_threshold,
                rotate_threshold=rotate_threshold,
                timeout=timeout,
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️[/yellow] Interrupted by user.")
            # Commit current progress before exiting
            if git_utils.has_uncommitted_changes(project_dir):
                console.print("[dim]Committing current progress...[/dim]")
                git_utils.commit_changes(project_dir, "ralph: interrupted - saving progress")
                console.print("[green]✓[/green] Progress saved.")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]❌[/red] Error: {e}")
            # Log error before exiting
            state.log_progress(project_dir, f"**Error**: {e}")
            sys.exit(1)


@main.command()
@click.argument(
    "project_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.pass_context
def status(ctx: click.Context, project_dir: Path) -> None:
    """Show task progress for PROJECT_DIR without running the loop.

    Displays criteria count, completion percentage, and current provider availability.
    """
    # Validate it's a git repo
    if not git_utils.is_git_repo(project_dir):
        console.print(
            f"[red]❌[/red] {project_dir} is not a git repository."
        )
        sys.exit(1)

    task_file = project_dir / "RALPH_TASK.md"

    # Check if task file exists
    if not task_file.exists():
        console.print(f"[yellow]⚠️[/yellow] No RALPH_TASK.md found in {project_dir}")
        console.print("Run [bold]ralph run {project_dir}[/bold] to create a task.")
        sys.exit(1)

    # Parse task file
    try:
        task_data = task.parse_task_file(task_file)
    except Exception as e:
        console.print(f"[red]❌[/red] Error parsing {task_file}: {e}")
        sys.exit(1)

    # Get task info from frontmatter
    frontmatter = task_data.get("frontmatter", {})
    task_name = frontmatter.get("task", "Unnamed task")
    max_iterations = frontmatter.get("max_iterations", 20)

    # Count criteria
    done, total = task.count_criteria(task_file)
    completion_status = task.check_completion(task_file)
    
    # Calculate percentage
    if total > 0:
        percentage = (done * 100) // total
    else:
        percentage = 0

    # Detect providers
    from ralph.providers import detect_available_providers
    
    available_providers = detect_available_providers()
    provider_names = [p.cli_tool if hasattr(p, 'cli_tool') else str(type(p).__name__) for p in available_providers]

    # Display status
    console.print("\n[bold]📋 Ralph Task Status[/bold]")
    console.print("")
    console.print(f"[bold]Task:[/bold] {task_name}")
    console.print(f"[bold]Path:[/bold] {project_dir}")
    console.print("")
    
    # Progress bar
    if total > 0:
        bar_width = 30
        filled = (done * bar_width) // total
        empty = bar_width - filled
        bar = "█" * filled + "░" * empty
        
        # Color based on completion
        if completion_status == "COMPLETE":
            bar_color = "green"
            status_icon = "✅"
        elif percentage >= 50:
            bar_color = "yellow"
            status_icon = "🔄"
        else:
            bar_color = "cyan"
            status_icon = "🔄"
        
        console.print(f"[bold]Progress:[/bold] [{bar_color}]{bar}[/{bar_color}] {done}/{total} ({percentage}%) {status_icon}")
    else:
        console.print("[bold]Progress:[/bold] No criteria defined")
    
    console.print("")
    console.print(f"[bold]Completion:[/bold] {completion_status}")
    console.print(f"[bold]Max iterations:[/bold] {max_iterations}")
    console.print("")
    console.print(f"[bold]Available providers:[/bold] {', '.join(provider_names) if provider_names else '[red]None[/red]'}")
    
    if not provider_names:
        console.print("\n[yellow]⚠️[/yellow] No providers available. Install cursor-agent, claude, gemini, or codex.")
    
    console.print("")


if __name__ == "__main__":
    main()
