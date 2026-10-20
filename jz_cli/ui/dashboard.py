"""
Dashboard widgets for jz CLI:
- Split Today's Agenda (Google Calendar) & Canvas Due Dates
- Expanded Canvas view (/canvas)
- 7-Day Calendar schedule view (/cal)
- Smart Study Planner view (/plan)
- Interactive Configuration wizard (/config)
- Help and command cheat sheet (/help)
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from rich.align import Align
from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget

from jz_cli.config import AppConfig, get_tokens_path, save_config
from jz_cli.services.calendar_service import CalendarEvent, CalendarService
from jz_cli.services.canvas_service import CanvasAssignment, CanvasCourse, CanvasService


class TodayAgendaWidget(Widget):
    """Left column widget: Today's schedule with relative status badges."""

    DEFAULT_CSS = """
    TodayAgendaWidget {
        width: 1fr;
        height: 100%;
        background: #0d1117;
        border: solid #21262d;
        border-top: solid #00f0ff;
        padding: 0 1;
    }
    """

    events: reactive[List[CalendarEvent]] = reactive([], layout=True)

    def render(self) -> RenderableType:
        table = Table(
            show_header=True,
            header_style="bold #00f0ff",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        table.add_column("Time / Badge", width=22, no_wrap=True)
        table.add_column("Event & Location", ratio=1)

        now = datetime.datetime.now().astimezone()

        if not self.events:
            table.add_row(
                Text("No Events", style="dim"),
                Text("No calendar events scheduled for today. Free day! ☕", style="dim green"),
            )
        else:
            for ev in self.events:
                badge_text, badge_style = ev.get_status_badge(now)
                time_range = (
                    "All Day"
                    if ev.is_all_day
                    else f"{ev.start_time.strftime('%I:%M %p')} - {ev.end_time.strftime('%I:%M %p')}"
                )

                time_badge = Text.assemble(
                    (f"{badge_text:<10} ", badge_style),
                    (f"\n{time_range}", "dim white"),
                )

                title_style = "bold bright_white" if "Ongoing" in badge_text else "bright_white"
                if "Done" in badge_text:
                    title_style = "dim strike"

                details = Text()
                details.append(ev.title, style=title_style)
                if ev.location:
                    details.append(f"\n📍 {ev.location}", style="dim #8be9fd")
                elif ev.meet_url:
                    details.append(f"\n🎥 {ev.meet_url}", style="dim #50fa7b")

                table.add_row(time_badge, details)
                table.add_section()

        header_title = Text.assemble(
            ("📅  Today's Agenda ", "bold #00f0ff"),
            (f"({len(self.events)} events)", "dim white"),
        )
        return Panel(
            table,
            title=header_title,
            title_align="left",
            border_style="#30363d",
            padding=(0, 1),
        )


class CanvasDueDatesWidget(Widget):
    """Right column widget: Canvas LMS assignments, course codes, points, countdowns."""

    DEFAULT_CSS = """
    CanvasDueDatesWidget {
        width: 1fr;
        height: 100%;
        background: #0d1117;
        border: solid #21262d;
        border-top: solid #ff79c6;
        padding: 0 1;
    }
    """

    assignments: reactive[List[CanvasAssignment]] = reactive([], layout=True)

    def render(self) -> RenderableType:
        table = Table(
            show_header=True,
            header_style="bold #ff79c6",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        table.add_column("Course / Status", width=22, no_wrap=True)
        table.add_column("Assignment & Points", ratio=1)

        now = datetime.datetime.now().astimezone()

        if not self.assignments:
            table.add_row(
                Text("All Clear", style="bold green"),
                Text("Zero pending assignments due. You are completely caught up! 🎉", style="dim green"),
            )
        else:
            for item in self.assignments:
                countdown_text, countdown_style = item.get_due_countdown(now)

                course_tag = Text.assemble(
                    (f"[{item.course_code}]", "bold #bd93f9"),
                    (f"\n{countdown_text}", countdown_style),
                )

                details = Text()
                details.append(item.name, style="bold bright_white")
                details.append(f"  ·  {item.points_possible:.0f} pts", style="dim #ffb86c")
                if item.has_submitted:
                    details.append("\n✓ Submitted", style="bold green")
                else:
                    details.append("\n⌛ Pending Submission", style="dim yellow")

                table.add_row(course_tag, details)
                table.add_section()

        header_title = Text.assemble(
            ("📚  Canvas Due Dates ", "bold #ff79c6"),
            (f"({len(self.assignments)} upcoming)", "dim white"),
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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.agenda_widget = TodayAgendaWidget()
        self.agenda_widget.events = events
        self.canvas_widget = CanvasDueDatesWidget()
        self.canvas_widget.assignments = assignments

    def update_data(self, events: List[CalendarEvent], assignments: List[CanvasAssignment]) -> None:
        self.agenda_widget.events = events
        self.canvas_widget.assignments = assignments

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
            title="📚 Canvas LMS — All Active Assignments & Deadlines",
            title_style="bold #ff79c6",
            header_style="bold #8be9fd",
            expand=True,
            box=None,
        )
        table.add_column("Course", width=14, style="bold #bd93f9")
        table.add_column("Assignment Name", ratio=2)
        table.add_column("Due Date & Countdown", ratio=1)
        table.add_column("Points", width=10, justify="right", style="#ffb86c")
        table.add_column("Status", width=14)

        now = datetime.datetime.now().astimezone()

        if not self.assignments:
            table.add_row("None", "No upcoming assignments found.", "", "-", "")
        else:
            for item in self.assignments:
                countdown_text, countdown_style = item.get_due_countdown(now)
                due_str = item.due_at.strftime("%b %d at %I:%M %p") if item.due_at else "No Due Date"

                status_text = Text("✓ Submitted", style="bold green") if item.has_submitted else Text("⌛ Pending", style="bold yellow")
                due_col = Text.assemble(
                    (f"{due_str}\n", "bright_white"),
                    (countdown_text, countdown_style),
                )

                table.add_row(
                    f"[{item.course_code}]",
                    item.name,
                    due_col,
                    f"{item.points_possible:.0f} pts",
                    status_text,
                )
                table.add_section()

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
        table.add_column("Day / Date", width=18, style="bold #00f0ff")
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
                if date_label and ev_date != "":
                    table.add_section()

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
        table.add_column("Suggested Window", width=26, style="bold #00f0ff")
        table.add_column("Target Assignment", ratio=2)
        table.add_column("Priority / Reason", ratio=1)
        table.add_column("Quick Action", width=24, style="bold #50fa7b")

        now = datetime.datetime.now().astimezone()

        if not self.assignments:
            table.add_row(
                "No Deadlines",
                "No upcoming assignments requiring focus blocks.",
                "All clear!",
                "Enjoy free time ☕",
            )
        else:
            # Pair free slots with assignments
            pending = [a for a in self.assignments if not a.has_submitted]
            slots = self.free_slots if self.free_slots else [
                (now.replace(hour=14, minute=0), now.replace(hour=16, minute=0), 120),
                (now.replace(hour=19, minute=0), now.replace(hour=21, minute=0), 120),
            ]

            for i, assign in enumerate(pending[: len(slots)]):
                start, end, duration_mins = slots[i % len(slots)]
                window_str = f"{start.strftime('%a %I:%M %p')} - {end.strftime('%I:%M %p')}\n({duration_mins}m free slot)"

                hours = duration_mins // 60
                dur_flag = f"{hours}h" if hours > 0 else f"{duration_mins}m"
                quick_cmd = f"/block {dur_flag} {assign.course_code}"

                priority = "🔥 Urgent (Due Today)" if assign.due_at and assign.due_at.date() == now.date() else "⚡ High Value"

                assign_text = Text.assemble(
                    (f"[{assign.course_code}] ", "bold #bd93f9"),
                    (f"{assign.name}\n", "bold bright_white"),
                    (f"Worth {assign.points_possible:.0f} pts · {assign.get_due_countdown(now)[0]}", "dim #ffb86c"),
                )

                table.add_row(
                    window_str,
                    assign_text,
                    Text(priority, style="bold yellow" if "Urgent" in priority else "cyan"),
                    Text(quick_cmd, style="bold green"),
                )
                table.add_section()

        instructions = Text(
            "\n💡 Press Shift+Tab to switch to Plan/Command mode, then run /block <time> <title> to insert blocks into Google Calendar.",
            style="italic dim white",
        )

        return Panel(
            RenderableType(table),
            title="🎯 Intelligent Study & Deadline Block Engine",
            border_style="#50fa7b",
            padding=(1, 2),
        )


class ConfigWizardWidget(Widget):
    """Interactive setup wizard for Canvas URL/token and Google OAuth (/config)."""

    DEFAULT_CSS = """
    ConfigWizardWidget {
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
            title="⚙️  jz CLI Configuration & Integration Wizard",
            title_style="bold #f1fa8c",
            expand=True,
            box=None,
        )
        table.add_column("Integration", width=20, style="bold cyan")
        table.add_column("Current Setting", ratio=2)
        table.add_column("Status", width=18)
        table.add_column("Action / Instructions", ratio=2)

        # Google Calendar Row
        gcal_status = Text("✓ Connected", style="bold green") if self.gcal_connected else Text("○ Not Connected", style="bold yellow")
        gcal_info = (
            "Google Calendar API OAuth2"
            if self.gcal_connected
            else f"Tokens file: {get_tokens_path()}"
        )
        table.add_row(
            "Google Calendar",
            gcal_info,
            gcal_status,
            "Place credentials.json in config dir or run local auth.",
        )
        table.add_section()

        # Canvas Row
        canvas_status = Text("✓ Connected", style="bold green") if self.canvas_connected else Text("○ Not Configured", style="bold yellow")
        url_display = self.config.canvas_url if self.config and self.config.canvas_url else "Not configured"
        table.add_row(
            "Canvas LMS URL",
            url_display,
            canvas_status,
            "e.g. https://gatech.instructure.com or canvas.instructure.com",
        )
        table.add_section()

        # User profile
        user_name = self.config.user_name if self.config else "Student"
        user_email = self.config.user_email if self.config else "student@university.edu"
        table.add_row(
            "User Profile",
            f"{user_name} <{user_email}>",
            Text("Active", style="bold green"),
            "Auto-populated from Canvas profile or config.json.",
        )

        content = Table.grid(padding=1)
        content.add_row(table)
        content.add_row(
            Text(
                "\nQuick Setup Commands:\n"
                "  • Set Canvas: Type `/set-canvas <canvas_url> <token>`\n"
                "  • Set Email:  Type `/set-email <your_email@university.edu>`\n"
                "  • Test Sync:   Type `/sync` to verify API calls\n"
                "  • Exit Setup:  Type `/today` to return to dashboard",
                style="bright_white",
            )
        )

        return Panel(content, border_style="#f1fa8c", padding=(1, 2))


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
            title="⚡ jz CLI — Slash Commands & Shortcuts Cheat Sheet",
            title_style="bold #00ff88",
            header_style="bold #8be9fd",
            expand=True,
            box=None,
        )
        table.add_column("Command / Key", width=22, style="bold #50fa7b")
        table.add_column("Mode / Context", width=18, style="cyan")
        table.add_column("Description", ratio=2)

        commands = [
            ("/today", "Any", "Switch to today's split view (Agenda + Canvas deadlines)"),
            ("/sync", "Any", "Trigger a fresh background sync of Google Calendar & Canvas data"),
            ("/canvas", "Any", "Open expanded table of all upcoming assignments & course points"),
            ("/cal", "Any", "7-day Google Calendar schedule overview"),
            ("/plan", "Plan", "Scan free slots against pending deadlines and suggest focus blocks"),
            ("/block <time> <title>", "Command", "Quick time-blocking in Google Calendar (e.g. /block 2h CS HW)"),
            ("/config", "Any", "Open configuration wizard for Canvas and Google credentials"),
            ("/help, ?", "Any", "Open this command reference screen"),
            ("/clear", "Any", "Clear log messages and return to clean dashboard"),
            ("Shift+Tab / Tab", "Global", "Cycle prompt modes: ◉ Plan  ➔  ◉ Command  ➔  ◉ Ask / Chat"),
            ("Up / Down Arrows", "Prompt", "Browse command history"),
            ("Esc", "Global", "Dismiss tips banner or return to default dashboard"),
            ("Ctrl+R / F5", "Global", "Quick refresh data"),
            ("q / Ctrl+C", "Global", "Quit jz CLI"),
        ]

        for cmd, mode, desc in commands:
            table.add_row(cmd, mode, desc)
            table.add_section()

        return Panel(table, border_style="#00ff88", padding=(1, 2))
