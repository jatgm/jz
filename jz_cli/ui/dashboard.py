"""
Clean, minimal dashboard widgets for jz CLI:
- Split Today's Agenda & Canvas Due Dates with uncluttered layouts
- Connection wizard (/connect)
- Expanded Canvas view (/canvas)
- 7-Day Calendar schedule view (/cal)
- Smart Study Planner view (/plan)
- Help and command cheat sheet (/help)
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget

from jz_cli.config import AppConfig, get_tokens_path
from jz_cli.services.calendar_service import CalendarEvent
from jz_cli.services.canvas_service import CanvasAssignment, CanvasCourse


class TodayAgendaWidget(Widget):
    """Left column widget: Sleek, uncluttered schedule view."""

    DEFAULT_CSS = """
    TodayAgendaWidget {
        width: 1fr;
        height: 100%;
        background: transparent;
        border: solid #21262d;
        border-top: solid #00f0ff;
        padding: 0 1;
    }
    """

    events: reactive[List[CalendarEvent]] = reactive([], layout=True)
    is_connected: reactive[bool] = reactive(False)
    is_demo: reactive[bool] = reactive(False)

    def render(self) -> RenderableType:
        if not self.is_connected and not self.is_demo:
            empty_table = Table.grid(padding=1)
            empty_table.add_row(Text("○ Google Calendar: Disconnected", style="bold yellow"))
            empty_table.add_row(
                Text(
                    "Connect your calendar to view today's schedule.\n\n"
                    "  • Type /connect gcal <ical_url_or_oauth>\n"
                    "  • Type /demo to preview sample schedule",
                    style="dim white",
                )
            )
            return Panel(
                empty_table,
                title=Text("📅 Today's Agenda", style="bold #00f0ff"),
                title_align="left",
                border_style="#30363d",
            )

        table = Table(
            show_header=True,
            header_style="bold #00f0ff",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        table.add_column("Time", width=12, style="dim white")
        table.add_column("Event Title", ratio=1)
        table.add_column("Status", width=14, justify="right")

        now = datetime.datetime.now().astimezone()

        if not self.events:
            table.add_row("—", Text("No events scheduled for today. Free day!", style="dim green"), "")
        else:
            for ev in self.events:
                badge_text, badge_style = ev.get_status_badge(now)
                time_str = "All Day" if ev.is_all_day else ev.start_time.strftime("%I:%M %p")
                title_style = "bold bright_white" if "Ongoing" in badge_text else "white"

                table.add_row(
                    time_str,
                    Text(ev.title, style=title_style),
                    Text(badge_text, style=badge_style),
                )

        header_title = Text.assemble(
            ("📅 Today's Agenda ", "bold #00f0ff"),
            (f"({len(self.events)} events)" if self.events else "", "dim white"),
        )
        return Panel(
            table,
            title=header_title,
            title_align="left",
            border_style="#30363d",
            padding=(0, 1),
        )


class CanvasDueDatesWidget(Widget):
    """Right column widget: Sleek, uncluttered assignments view."""

    DEFAULT_CSS = """
    CanvasDueDatesWidget {
        width: 1fr;
        height: 100%;
        background: transparent;
        border: solid #21262d;
        border-top: solid #ff79c6;
        padding: 0 1;
    }
    """

    assignments: reactive[List[CanvasAssignment]] = reactive([], layout=True)
    is_connected: reactive[bool] = reactive(False)
    is_demo: reactive[bool] = reactive(False)

    def render(self) -> RenderableType:
        if not self.is_connected and not self.is_demo:
            empty_table = Table.grid(padding=1)
            empty_table.add_row(Text("○ Canvas LMS: Disconnected", style="bold yellow"))
            empty_table.add_row(
                Text(
                    "Connect Canvas to sync assignments & deadlines.\n\n"
                    "  • Type /connect canvas <domain> <token>\n"
                    "  • Type /connect canvas <ical_feed_url>\n"
                    "  • Type /demo to preview sample deadlines",
                    style="dim white",
                )
            )
            return Panel(
                empty_table,
                title=Text("📚 Canvas Due Dates", style="bold #ff79c6"),
                title_align="left",
                border_style="#30363d",
            )

        table = Table(
            show_header=True,
            header_style="bold #ff79c6",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        table.add_column("Course", width=12, style="bold #bd93f9")
        table.add_column("Assignment", ratio=1)
        table.add_column("Points", width=8, justify="right", style="dim #ffb86c")
        table.add_column("Due", width=18, justify="right")

        now = datetime.datetime.now().astimezone()

        if not self.assignments:
            table.add_row("—", Text("All clear! Zero pending deadlines.", style="dim green"), "", "")
        else:
            for item in self.assignments:
                countdown_text, countdown_style = item.get_due_countdown(now)
                table.add_row(
                    f"[{item.course_code}]",
                    Text(item.name, style="bright_white"),
                    f"{item.points_possible:.0f} pts" if item.points_possible else "—",
                    Text(countdown_text, style=countdown_style),
                )

        header_title = Text.assemble(
            ("📚 Canvas Due Dates ", "bold #ff79c6"),
            (f"({len(self.assignments)} upcoming)" if self.assignments else "", "dim white"),
        )
        return Panel(
            table,
            title=header_title,
            title_align="left",
            border_style="#30363d",
            padding=(0, 1),
        )


class SplitDashboardWidget(Widget):
    """Standard two-column main dashboard view."""

    DEFAULT_CSS = """
    SplitDashboardWidget {
        height: 100%;
        width: 100%;
    }

    #columns-container {
        height: 100%;
        width: 100%;
    }
    """

    def __init__(
        self,
        events: List[CalendarEvent],
        assignments: List[CanvasAssignment],
        is_gcal_connected: bool = False,
        is_canvas_connected: bool = False,
        is_demo: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.agenda_widget = TodayAgendaWidget()
        self.agenda_widget.events = events
        self.agenda_widget.is_connected = is_gcal_connected
        self.agenda_widget.is_demo = is_demo

        self.canvas_widget = CanvasDueDatesWidget()
        self.canvas_widget.assignments = assignments
        self.canvas_widget.is_connected = is_canvas_connected
        self.canvas_widget.is_demo = is_demo

    def update_data(
        self,
        events: List[CalendarEvent],
        assignments: List[CanvasAssignment],
        is_gcal_connected: bool,
        is_canvas_connected: bool,
        is_demo: bool,
    ) -> None:
        self.agenda_widget.events = events
        self.agenda_widget.is_connected = is_gcal_connected
        self.agenda_widget.is_demo = is_demo

        self.canvas_widget.assignments = assignments
        self.canvas_widget.is_connected = is_canvas_connected
        self.canvas_widget.is_demo = is_demo

    def compose(self) -> ComposeResult:
        with Horizontal(id="columns-container"):
            yield self.agenda_widget
            yield self.canvas_widget


class ExpandedCanvasWidget(Widget):
    """Full-screen view of Canvas courses and assignments (/canvas)."""

    DEFAULT_CSS = """
    ExpandedCanvasWidget {
        height: 100%;
        width: 100%;
        padding: 0 1;
    }
    """

    courses: reactive[List[CanvasCourse]] = reactive([])
    assignments: reactive[List[CanvasAssignment]] = reactive([])

    def render(self) -> RenderableType:
        table = Table(
            title="📚 Canvas LMS — All Upcoming Deadlines",
            title_style="bold #ff79c6",
            header_style="bold #8be9fd",
            expand=True,
            box=None,
        )
        table.add_column("Course", width=14, style="bold #bd93f9")
        table.add_column("Assignment Name", ratio=2)
        table.add_column("Due Date & Countdown", ratio=1)
        table.add_column("Points", width=10, justify="right", style="#ffb86c")

        now = datetime.datetime.now().astimezone()

        if not self.assignments:
            table.add_row("None", "No upcoming assignments found.", "", "—")
        else:
            for item in self.assignments:
                countdown_text, countdown_style = item.get_due_countdown(now)
                due_str = item.due_at.strftime("%b %d at %I:%M %p") if item.due_at else "No Due Date"
                due_col = Text.assemble(
                    (f"{due_str}  ", "bright_white"),
                    (f"({countdown_text})", countdown_style),
                )
                table.add_row(
                    f"[{item.course_code}]",
                    item.name,
                    due_col,
                    f"{item.points_possible:.0f} pts",
                )

        return Panel(table, border_style="#ff79c6", padding=(1, 2))


class WeekCalendarWidget(Widget):
    """7-day schedule view (/cal)."""

    DEFAULT_CSS = """
    WeekCalendarWidget {
        height: 100%;
        width: 100%;
        padding: 0 1;
    }
    """

    events: reactive[List[CalendarEvent]] = reactive([])

    def render(self) -> RenderableType:
        table = Table(
            title="📅 Google Calendar — 7-Day Schedule Overview",
            title_style="bold #00f0ff",
            header_style="bold #50fa7b",
            expand=True,
            box=None,
        )
        table.add_column("Day / Date", width=16, style="bold #00f0ff")
        table.add_column("Time Range", width=22)
        table.add_column("Event Title", ratio=2)
        table.add_column("Location / Link", ratio=1)

        if not self.events:
            table.add_row("No Events", "", "No upcoming events scheduled.", "")
        else:
            curr_date = None
            for ev in self.events:
                ev_date = ev.start_time.strftime("%a, %b %d")
                date_label = ev_date if ev_date != curr_date else ""
                curr_date = ev_date

                time_str = "All Day" if ev.is_all_day else f"{ev.start_time.strftime('%I:%M %p')} - {ev.end_time.strftime('%I:%M %p')}"
                loc_str = ev.location or ev.meet_url or "—"

                table.add_row(
                    date_label,
                    time_str,
                    Text(ev.title, style="bold bright_white"),
                    Text(loc_str, style="dim #8be9fd"),
                )

        return Panel(table, border_style="#00f0ff", padding=(1, 2))


class StudyPlannerWidget(Widget):
    """Smart study planner matching free calendar slots with pending Canvas deadlines (/plan)."""

    DEFAULT_CSS = """
    StudyPlannerWidget {
        height: 100%;
        width: 100%;
        padding: 0 1;
    }
    """

    free_slots: reactive[list] = reactive([])
    assignments: reactive[List[CanvasAssignment]] = reactive([])

    def render(self) -> RenderableType:
        table = Table(
            title="🎯 Smart Study Planner — Recommended Focus Blocks",
            title_style="bold #50fa7b",
            header_style="bold #f1fa8c",
            expand=True,
            box=None,
        )
        table.add_column("Window", width=24, style="bold #00f0ff")
        table.add_column("Target Assignment", ratio=2)
        table.add_column("Action", width=24, style="bold #50fa7b")

        now = datetime.datetime.now().astimezone()

        if not self.assignments:
            table.add_row("No Deadlines", "No pending assignments requiring study blocks.", "Enjoy free time ☕")
        else:
            pending = [a for a in self.assignments if not a.has_submitted]
            slots = self.free_slots if self.free_slots else [
                (now.replace(hour=14, minute=0), now.replace(hour=16, minute=0), 120),
                (now.replace(hour=19, minute=0), now.replace(hour=21, minute=0), 120),
            ]

            for i, assign in enumerate(pending[: len(slots)]):
                start, end, duration_mins = slots[i % len(slots)]
                window_str = f"{start.strftime('%a %I:%M %p')} - {end.strftime('%I:%M %p')}"
                hours = duration_mins // 60
                dur_flag = f"{hours}h" if hours > 0 else f"{duration_mins}m"
                quick_cmd = f"/block {dur_flag} {assign.course_code}"

                assign_text = Text.assemble(
                    (f"[{assign.course_code}] ", "bold #bd93f9"),
                    (f"{assign.name} ", "bold bright_white"),
                    (f"({assign.get_due_countdown(now)[0]})", "dim yellow"),
                )

                table.add_row(window_str, assign_text, Text(quick_cmd, style="bold green"))

        instructions = Text(
            "\n💡 Run /block <time> <title> to insert focus sessions into Google Calendar.",
            style="italic dim white",
        )

        return Panel(
            Group(table, instructions),
            title="🎯 Study & Deadline Block Engine",
            border_style="#50fa7b",
            padding=(1, 2),
        )


class ConnectWizardWidget(Widget):
    """Clean interactive setup guide (/connect)."""
    """Clean interactive setup guide (/connect)."""

    DEFAULT_CSS = """
    ConnectWizardWidget {
        height: 100%;
        width: 100%;
        padding: 0 1;
    }
    """

    config: reactive[Optional[AppConfig]] = reactive(None)
    gcal_connected: reactive[bool] = reactive(False)
    canvas_connected: reactive[bool] = reactive(False)

    def render(self) -> RenderableType:
        table = Table(
            title="⚡ Connect Live Accounts & Integrations",
            title_style="bold #00ff88",
            expand=True,
            box=None,
        )
        table.add_column("Integration", width=18, style="bold cyan")
        table.add_column("Status", width=16)
        table.add_column("Connection Instructions & Commands", ratio=2)

        gcal_status = Text("Connected ●", style="bold green") if self.gcal_connected else Text("Disconnected ○", style="dim white")
        table.add_row(
            "Google Calendar",
            gcal_status,
            Text(
                "• Private iCal Feed (Instant 0-setup): /connect gcal <url>\n"
                "  (Google Calendar -> Settings -> Integrate Calendar -> Secret address in iCal format)\n"
                "• Or OAuth credentials file: place credentials.json in config dir.",
                style="white",
            ),
        )
        table.add_section()

        canvas_status = Text("Connected ●", style="bold green") if self.canvas_connected else Text("Disconnected ○", style="dim white")
        table.add_row(
            "Canvas LMS",
            canvas_status,
            Text(
                "• API Token: /connect canvas <domain> <token>\n"
                "  e.g. /connect canvas gatech.instructure.com 2092~abcdef...\n"
                "• Or Calendar Feed URL: /connect canvas <feed_url>\n"
                "  (Canvas -> Calendar -> Calendar Feed -> copy URL)",
                style="white",
            ),
        )

        content = Group(
            table,
            Text(
                "\nCommands:\n"
                "  /today             Return to dashboard\n"
                "  /demo              Toggle preview demo mode\n"
                "  /sync              Refresh live connections",
                style="dim white",
            ),
        )

        return Panel(content, border_style="#00ff88", padding=(1, 2))


ConfigWizardWidget = ConnectWizardWidget


class HelpWidget(Widget):
    """Help and slash command reference cheat sheet (/help)."""

    DEFAULT_CSS = """
    HelpWidget {
        height: 100%;
        width: 100%;
        padding: 0 1;
    }
    """

    def render(self) -> RenderableType:
        table = Table(
            title="⚡ Slash Commands & Shortcuts Cheat Sheet",
            title_style="bold #00ff88",
            header_style="bold #8be9fd",
            expand=True,
            box=None,
        )
        table.add_column("Command / Key", width=24, style="bold #50fa7b")
        table.add_column("Description", ratio=2)

        commands = [
            ("/today", "Switch to today's split view (Agenda + Canvas deadlines)"),
            ("/connect", "Connect live Google Calendar and Canvas LMS accounts"),
            ("/sync", "Trigger background re-sync of Calendar and Canvas data"),
            ("/canvas", "Open expanded table of all upcoming assignments"),
            ("/cal", "7-day Google Calendar schedule overview"),
            ("/plan", "Scan free slots against pending deadlines and suggest focus blocks"),
            ("/block <time> <title>", "Quick time-blocking (e.g. /block 2h CS HW)"),
            ("/demo", "Toggle demo preview mode with sample academic data"),
            ("/paths", "List all directories and files managed by jz on your system"),
            ("/uninstall", "Instructions and prompt for clean zero-trace removal"),
            ("Shift+Tab / Tab", "Cycle prompt modes: ◉ Plan  ➔  ◉ Command  ➔  ◉ Ask"),
            ("Up / Down Arrows", "Browse command history in prompt"),
            ("Esc", "Return to default today view"),
            ("q / Ctrl+C", "Quit jz CLI"),
        ]

        for cmd, desc in commands:
            table.add_row(cmd, desc)

        return Panel(table, border_style="#00ff88", padding=(1, 2))
