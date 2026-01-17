"""Rich UI components for Ralph CLI."""

import time
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text
from rich.markup import escape

from ralph import tokens

# Consistent color theme
THEME = {
    "primary": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "muted": "dim",
    "accent": "magenta",
    "info": "blue",
}


class RalphLiveDisplay:
    """Live progress display for ralph run command.
    
    Shows: spinner, iteration count, provider, token usage, elapsed time.
    """

    def __init__(
        self,
        max_iterations: int,
        rotate_threshold: int = tokens.ROTATE_THRESHOLD,
        console: Optional[Console] = None,
    ):
        self.console = console or Console()
        self.max_iterations = max_iterations
        self.rotate_threshold = rotate_threshold
        
        # State
        self.current_iteration = 0
        self.provider_name = ""
        self.token_tracker: Optional[tokens.TokenTracker] = None
        self.start_time = time.time()
        self.status_message = "Starting..."
        self.criteria: List[Tuple[str, bool]] = []  # (text, is_checked)
        
        # Create progress display
        # Format theme colors but preserve {task.fields[...]} for Rich to handle
        primary_color = THEME["primary"]
        accent_color = THEME["accent"]
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn(f"[bold {primary_color}]Iteration {{task.fields[iteration]}}/{{task.fields[max_iter]}}[/]"),
            TextColumn("•"),
            TextColumn(f"[{accent_color}]{{task.fields[provider]}}[/]"),
            TextColumn("•"),
            TextColumn("{task.fields[tokens]}"),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )
        
        self._task_id: Optional[TaskID] = None
        self._live: Optional[Live] = None

    def _build_display(self) -> Group:
        """Build the complete live display."""
        components = []
        
        # Add progress bar
        components.append(self.progress)
        
        # Add criteria checklist if available
        if self.criteria:
            try:
                criteria_table = self._build_criteria_table()
                components.append(criteria_table)
            except Exception:
                # If there's any error building/measuring the criteria table
                # (e.g., MarkupError from malformed text), just skip it
                # This prevents the entire display from crashing
                pass
        
        return Group(*components)

    def _build_criteria_table(self) -> Table:
        """Build the criteria checklist table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Status", width=3)
        table.add_column("Criterion", overflow="fold")
        
        for text, is_checked in self.criteria:
            if is_checked:
                status = f"[{THEME['success']}]✓[/]"
                style = THEME["muted"]
            else:
                status = f"[{THEME['muted']}]○[/]"
                style = ""
            
            # Escape any markup-like patterns in the criterion text to prevent MarkupError
            # Rich's measurement system may parse Text objects as markup, so we escape first
            escaped_text = escape(text)
            
            # Create Text object with the escaped content
            if style:
                criterion_text = Text(escaped_text, style=style)
            else:
                criterion_text = Text(escaped_text)
            
            table.add_row(status, criterion_text)
        
        return table

    def _get_token_display(self) -> str:
        """Get formatted token usage display."""
        if not self.token_tracker:
            return f"[{THEME['muted']}]0 tokens[/]"
        
        current = self.token_tracker.calculate_tokens()
        health_indicator = self.token_tracker.get_health_emoji()
        pct = (current * 100) // self.rotate_threshold
        
        # Color based on usage
        if pct < 60:
            color = THEME["success"]
        elif pct < 80:
            color = THEME["warning"]
        else:
            color = THEME["error"]
        
        return f"{health_indicator} [{color}]{current:,}[/][{THEME['muted']}]/{self.rotate_threshold:,}[/]"

    def start(self) -> "RalphLiveDisplay":
        """Start the live display."""
        self._task_id = self.progress.add_task(
            "ralph",
            total=None,  # Indeterminate
            iteration=self.current_iteration,
            max_iter=self.max_iterations,
            provider=self.provider_name or "starting",
            tokens=self._get_token_display(),
        )
        
        # Build display with error handling for MarkupError
        try:
            display = self._build_display()
        except Exception as e:
            # If building display fails (e.g., MarkupError in criteria table),
            # fall back to just the progress bar
            from rich.errors import MarkupError
            if isinstance(e, MarkupError):
                display = Group(self.progress)
            else:
                raise
        
        self._live = Live(
            display,
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )
        self._live.start()
        return self

    def stop(self) -> None:
        """Stop the live display."""
        if self._live:
            self._live.stop()
            self._live = None

    def update(
        self,
        iteration: Optional[int] = None,
        provider: Optional[str] = None,
        token_tracker: Optional[tokens.TokenTracker] = None,
        status: Optional[str] = None,
        criteria: Optional[List[Tuple[str, bool]]] = None,
    ) -> None:
        """Update the live display with new values."""
        if iteration is not None:
            self.current_iteration = iteration
        if provider is not None:
            self.provider_name = provider
        if token_tracker is not None:
            self.token_tracker = token_tracker
        if status is not None:
            self.status_message = status
        if criteria is not None:
            self.criteria = criteria
        
        # Update progress task
        if self._task_id is not None:
            self.progress.update(
                self._task_id,
                iteration=self.current_iteration,
                max_iter=self.max_iterations,
                provider=self.provider_name or "unknown",
                tokens=self._get_token_display(),
            )
        
        # Refresh live display with updated criteria
        if self._live:
            try:
                self._live.update(self._build_display())
            except Exception as e:
                # If there's a MarkupError or any other error during rendering/measurement,
                # try building display without criteria table
                from rich.errors import MarkupError
                if isinstance(e, MarkupError):
                    # Build display without criteria to avoid the markup error
                    components = [self.progress]
                    try:
                        self._live.update(Group(*components))
                    except Exception:
                        # If even that fails, just skip the update
                        pass
                else:
                    # For other errors, re-raise
                    raise
            
    def __enter__(self) -> "RalphLiveDisplay":
        return self.start()

    def __exit__(self, *args) -> None:
        self.stop()


def get_criteria_list(task_file: Path) -> List[Tuple[str, bool]]:
    """Extract criteria from task file as list of (text, is_checked) tuples."""
    import re
    
    if not task_file.exists():
        return []
    
    content = task_file.read_text(encoding="utf-8")
    criteria = []
    
    # Match checkbox list items
    checkbox_pattern = r"^\s*([-*]|[0-9]+\.)\s+\[([ x])\]\s+(.+)$"
    
    for line in content.splitlines():
        match = re.match(checkbox_pattern, line)
        if match:
            is_checked = match.group(2) == "x"
            text = match.group(3).strip()
            criteria.append((text, is_checked))
    
    return criteria


def print_header(console: Console, title: str = "Ralph Wiggum") -> None:
    """Print a styled header."""
    from rich.rule import Rule
    console.print()
    console.print(Rule(f"[bold {THEME['primary']}]{title}[/]", style=THEME["primary"]))


def print_section_rule(console: Console, title: str = "") -> None:
    """Print a section separator rule."""
    from rich.rule import Rule
    if title:
        console.print(Rule(title, style=THEME["muted"]))
    else:
        console.print(Rule(style=THEME["muted"]))


def print_success(console: Console, message: str) -> None:
    """Print a success message."""
    console.print(f"[{THEME['success']}]✓[/] {message}")


def print_error(console: Console, message: str) -> None:
    """Print an error message."""
    console.print(f"[{THEME['error']}]✗[/] {message}")


def print_warning(console: Console, message: str) -> None:
    """Print a warning message."""
    console.print(f"[{THEME['warning']}]⚠[/] {message}")


def print_info(console: Console, message: str) -> None:
    """Print an info message."""
    console.print(f"[{THEME['info']}]ℹ[/] {message}")


def display_question_panel(console: Console, question_text: str) -> None:
    """Display an agent question in a styled Rich panel.
    
    Args:
        console: Rich console instance
        question_text: The question text to display (can be markdown)
    """
    from rich.markdown import Markdown
    
    console.print()
    console.print(Panel(
        Markdown(question_text),
        title="[bold cyan]? Agent Question[/]",
        border_style=THEME["warning"],
        padding=(1, 2),
    ))
