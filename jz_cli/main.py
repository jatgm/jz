"""
Main CLI entry point for jz CLI using Typer.
Routes commands, handles CLI flags, and launches interactive Textual TUI.
"""

from __future__ import annotations

import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from jz_cli import __app_name__, __version__
from jz_cli.config import AppConfig, get_base_dir, get_tokens_path, load_config, save_config
from jz_cli.services.calendar_service import CalendarService
from jz_cli.services.canvas_service import CanvasService
from jz_cli.ui.app import JZApp

console = Console()
cli = typer.Typer(
    name="jz",
    help="⚡ jz - Sleek developer-centric terminal productivity CLI for Google Calendar & Canvas LMS",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)


def run_tui(demo_mode: bool = False) -> None:
    """Launch the interactive Textual Terminal UI."""
    config = load_config()
    if demo_mode:
        config.demo_mode = True
    app = JZApp(config=config)
    app.run()


@cli.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(None, "--version", "-v", help="Display jz version and exit"),
    demo: bool = typer.Option(False, "--demo", help="Launch in demo mode with sample data"),
) -> None:
    """
    jz: The sleek cross-platform terminal productivity companion.
    Run 'jz' without arguments to launch the full interactive TUI.
    """
    if version:
        console.print(f"[bold #00ff88]{__app_name__} CLI[/] [cyan]v{__version__}[/]")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        run_tui(demo_mode=demo)


@cli.command("ui")
def cmd_ui(
    demo: bool = typer.Option(False, "--demo", help="Force demo mode with mock data"),
) -> None:
    """Launch the full interactive TUI (default when running 'jz')."""
    run_tui(demo_mode=demo)


@cli.command("today")
def cmd_today() -> None:
    """Quick terminal summary of today's calendar events and Canvas deadlines."""
    config = load_config()
    cal = CalendarService(demo_mode=config.demo_mode)
    canvas = CanvasService(config)

    now = datetime.datetime.now().astimezone()
    today_events = cal.get_today_events()
    deadlines = canvas.get_today_deadlines()

    # Agenda Table
    agenda_table = Table(title="📅 Today's Agenda", title_style="bold #00f0ff", box=None)
    agenda_table.add_column("Time", style="dim white", width=22)
    agenda_table.add_column("Badge", width=14)
    agenda_table.add_column("Event Title", style="bold bright_white")
    agenda_table.add_column("Location", style="dim #8be9fd")

    for ev in today_events:
        badge_text, badge_style = ev.get_status_badge(now)
        time_str = "All Day" if ev.is_all_day else f"{ev.start_time.strftime('%I:%M %p')} - {ev.end_time.strftime('%I:%M %p')}"
        agenda_table.add_row(
            time_str,
            Text(badge_text, style=badge_style),
            ev.title,
            ev.location or ev.meet_url or "—",
        )

    # Deadlines Table
    due_table = Table(title="⏰ Canvas Deadlines Due Today", title_style="bold #ff79c6", box=None)
    due_table.add_column("Course", style="bold #bd93f9", width=12)
    due_table.add_column("Assignment", style="bold bright_white")
    due_table.add_column("Countdown", width=24)
    due_table.add_column("Points", justify="right", style="#ffb86c", width=10)

    if not deadlines:
        due_table.add_row("—", "No assignments due today. All caught up! 🎉", "Clear", "—")
    else:
        for d in deadlines:
            cd_text, cd_style = d.get_due_countdown(now)
            due_table.add_row(
                f"[{d.course_code}]",
                d.name,
                Text(cd_text, style=cd_style),
                f"{d.points_possible:.0f} pts",
            )

    console.print(Panel(agenda_table, border_style="#00f0ff"))
    console.print(Panel(due_table, border_style="#ff79c6"))


@cli.command("canvas")
def cmd_canvas() -> None:
    """Print all upcoming Canvas LMS assignments grouped by urgency."""
    config = load_config()
    canvas = CanvasService(config)
    assignments = canvas.get_upcoming_assignments()
    now = datetime.datetime.now().astimezone()

    table = Table(
        title="📚 Canvas LMS — Upcoming Assignments",
        title_style="bold #ff79c6",
        header_style="bold #8be9fd",
    )
    table.add_column("Course", style="bold #bd93f9", width=14)
    table.add_column("Assignment Name", ratio=2)
    table.add_column("Due Date & Countdown", ratio=1)
    table.add_column("Points", justify="right", width=10, style="#ffb86c")

    for a in assignments:
        cd_text, cd_style = a.get_due_countdown(now)
        due_str = a.due_at.strftime("%b %d at %I:%M %p") if a.due_at else "No Due Date"
        table.add_row(
            f"[{a.course_code}]",
            a.name,
            Text(f"{due_str} ({cd_text})", style=cd_style),
            f"{a.points_possible:.0f} pts",
        )

    console.print(table)


@cli.command("cal")
def cmd_cal(days: int = typer.Option(7, "--days", "-d", help="Days to fetch")) -> None:
    """Display upcoming schedule from Google Calendar."""
    config = load_config()
    cal = CalendarService(demo_mode=config.demo_mode)
    events = cal.get_upcoming_events(days=days)

    table = Table(
        title=f"📅 Google Calendar — Next {days} Days",
        title_style="bold #00f0ff",
        header_style="bold #50fa7b",
    )
    table.add_column("Date", style="bold #00f0ff", width=16)
    table.add_column("Time Range", width=22)
    table.add_column("Event", style="bold bright_white")
    table.add_column("Location / Link", style="dim #8be9fd")

    for ev in events:
        table.add_row(
            ev.start_time.strftime("%a, %b %d"),
            "All Day" if ev.is_all_day else f"{ev.start_time.strftime('%I:%M %p')} - {ev.end_time.strftime('%I:%M %p')}",
            ev.title,
            ev.location or ev.meet_url or "—",
        )

    console.print(table)


@cli.command("sync")
def cmd_sync() -> None:
    """Test sync connections to Google Calendar and Canvas LMS."""
    config = load_config()
    console.print("[bold cyan]Testing integrations...[/]")

    # Canvas check
    canvas = CanvasService(config)
    if config.is_canvas_configured:
        ok, msg, _ = canvas.test_connection()
        col = "green" if ok else "red"
        console.print(f"[{col}]Canvas LMS:[/] {msg}")
    else:
        console.print("[yellow]Canvas LMS:[/] Not configured. (Using realistic demo data)")

    # GCal check
    cal = CalendarService(demo_mode=config.demo_mode)
    tokens_file = get_tokens_path()
    if cal.is_connected:
        console.print("[green]Google Calendar:[/] Connected and valid.")
    elif tokens_file.exists():
        console.print("[yellow]Google Calendar:[/] Token found but requires refresh or re-auth.")
    else:
        console.print(f"[yellow]Google Calendar:[/] Not configured. Tokens expected at: {tokens_file}")


@cli.command("config")
def cmd_config(
    canvas_url: Optional[str] = typer.Option(None, "--canvas-url", help="Canvas base URL (e.g. canvas.instructure.com)"),
    canvas_token: Optional[str] = typer.Option(None, "--canvas-token", help="Canvas personal access token"),
    email: Optional[str] = typer.Option(None, "--email", help="Student user email"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Active profile name"),
) -> None:
    """View or configure Canvas LMS and Google Calendar credentials."""
    config = load_config()

    if not any([canvas_url, canvas_token, email, profile]):
        # Display current config info
        console.print(Panel(
            f"[bold #00ff88]jz Configuration[/]\n\n"
            f"Config Directory:  [dim]{get_base_dir()}[/]\n"
            f"Canvas URL:        [cyan]{config.canvas_url or '(not configured)'}[/]\n"
            f"Canvas Token:      [dim]{'***' + config.canvas_token[-4:] if config.canvas_token else '(not set)'}[/]\n"
            f"Student Email:     [bright_white]{config.user_email}[/]\n"
            f"Active Profile:    [yellow]{config.active_profile}[/]\n"
            f"Tokens File:       [dim]{get_tokens_path()}[/]\n"
            f"Demo Mode:         [magenta]{config.demo_mode}[/]\n\n"
            f"[italic dim]Use --canvas-url, --canvas-token, or --email to update, or run 'jz' and type /config.[/]",
            border_style="#00ff88",
        ))
        return

    if canvas_url:
        config.canvas_url = canvas_url
    if canvas_token:
        config.canvas_token = canvas_token
    if email:
        config.user_email = email
    if profile:
        config.active_profile = profile

    config.demo_mode = False
    save_config(config)
    console.print("[bold green]✓ Configuration updated successfully![/]")


def run() -> None:
    """Console script entry point for 'jz' command."""
    cli()


if __name__ == "__main__":
    run()
