"""CLI entry point for Ralph."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install as install_rich_traceback

from ralph import __version__, git_utils, interview, loop, state, task
from ralph.debug import setup_logging
from ralph.ui import THEME

# Install Rich tracebacks for beautiful error display
install_rich_traceback(show_locals=False, width=100, word_wrap=True)

console = Console()


def show_error_panel(title: str, message: str, hint: Optional[str] = None) -> None:
    """Display a styled error panel with optional hint."""
    content = f"[bold]{message}[/bold]"
    if hint:
        content += f"\n\n[{THEME['muted']}]Hint: {hint}[/]"
    
    console.print()
    console.print(Panel(
        content,
        title=f"[bold {THEME['error']}]{title}[/]",
        border_style=THEME["error"],
        padding=(1, 2),
    ))
    console.print()


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
    """Ralph - Autonomous development loop.

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
        show_error_panel(
            "Not a Git Repository",
            f"{project_dir} is not a git repository.",
            "Ralph requires git for state persistence. Run 'git init' first."
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
        show_error_panel(
            "Task File Error",
            f"Failed to parse {task_file}",
            str(e)
        )
        sys.exit(1)

    # Initialize .ralph directory
    state.init_ralph_dir(project_dir)

    # Check if already complete
    completion_status = task.check_completion(task_file)
    if completion_status == "COMPLETE":
        console.print("[green]✓[/green] Task already complete! All criteria are checked.")
        sys.exit(0)

    # Validate PR flag
    if pr and not branch:
        show_error_panel(
            "Invalid Options",
            "--pr requires --branch",
            "Specify a branch name with --branch <name>"
        )
        sys.exit(1)

    # Show summary
    from rich.rule import Rule
    from ralph.providers import detect_available_providers
    
    available_providers = detect_available_providers()
    provider_names = [p.get_display_name() if hasattr(p, 'get_display_name') else p.cli_tool for p in available_providers]
    
    console.print()
    console.print(Rule(f"[bold {THEME['primary']}]Ralph[/]", style=THEME["primary"]))
    console.print()
    console.print(f"[{THEME['muted']}]Workspace:[/] {project_dir}")
    console.print(f"[{THEME['muted']}]Providers:[/] {', '.join(provider_names) if provider_names else 'None'}")
    console.print(f"[{THEME['muted']}]Max iter:[/]  {iterations}")
    if branch:
        console.print(f"[{THEME['muted']}]Branch:[/]    {branch}")
    if pr:
        console.print(f"[{THEME['muted']}]Open PR:[/]   Yes")
    if once:
        console.print(f"[{THEME['muted']}]Mode:[/]      Single iteration")
    if verbose:
        console.print(f"[{THEME['muted']}]Verbose:[/]   Yes")
    console.print()

    # Count criteria
    console.print(Rule("[bold]Progress[/bold]", style=THEME["muted"]))
    criteria_counts = task.count_criteria(task_file)
    done, total = criteria_counts
    remaining = total - done
    console.print(f"[{THEME['success'] if done == total else THEME['warning']}]{done} / {total}[/] criteria complete ({remaining} remaining)")
    console.print()

    # Run loop
    if once:
        from ralph.providers import get_provider_rotation
        
        provider_rotation = get_provider_rotation()
        if not provider_rotation.providers:
            show_error_panel(
                "No Providers Available",
                "No LLM providers found on your system.",
                "Install one of: agent (Cursor), claude, gemini, or codex"
            )
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
            console.print("\n[green]✓[/green] Task completed in single iteration!")
        else:
            console.print(f"\n[dim]Single iteration complete. {remaining} criteria remaining.[/]")
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
            console.print("\n[yellow]⚠[/yellow] Interrupted by user.")
            # Commit current progress before exiting
            if git_utils.has_uncommitted_changes(project_dir):
                console.print("[dim]Committing current progress...[/dim]")
                git_utils.commit_changes(project_dir, "ralph: interrupted - saving progress")
                console.print("[green]✓[/green] Progress saved.")
            sys.exit(1)
        except Exception as e:
            show_error_panel(
                "Execution Error",
                str(e),
                "Check .ralph/errors.log for details"
            )
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
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, TextColumn
    from rich.rule import Rule
    from rich.table import Table
    
    from ralph.ui import THEME, get_criteria_list
    
    # Validate it's a git repo
    if not git_utils.is_git_repo(project_dir):
        console.print(
            f"[{THEME['error']}]✗[/] {project_dir} is not a git repository."
        )
        sys.exit(1)

    task_file = project_dir / "RALPH_TASK.md"

    # Check if task file exists
    if not task_file.exists():
        console.print(f"[{THEME['warning']}]⚠[/] No RALPH_TASK.md found in {project_dir}")
        console.print(f"Run [bold]ralph run {project_dir}[/bold] to create a task.")
        sys.exit(1)

    # Parse task file
    try:
        task_data = task.parse_task_file(task_file)
    except Exception as e:
        console.print(f"[{THEME['error']}]✗[/] Error parsing {task_file}: {e}")
        sys.exit(1)

    # Get task info from frontmatter
    frontmatter = task_data.get("frontmatter", {})
    task_name = frontmatter.get("task", "Unnamed task")
    max_iterations = frontmatter.get("max_iterations", 20)
    test_command = frontmatter.get("test_command", "")

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
    provider_names = [p.get_display_name() if hasattr(p, 'get_display_name') else p.cli_tool for p in available_providers]

    # Print header
    console.print()
    console.print(Rule(f"[bold {THEME['primary']}]Ralph Task Status[/]", style=THEME["primary"]))
    console.print()
    
    # Task summary panel
    summary_text = f"[bold]{task_name}[/bold]\n"
    summary_text += f"[{THEME['muted']}]Path: {project_dir}[/]\n"
    summary_text += f"[{THEME['muted']}]Max iterations: {max_iterations}[/]"
    if test_command:
        summary_text += f"\n[{THEME['muted']}]Test command: {test_command}[/]"
    
    # Add completion status to panel
    if completion_status == "COMPLETE":
        status_text = f"[{THEME['success']}]✓ COMPLETE[/]"
    elif total > 0:
        remaining = total - done
        status_text = f"[{THEME['warning']}]{remaining} criteria remaining[/]"
    else:
        status_text = f"[{THEME['muted']}]No criteria defined[/]"
    
    summary_text += f"\n\n{status_text}"
    
    console.print(Panel(
        summary_text,
        title="[bold]Task Summary[/bold]",
        border_style=THEME["primary"],
        padding=(1, 2),
    ))
    console.print()
    
    # Progress bar with percentage
    if total > 0:
        # Determine color based on completion
        if completion_status == "COMPLETE":
            bar_color = THEME["success"]
        elif percentage >= 50:
            bar_color = THEME["warning"]
        else:
            bar_color = THEME["primary"]
        
        # Create a simple progress bar display
        progress = Progress(
            TextColumn("[bold]Progress[/bold]"),
            BarColumn(bar_width=40, complete_style=bar_color, finished_style=THEME["success"]),
            TextColumn(f"[{bar_color}]{done}/{total}[/] ({percentage}%)"),
            console=console,
            transient=False,
        )
        
        with progress:
            task_id = progress.add_task("progress", total=total, completed=done)
        
        console.print()
    
    # Criteria checklist table
    criteria = get_criteria_list(task_file)
    if criteria:
        console.print(Rule("[bold]Completion Criteria[/bold]", style=THEME["muted"]))
        console.print()
        
        criteria_table = Table(show_header=False, box=None, padding=(0, 1))
        criteria_table.add_column("Status", width=3)
        criteria_table.add_column("Criterion", overflow="fold")
        
        for text, is_checked in criteria:
            if is_checked:
                status_mark = f"[{THEME['success']}]✓[/]"
                style = THEME["muted"]
            else:
                status_mark = f"[{THEME['muted']}]○[/]"
                style = ""
            criteria_table.add_row(status_mark, f"[{style}]{text}[/]" if style else text)
        
        console.print(criteria_table)
        console.print()
    
    # Provider availability section
    console.print(Rule("[bold]Providers[/bold]", style=THEME["muted"]))
    console.print()
    
    if provider_names:
        provider_table = Table(show_header=True, box=None, padding=(0, 2))
        provider_table.add_column("Provider", style="bold")
        provider_table.add_column("Status")
        
        for name in provider_names:
            provider_table.add_row(name, f"[{THEME['success']}]available[/]")
        
        console.print(provider_table)
    else:
        console.print(f"[{THEME['warning']}]⚠[/] No providers available.")
        console.print(f"[{THEME['muted']}]Install agent, claude, gemini, or codex.[/]")
    
    console.print()


@main.command()
@click.pass_context
def providers(ctx: click.Context) -> None:
    """Show available LLM providers and their status.

    Displays a table of detected providers with availability status
    and indicates the current/next provider in the rotation order.
    """
    from rich.rule import Rule
    from rich.table import Table
    
    from ralph.providers import detect_available_providers, get_provider_rotation, PROVIDERS
    from ralph.ui import THEME
    
    console.print()
    console.print(Rule(f"[bold {THEME['primary']}]LLM Providers[/]", style=THEME["primary"]))
    console.print()
    
    # Get all known providers and which are available
    available = detect_available_providers()
    available_names = {p.get_display_name() if hasattr(p, 'get_display_name') else p.cli_tool for p in available}
    
    # Get rotation to show current/next
    rotation = None
    current_name = None
    if available:
        rotation = get_provider_rotation()
        if rotation.providers:
            current = rotation.get_current()
            current_name = current.get_display_name() if hasattr(current, 'get_display_name') else current.cli_tool
    
    # Build table
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("", width=3)  # Indicator column
    table.add_column("Provider", style="bold")
    table.add_column("CLI Tool")
    table.add_column("Status")
    table.add_column("Rotation")
    
    # Show all known providers
    all_providers = list(PROVIDERS.items())
    
    for cli_name, provider_class in all_providers:
        provider = provider_class()
        display_name = provider.get_display_name() if hasattr(provider, 'get_display_name') else cli_name
        
        is_available = display_name in available_names
        is_current = display_name == current_name
        
        # Indicator
        if is_current:
            indicator = f"[{THEME['accent']}]►[/]"
        elif is_available:
            indicator = f"[{THEME['success']}]●[/]"
        else:
            indicator = f"[{THEME['muted']}]○[/]"
        
        # Status
        if is_available:
            status = f"[{THEME['success']}]available[/]"
        else:
            status = f"[{THEME['muted']}]not found[/]"
        
        # Rotation position
        if is_available and rotation:
            try:
                idx = [p.get_display_name() if hasattr(p, 'get_display_name') else p.cli_tool 
                       for p in rotation.providers].index(display_name)
                if is_current:
                    rotation_text = f"[{THEME['accent']}]current[/]"
                elif idx == 1:
                    rotation_text = f"[{THEME['info']}]next[/]"
                else:
                    rotation_text = f"[{THEME['muted']}]#{idx + 1}[/]"
            except ValueError:
                rotation_text = f"[{THEME['muted']}]-[/]"
        else:
            rotation_text = f"[{THEME['muted']}]-[/]"
        
        table.add_row(indicator, display_name, cli_name, status, rotation_text)
    
    console.print(table)
    console.print()
    
    # Summary
    if available:
        console.print(f"[{THEME['success']}]✓[/] {len(available)} provider(s) available for rotation")
    else:
        console.print(f"[{THEME['warning']}]⚠[/] No providers available")
        console.print(f"[{THEME['muted']}]Install one of: agent, claude, gemini, codex[/]")
    
    console.print()


@main.command()
@click.argument(
    "project_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--errors",
    is_flag=True,
    default=False,
    help="Show errors.log instead of activity.log",
)
@click.option(
    "--lines",
    "-n",
    type=int,
    default=None,
    help="Show last N lines only (default: all)",
)
@click.option(
    "--no-pager",
    is_flag=True,
    default=False,
    help="Disable pagination (print all at once)",
)
@click.pass_context
def logs(ctx: click.Context, project_dir: Path, errors: bool, lines: int, no_pager: bool) -> None:
    """View activity or error logs for PROJECT_DIR.

    Shows syntax-highlighted, colorized log output with pagination.
    Use --errors to view errors.log instead of activity.log.
    """
    import re
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich.text import Text
    
    from ralph.ui import THEME
    
    ralph_dir = project_dir / ".ralph"
    
    if not ralph_dir.exists():
        console.print(f"[{THEME['warning']}]⚠[/] No .ralph directory found in {project_dir}")
        console.print(f"Run [bold]ralph run {project_dir}[/bold] first.")
        sys.exit(1)
    
    log_file = ralph_dir / ("errors.log" if errors else "activity.log")
    log_name = "Errors" if errors else "Activity"
    
    if not log_file.exists():
        console.print(f"[{THEME['warning']}]⚠[/] No {log_file.name} found")
        sys.exit(1)
    
    content = log_file.read_text(encoding="utf-8")
    log_lines = content.splitlines()
    
    # Apply --lines limit if specified
    if lines is not None and lines > 0:
        log_lines = log_lines[-lines:]
    
    # Color mapping for log levels (using Unicode symbols and text patterns)
    level_colors = {
        "●": THEME["success"],  # Will be colored based on context
        "✓": THEME["success"],
        "✗": THEME["error"],
        "⚠": THEME["warning"],
        "ROTATE": THEME["error"],
        "WARN": THEME["warning"],
    }
    
    def colorize_line(line: str) -> Text:
        """Apply colors based on log level indicators."""
        text = Text()
        
        # Check for timestamp pattern [HH:MM:SS]
        timestamp_match = re.match(r'^(\[[0-9:]+\])\s*(.*)$', line)
        if timestamp_match:
            timestamp, rest = timestamp_match.groups()
            text.append(timestamp, style=THEME["muted"])
            text.append(" ")
            line = rest
        
        # Check for session markers
        if line.startswith("═══") or line.startswith("Ralph Session"):
            text.append(line, style=f"bold {THEME['primary']}")
            return text
        
        if line.startswith("SESSION"):
            text.append(line, style=f"bold {THEME['accent']}")
            return text
        
        # Check for symbols and color accordingly
        found_color = None
        for symbol, color in level_colors.items():
            if symbol in line:
                found_color = color
                break
        
        # Special handling for ● symbol - check context to determine color
        if "●" in line:
            # Determine color based on surrounding context
            if "TOKENS" in line:
                # Token status line - check percentage
                import re
                pct_match = re.search(r'\((\d+)%\)', line)
                if pct_match:
                    pct = int(pct_match.group(1))
                    if pct < 60:
                        found_color = THEME["success"]
                    elif pct < 80:
                        found_color = THEME["warning"]
                    else:
                        found_color = THEME["error"]
                else:
                    found_color = THEME["success"]  # Default to green
            else:
                # Other uses - default to success
                found_color = THEME["success"]
        
        # Check for ROTATE/WARN keywords
        if "ROTATE" in line:
            found_color = THEME["error"]
        elif "WARN" in line:
            found_color = THEME["warning"]
        
        if found_color:
            text.append(line, style=found_color)
        else:
            text.append(line)
        
        return text
    
    def render_log_output():
        """Render the log output with colors."""
        # Print header
        console.print()
        console.print(Rule(f"[bold {THEME['primary']}]{log_name} Log[/]", style=THEME["primary"]))
        console.print(f"[{THEME['muted']}]{log_file}[/]")
        console.print()
        
        # Pattern to detect code blocks or shell commands with multi-line output
        in_code_block = False
        code_lines = []
        
        for line in log_lines:
            # Skip markdown headers in the log file
            if line.startswith("#") or line.startswith(">"):
                console.print(Text(line, style=THEME["muted"]))
                continue
            
            # Empty lines
            if not line.strip():
                console.print()
                continue
            
            # Check for multi-line shell output (heredoc in commit messages)
            if "<<'EOF'" in line or "<<EOF" in line:
                in_code_block = True
                console.print(colorize_line(line))
                continue
            
            if in_code_block:
                if line.strip() == "EOF" or line.endswith("EOF"):
                    in_code_block = False
                    console.print(Text(line, style=THEME["muted"]))
                else:
                    # Show code in code block style
                    console.print(Text(f"  {line}", style="italic"))
                continue
            
            # Regular log line
            console.print(colorize_line(line))
        
        console.print()
    
    # Use pager for long output
    if no_pager or len(log_lines) < 50:
        render_log_output()
    else:
        with console.pager(styles=True):
            render_log_output()


if __name__ == "__main__":
    main()
