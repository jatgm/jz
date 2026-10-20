"""
Main Textual Application root for jz CLI:
Coordinates Header, Dynamic View swapping, Interactive Prompt Box,
and Footer Status Bar with reactive slash command handling.
"""

from __future__ import annotations

import asyncio
import datetime
import re
from typing import List, Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive

from jz_cli import __version__
from jz_cli.config import AppConfig, load_config, save_config
from jz_cli.services.calendar_service import CalendarEvent, CalendarService
from jz_cli.services.canvas_service import CanvasAssignment, CanvasCourse, CanvasService
from jz_cli.tracker import get_tracked_items
from jz_cli.ui.dashboard import (
    ConnectWizardWidget,
    ExpandedCanvasWidget,
    HelpWidget,
    SplitDashboardWidget,
    StudyPlannerWidget,
    WeekCalendarWidget,
)
from jz_cli.ui.header import HeaderView
from jz_cli.ui.prompt_input import FooterStatusBar, PromptBox


class JZApp(App):
    """Clean developer-centric productivity terminal UI."""

    CSS = """
    Screen {
        background: #0d1117;
        color: #c9d1d9;
    }

    #main-content {
        height: 1fr;
        width: 100%;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit_app", "Quit", show=False),
        Binding("ctrl+c", "quit_app", "Quit", show=False),
        Binding("escape", "handle_escape", "Back", show=False),
        Binding("shift+tab", "cycle_prompt_mode", "Cycle Mode", show=False),
        Binding("tab", "cycle_prompt_mode", "Cycle Mode", show=False),
        Binding("ctrl+r", "trigger_sync", "Sync", show=False),
        Binding("f5", "trigger_sync", "Sync", show=False),
        Binding("question_mark", "show_help", "Help", show=False),
        Binding("up", "handle_up_arrow", "History Up", show=False),
        Binding("down", "handle_down_arrow", "History Down", show=False),
    ]

    current_view = reactive("today")

    def __init__(self, config: Optional[AppConfig] = None, **kwargs):
        super().__init__(**kwargs)
        self.config: AppConfig = config or load_config()
        self.cal_service = CalendarService(
            demo_mode=self.config.demo_mode,
            gcal_ical_url=self.config.gcal_ical_url,
        )
        self.canvas_service = CanvasService(self.config)

        self.today_events: List[CalendarEvent] = []
        self.week_events: List[CalendarEvent] = []
        self.assignments: List[CanvasAssignment] = []
        self.courses: List[CanvasCourse] = []

        self.header_view = HeaderView(config=self.config)
        self.split_dashboard = SplitDashboardWidget(
            [],
            [],
            is_gcal_connected=self.cal_service.is_connected,
            is_canvas_connected=self.canvas_service.is_configured,
            is_demo=self.config.demo_mode,
        )
        self.canvas_view = ExpandedCanvasWidget()
        self.calendar_view = WeekCalendarWidget()
        self.planner_view = StudyPlannerWidget()
        self.connect_view = ConnectWizardWidget()
        self.help_view = HelpWidget()

        self.prompt_box = PromptBox()
        self.footer_bar = FooterStatusBar()

    def compose(self) -> ComposeResult:
        yield self.header_view
        with Container(id="main-content"):
            yield self.split_dashboard
        yield self.prompt_box
        yield self.footer_bar

    async def on_mount(self) -> None:
        self.title = "jz CLI"
        self.prompt_box.focus_input()
        self.sync_data_worker()

    @work(exclusive=True, thread=True)
    def sync_data_worker(self) -> None:
        """Fetch latest Calendar and Canvas data in background thread."""
        self.call_from_thread(self._set_sync_state, "Syncing...")

        try:
            today_ev = self.cal_service.get_today_events()
            week_ev = self.cal_service.get_upcoming_events(days=7)
            assigns = self.canvas_service.get_upcoming_assignments()
            courses = self.canvas_service.get_courses()
            free_slots = self.cal_service.find_free_slots(days=3)

            self.today_events = today_ev
            self.week_events = week_ev
            self.assignments = assigns
            self.courses = courses

            self.call_from_thread(self._update_all_widgets, today_ev, week_ev, assigns, courses, free_slots)
            self.call_from_thread(self._set_sync_state, "Idle")
        except Exception as e:
            self.call_from_thread(self._set_sync_state, f"Error: {e}")

    def _set_sync_state(self, sys: str) -> None:
        self.footer_bar.system_status = sys
        self.footer_bar.gcal_connected = self.cal_service.is_connected
        self.footer_bar.canvas_connected = self.canvas_service.is_configured
        self.header_view.metadata.gcal_connected = self.cal_service.is_connected
        self.header_view.metadata.canvas_connected = self.canvas_service.is_configured

    def _update_all_widgets(
        self,
        today_ev: List[CalendarEvent],
        week_ev: List[CalendarEvent],
        assigns: List[CanvasAssignment],
        courses: List[CanvasCourse],
        free_slots: list,
    ) -> None:
        self.split_dashboard.update_data(
            today_ev,
            assigns,
            is_gcal_connected=self.cal_service.is_connected,
            is_canvas_connected=self.canvas_service.is_configured,
            is_demo=self.config.demo_mode,
        )
        self.calendar_view.events = week_ev
        self.canvas_view.assignments = assigns
        self.canvas_view.courses = courses
        self.planner_view.assignments = assigns
        self.planner_view.free_slots = free_slots

        self.connect_view.config = self.config
        self.connect_view.gcal_connected = self.cal_service.is_connected
        self.connect_view.canvas_connected = self.canvas_service.is_configured

    def switch_view(self, view_name: str) -> None:
        main_content = self.query_one("#main-content", Container)
        main_content.remove_children()

        if view_name == "today":
            main_content.mount(self.split_dashboard)
        elif view_name == "canvas":
            main_content.mount(self.canvas_view)
        elif view_name == "cal":
            main_content.mount(self.calendar_view)
        elif view_name == "plan":
            main_content.mount(self.planner_view)
        elif view_name in ("connect", "config"):
            main_content.mount(self.connect_view)
        elif view_name == "help":
            main_content.mount(self.help_view)

        self.current_view = view_name
        self.prompt_box.focus_input()

    # Keybinding actions
    def action_quit_app(self) -> None:
        self.exit()

    def action_handle_escape(self) -> None:
        if self.current_view != "today":
            self.switch_view("today")
            self.prompt_box.feedback.clear()
        else:
            self.prompt_box.feedback.clear()

    def action_cycle_prompt_mode(self) -> None:
        new_mode = self.prompt_box.cycle_mode()
        self.notify(f"Mode switched to {new_mode}", title="jz Mode", timeout=1.0)

    def action_trigger_sync(self) -> None:
        self.prompt_box.feedback.show_message("Re-syncing accounts...", "bold cyan")
        self.sync_data_worker()

    def action_show_help(self) -> None:
        self.switch_view("help")

    def action_handle_up_arrow(self) -> None:
        self.prompt_box.text_input.action_history_up()

    def action_handle_down_arrow(self) -> None:
        self.prompt_box.text_input.action_history_down()

    # Prompt Command Handling
    @on(PromptBox.CommandSubmitted)
    def handle_command_submitted(self, event: PromptBox.CommandSubmitted) -> None:
        cmd_raw = event.command.strip()
        mode = event.mode

        if not cmd_raw:
            return

        if cmd_raw.startswith("/"):
            self._handle_slash_command(cmd_raw)
        elif mode == "Command":
            self._handle_slash_command(f"/{cmd_raw}")
        elif mode == "Plan":
            self._handle_plan_prompt(cmd_raw)
        else:
            self._handle_ask_prompt(cmd_raw)

    def _handle_slash_command(self, cmd_line: str) -> None:
        parts = cmd_line.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("/today", "/home"):
            self.switch_view("today")
            self.prompt_box.feedback.show_message("Today's Dashboard", "#00f0ff")

        elif cmd in ("/sync", "/refresh"):
            self.action_trigger_sync()

        elif cmd in ("/connect", "/config"):
            if args:
                self._execute_connect_subcommand(args)
            else:
                self.switch_view("connect")
                self.prompt_box.feedback.show_message("Connect live Google Calendar & Canvas accounts", "#00ff88")

        elif cmd in ("/canvas", "/assignments"):
            self.switch_view("canvas")
            self.prompt_box.feedback.show_message(f"Canvas view: {len(self.assignments)} assignments", "#ff79c6")

        elif cmd in ("/cal", "/calendar", "/week"):
            self.switch_view("cal")
            self.prompt_box.feedback.show_message(f"7-Day Calendar: {len(self.week_events)} events", "#00f0ff")

        elif cmd == "/plan":
            self.switch_view("plan")
            self.prompt_box.feedback.show_message("Study Planner: Correlating free slots with Canvas deadlines", "#50fa7b")

        elif cmd.startswith("/block"):
            self._execute_time_block(args)

        elif cmd == "/demo":
            self.config.demo_mode = not self.config.demo_mode
            save_config(self.config)
            self.cal_service.demo_mode = self.config.demo_mode
            state = "Enabled" if self.config.demo_mode else "Disabled"
            self.prompt_box.feedback.show_message(f"Demo Mode {state}", "bold yellow")
            self.sync_data_worker()

        elif cmd in ("/paths", "/files"):
            items = get_tracked_items()
            paths_str = " | ".join(f"{it.name}: {it.path}" for it in items if it.exists)
            self.prompt_box.feedback.show_message(f"Tracked paths: {paths_str}", "dim white")

        elif cmd == "/uninstall":
            self.prompt_box.feedback.show_message(
                "To cleanly remove jz without a trace, exit and run: jz uninstall --yes",
                "bold yellow",
            )

        elif cmd in ("/help", "/?"):
            self.switch_view("help")
            self.prompt_box.feedback.show_message("Commands & Shortcuts reference", "#50fa7b")

        elif cmd == "/clear":
            self.prompt_box.feedback.clear()
            self.switch_view("today")

        elif cmd in ("/quit", "/exit", "/q"):
            self.exit()

        else:
            self.prompt_box.feedback.show_message(
                f"Unknown command '{cmd}'. Type /help to view available commands.",
                "bold red",
            )

    def _execute_connect_subcommand(self, args: str) -> None:
        """Handle `/connect canvas ...` or `/connect gcal ...`."""
        parts = args.split(maxsplit=2)
        target = parts[0].lower()

        if target == "canvas":
            if len(parts) < 2:
                self.prompt_box.feedback.show_message(
                    "Usage: /connect canvas <feed_url> OR /connect canvas <domain> <token>",
                    "bold yellow",
                )
                return

            if len(parts) == 2 and (".ics" in parts[1] or "feeds/calendars" in parts[1]):
                feed_url = parts[1].strip()
                self.config.canvas_ical_url = feed_url
                self.config.demo_mode = False
                save_config(self.config)
                self.canvas_service.config = self.config
                ok, msg, _ = self.canvas_service.test_connection()
                style = "bold green" if ok else "bold yellow"
                self.prompt_box.feedback.show_message(f"Canvas iCal: {msg}", style)
                self.sync_data_worker()
                return

            if len(parts) >= 3:
                domain, token = parts[1].strip(), parts[2].strip()
                self.config.canvas_url = domain
                self.config.canvas_token = token
                self.config.demo_mode = False
                save_config(self.config)
                self.canvas_service.config = self.config
                ok, msg, profile = self.canvas_service.test_connection()
                if ok:
                    if profile.get("primary_email"):
                        self.config.user_email = profile["primary_email"]
                        self.header_view.metadata.user_email = self.config.user_email
                    if profile.get("name"):
                        self.config.user_name = profile["name"]
                    save_config(self.config)
                    self.prompt_box.feedback.show_message(f"Connected: {msg}", "bold green")
                    self.sync_data_worker()
                else:
                    self.prompt_box.feedback.show_message(f"Canvas Warning: {msg}", "bold yellow")
                return

            self.prompt_box.feedback.show_message(
                "Usage: /connect canvas <domain> <token>", "bold yellow"
            )

        elif target in ("gcal", "calendar"):
            if len(parts) < 2:
                self.prompt_box.feedback.show_message(
                    "Usage: /connect gcal <private_ical_url>", "bold yellow"
                )
                return
            gcal_url = parts[1].strip()
            self.config.gcal_ical_url = gcal_url
            self.config.demo_mode = False
            save_config(self.config)
            self.cal_service.gcal_ical_url = gcal_url
            self.prompt_box.feedback.show_message("Google Calendar linked via iCal feed!", "bold green")
            self.sync_data_worker()

        else:
            self.prompt_box.feedback.show_message(
                "Usage: /connect canvas <url/token> OR /connect gcal <url>", "bold yellow"
            )

    def _execute_time_block(self, args: str) -> None:
        if not args:
            self.prompt_box.feedback.show_message(
                "Usage: /block <duration> <title> (e.g. /block 2h CS 2110 HW)", "bold yellow"
            )
            return

        match = re.match(r"^(\d+(?:\.\d+)?)\s*([hmHM])?\s+(.+)$", args)
        if not match:
            duration_mins = 60
            title = args
        else:
            qty = float(match.group(1))
            unit = (match.group(2) or "h").lower()
            title = match.group(3).strip()
            duration_mins = int(qty * 60) if unit == "h" else int(qty)

        success, msg = self.cal_service.create_time_block(title, duration_mins)
        style = "bold #50fa7b" if success else "bold red"
        self.prompt_box.feedback.show_message(msg, style)
        if success:
            self.sync_data_worker()

    def _handle_plan_prompt(self, prompt: str) -> None:
        lower = prompt.lower()
        if any(w in lower for w in ["study", "plan", "free", "schedule", "suggest"]):
            self.switch_view("plan")
            self.prompt_box.feedback.show_message(
                "Generated study recommendations based on your free slots and upcoming Canvas deadlines.",
                "bold #50fa7b",
            )
        elif lower.startswith("block "):
            self._execute_time_block(prompt[6:])
        else:
            self.switch_view("plan")
            self.prompt_box.feedback.show_message(
                f"Plan Analysis for '{prompt}': Check suggested focus windows above.",
                "bold #50fa7b",
            )

    def _handle_ask_prompt(self, prompt: str) -> None:
        lower = prompt.lower()
        now = datetime.datetime.now().astimezone()

        if "due today" in lower or "tonight" in lower:
            today_deadlines = [a for a in self.assignments if a.due_at and a.due_at.date() == now.date()]
            if today_deadlines:
                items_str = ", ".join(f"[{a.course_code}] {a.name} ({a.points_possible:.0f} pts)" for a in today_deadlines)
                self.prompt_box.feedback.show_message(f"Due today: {items_str}", "bold yellow")
            else:
                self.prompt_box.feedback.show_message("No assignments due today! You're clear.", "bold green")

        elif "due tomorrow" in lower:
            tomorrow_date = (now + datetime.timedelta(days=1)).date()
            tmrw = [a for a in self.assignments if a.due_at and a.due_at.date() == tomorrow_date]
            if tmrw:
                items_str = ", ".join(f"[{a.course_code}] {a.name}" for a in tmrw)
                self.prompt_box.feedback.show_message(f"Due tomorrow: {items_str}", "bold cyan")
            else:
                self.prompt_box.feedback.show_message("Nothing due tomorrow.", "bold green")

        elif "next class" in lower or "next meeting" in lower or "next event" in lower:
            upcoming_today = [e for e in self.today_events if e.end_time > now and not e.is_all_day]
            if upcoming_today:
                nxt = upcoming_today[0]
                badge = nxt.get_status_badge(now)[0]
                self.prompt_box.feedback.show_message(
                    f"Next event: {nxt.title} at {nxt.start_time.strftime('%I:%M %p')} {badge}",
                    "bold #00f0ff",
                )
            else:
                self.prompt_box.feedback.show_message("No more classes or meetings remaining on today's calendar.", "bold green")

        elif "free" in lower or "free time" in lower:
            free = self.cal_service.find_free_slots(days=1)
            if free:
                slots_str = ", ".join(f"{s[0].strftime('%I:%M %p')}-{s[1].strftime('%I:%M %p')} ({s[2]}m)" for s in free[:3])
                self.prompt_box.feedback.show_message(f"Free slots today: {slots_str}", "bold #50fa7b")
            else:
                self.prompt_box.feedback.show_message("Schedule is packed today. No open slots.", "bold yellow")

        else:
            self.prompt_box.feedback.show_message(
                f"Assistant: {len(self.today_events)} events today, {len(self.assignments)} pending assignments.",
                "bright_white",
            )
