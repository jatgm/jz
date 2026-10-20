"""
Main CLI entry point for jz CLI using Typer.
Routes commands, handles CLI flags, path tracking, and launches interactive Textual TUI.
"""

from __future__ import annotations

import datetime
import sys
from typing import Optional

# Ensure UTF-8 output across Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from jz_cli import __app_name__, __version__
from jz_cli.config import (
    AppConfig,
    get_base_dir,
    get_tokens_path,
    load_config,
    save_config,
)
from jz_cli.services.calendar_service import CalendarService
from jz_cli.services.canvas_service import CanvasService
from jz_cli.tracker import get_tracked_items, uninstall_application
from jz_cli.ui.app import JZApp

console = Console(highlight=False)
cli = typer.Typer(
    name="jz",
    help="jz - Terminal productivity CLI connecting Google Calendar & Canvas LMS",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)


def run_tui(demo_mode: bool = False) -> None:
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
    jz: Cross-platform terminal productivity application.
    Run 'jz' without arguments to launch the full interactive TUI.
    """
    if version:
        console.print(f"[bold #00ff88]{__app_name__} CLI[/] [cyan]v{__version__}[/]")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        run_tui(demo_mode=demo)


@cli.command("ui")
def cmd_ui(
    demo: bool = typer.Option(False, "--demo", help="Force demo mode with sample data"),
) -> None:
    """Launch the full interactive TUI (default when running 'jz')."""
    run_tui(demo_mode=demo)


@cli.command("today")
def cmd_today(
    demo: bool = typer.Option(False, "--demo", help="Show demo data"),
) -> None:
    """Terminal summary of today's calendar events and Canvas deadlines."""
    config = load_config()
    if demo:
        config.demo_mode = True
    cal = CalendarService(demo_mode=config.demo_mode, gcal_ical_url=config.gcal_ical_url)
    canvas = CanvasService(config)

    now = datetime.datetime.now().astimezone()
    today_events = cal.get_today_events()
    deadlines = canvas.get_today_deadlines()

    # Agenda Table
    agenda_table = Table(title="Today's Agenda", title_style="bold #00f0ff", box=None)
    agenda_table.add_column("Time", style="dim white", width=14)
    agenda_table.add_column("Event Title", style="bold bright_white")
    agenda_table.add_column("Status", width=14, justify="right")

    if not cal.is_connected and not config.demo_mode:
        agenda_table.add_row("—", "Google Calendar: Disconnected. Run 'jz connect gcal <url>' to link.", "")
    elif not today_events:
        agenda_table.add_row("—", "No events scheduled for today. Free day!", "")
    else:
        for ev in today_events:
            badge_text, badge_style = ev.get_status_badge(now)
            time_str = "All Day" if ev.is_all_day else ev.start_time.strftime("%I:%M %p")
            agenda_table.add_row(time_str, ev.title, Text(badge_text, style=badge_style))

    # Deadlines Table
    due_table = Table(title="Canvas Deadlines Due Today", title_style="bold #ff79c6", box=None)
    due_table.add_column("Course", style="bold #bd93f9", width=12)
    due_table.add_column("Assignment", style="bold bright_white")
    due_table.add_column("Points", justify="right", style="#ffb86c", width=10)
    due_table.add_column("Countdown", width=22, justify="right")

    if not canvas.is_configured and not config.demo_mode:
        due_table.add_row("—", "Canvas LMS: Disconnected. Run 'jz connect canvas' to link.", "—", "")
    elif not deadlines:
        due_table.add_row("—", "No assignments due today. All caught up!", "—", "")
    else:
        for d in deadlines:
            cd_text, cd_style = d.get_due_countdown(now)
            due_table.add_row(
                f"[{d.course_code}]",
                d.name,
                f"{d.points_possible:.0f} pts" if d.points_possible else "—",
                Text(cd_text, style=cd_style),
            )

    console.print(Panel(agenda_table, border_style="#00f0ff"))
    console.print(Panel(due_table, border_style="#ff79c6"))


@cli.command("canvas")
def cmd_canvas(
    demo: bool = typer.Option(False, "--demo", help="Show demo data"),
) -> None:
    """Print upcoming Canvas LMS assignments."""
    config = load_config()
    if demo:
        config.demo_mode = True
    canvas = CanvasService(config)
    assignments = canvas.get_upcoming_assignments()
    now = datetime.datetime.now().astimezone()

    table = Table(
        title="Canvas LMS — Upcoming Assignments",
        title_style="bold #ff79c6",
        header_style="bold #8be9fd",
    )
    table.add_column("Course", style="bold #bd93f9", width=14)
    table.add_column("Assignment Name", ratio=2)
    table.add_column("Due Date & Countdown", ratio=1)
    table.add_column("Points", justify="right", width=10, style="#ffb86c")

    if not canvas.is_configured and not config.demo_mode:
        table.add_row("—", "Canvas LMS is not connected. Run 'jz connect canvas' to link.", "", "")
    elif not assignments:
        table.add_row("—", "No upcoming assignments found.", "", "")
    else:
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
def cmd_cal(
    days: int = typer.Option(7, "--days", "-d", help="Days to fetch"),
    demo: bool = typer.Option(False, "--demo", help="Show demo data"),
) -> None:
    """Display upcoming schedule from Google Calendar."""
    config = load_config()
    if demo:
        config.demo_mode = True
    cal = CalendarService(demo_mode=config.demo_mode, gcal_ical_url=config.gcal_ical_url)
    events = cal.get_upcoming_events(days=days)

    table = Table(
        title=f"Google Calendar — Next {days} Days",
        title_style="bold #00f0ff",
        header_style="bold #50fa7b",
    )
    table.add_column("Date", style="bold #00f0ff", width=16)
    table.add_column("Time Range", width=22)
    table.add_column("Event", style="bold bright_white")
    table.add_column("Location / Link", style="dim #8be9fd")

    if not cal.is_connected and not config.demo_mode:
        table.add_row("—", "", "Google Calendar is not connected. Run 'jz connect gcal' to link.", "")
    elif not events:
        table.add_row("—", "", "No events scheduled.", "")
    else:
        for ev in events:
            table.add_row(
                ev.start_time.strftime("%a, %b %d"),
                "All Day" if ev.is_all_day else f"{ev.start_time.strftime('%I:%M %p')} - {ev.end_time.strftime('%I:%M %p')}",
                ev.title,
                ev.location or ev.meet_url or "—",
            )

    console.print(table)


@cli.command("paths")
def cmd_paths() -> None:
    """List every file and directory tracked and managed by jz."""
    items = get_tracked_items()
    table = Table(
        title="jz — Managed Files & Storage Inventory",
        title_style="bold #00ff88",
        header_style="bold cyan",
    )
    table.add_column("Item Name", width=24, style="bold bright_white")
    table.add_column("Status", width=12)
    table.add_column("Size", width=12, justify="right", style="yellow")
    table.add_column("Path", ratio=1, style="dim white")

    for item in items:
        status = Text("Exists", style="green") if item.exists else Text("Not created", style="dim")
        size_str = f"{item.size_bytes} B" if item.exists else "—"
        table.add_row(item.name, status, size_str, str(item.path))

    console.print(table)


@cli.command("uninstall")
def cmd_uninstall(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    purge_pkg: bool = typer.Option(True, "--purge-package/--keep-package", help="Also pip uninstall jz-cli"),
) -> None:
    """
    Completely remove all configuration, cache, and token files without leaving a trace.
    """
    items = get_tracked_items()
    console.print("[bold yellow]This will remove all jz data, configuration, and tokens from your system:[/]")
    for item in items:
        if item.exists:
            console.print(f"  • [red]{item.path}[/] ({item.size_bytes} bytes)")

    if not yes:
        confirm = typer.confirm("\nAre you sure you want to proceed with full uninstallation?")
        if not confirm:
            console.print("[dim]Uninstallation canceled.[/]")
            raise typer.Exit()

    ok, deleted = uninstall_application(remove_package=purge_pkg)
    for msg in deleted:
        console.print(f"[green]✓[/] {msg}")

    console.print("\n[bold green]✓ Uninstallation complete! Zero trace remaining on system.[/]")


@cli.command("connect")
def cmd_connect(
    service: Optional[str] = typer.Argument(None, help="Service to connect: 'canvas' or 'gcal'"),
    url: Optional[str] = typer.Option(None, "--url", help="URL, domain, or iCal feed URL"),
    token: Optional[str] = typer.Option(None, "--token", help="Canvas personal access token"),
) -> None:
    """Link Google Calendar or Canvas LMS accounts."""
    config = load_config()

    if not service:
        console.print(
            "[bold cyan]jz Connect Wizard[/]\n"
            "Connect Canvas:\n"
            "  jz connect canvas --url gatech.instructure.com --token <TOKEN>\n"
            "  jz connect canvas --url <CANVAS_ICAL_FEED_URL>\n\n"
            "Connect Google Calendar:\n"
            "  jz connect gcal --url <PRIVATE_ICAL_URL>\n"
        )
        return

    svc = service.lower()
    if svc == "canvas":
        if not url:
            url = typer.prompt("Canvas domain or iCal feed URL (e.g. gatech.instructure.com or .ics URL)")

        if ".ics" in url or "feeds/calendars" in url:
            config.canvas_ical_url = url.strip()
            config.demo_mode = False
            save_config(config)
            console.print("[bold green]✓ Canvas iCal feed connected successfully![/]")
        else:
            if not token:
                token = typer.prompt("Canvas Personal Access Token (from Account -> Settings)", hide_input=True)
            config.canvas_url = url.strip()
            config.canvas_token = token.strip()
            config.demo_mode = False
            save_config(config)

            # Test connection
            canvas = CanvasService(config)
            ok, msg, profile = canvas.test_connection()
            if ok:
                if profile.get("primary_email"):
                    config.user_email = profile["primary_email"]
                if profile.get("name"):
                    config.user_name = profile["name"]
                save_config(config)
                console.print(f"[bold green]✓ {msg}[/]")
            else:
                console.print(f"[bold yellow]Warning: {msg}[/]")

    elif svc in ("gcal", "calendar"):
        if not url:
            url = typer.prompt("Google Calendar secret iCal URL (from GCal Settings -> Integrate Calendar)")
        config.gcal_ical_url = url.strip()
        config.demo_mode = False
        save_config(config)
        console.print("[bold green]✓ Google Calendar linked successfully![/]")


@cli.command("sync")
def cmd_sync() -> None:
    """Test sync connections to Google Calendar and Canvas LMS."""
    config = load_config()
    console.print("[bold cyan]Testing integrations...[/]")

    canvas = CanvasService(config)
    if canvas.is_configured:
        ok, msg, _ = canvas.test_connection()
        col = "green" if ok else "red"
        console.print(f"[{col}]Canvas LMS:[/] {msg}")
    else:
        console.print("[dim]Canvas LMS: Not configured. (Run 'jz connect canvas' to link)[/]")

    cal = CalendarService(demo_mode=config.demo_mode, gcal_ical_url=config.gcal_ical_url)
    if cal.is_connected:
        console.print("[green]Google Calendar:[/] Connected and valid.")
    else:
        console.print("[dim]Google Calendar: Not configured. (Run 'jz connect gcal' to link)[/]")


@cli.command("config")
def cmd_config(
    canvas_url: Optional[str] = typer.Option(None, "--canvas-url", help="Canvas base URL"),
    canvas_token: Optional[str] = typer.Option(None, "--canvas-token", help="Canvas access token"),
    email: Optional[str] = typer.Option(None, "--email", help="Student email"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Active profile"),
) -> None:
    """View or update configuration."""
    config = load_config()

    if not any([canvas_url, canvas_token, email, profile]):
        console.print(Panel(
            f"[bold #00ff88]jz Configuration[/]\n\n"
            f"Config Directory:  [dim]{get_base_dir()}[/]\n"
            f"Canvas URL:        [cyan]{config.canvas_url or '(not configured)'}[/]\n"
            f"Canvas iCal Feed:  [cyan]{config.canvas_ical_url or '(not configured)'}[/]\n"
            f"Google iCal Feed:  [cyan]{config.gcal_ical_url or '(not configured)'}[/]\n"
            f"Student Email:     [bright_white]{config.user_email or '(not set)'}[/]\n"
            f"Active Profile:    [yellow]{config.active_profile}[/]\n"
            f"Demo Mode:         [magenta]{config.demo_mode}[/]",
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

    save_config(config)
    console.print("[bold green]✓ Configuration updated successfully![/]")


def run() -> None:
    cli()


if __name__ == "__main__":
    run()
