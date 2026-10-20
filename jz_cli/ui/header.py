"""
Header widget for jz CLI: Modern ASCII logo, session metadata block,
and dismissible notice/tips banner.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget

from jz_cli import __version__
from jz_cli.config import AppConfig


ASCII_LOGO = [
    "   ██╗███████╗",
    "   ██║╚══███╔╝",
    "   ██║  ███╔╝ ",
    "██ ██║ ███╔╝  ",
    "╚████║███████╗",
    " ╚═══╝╚══════╝",
]


class JZLogo(Widget):
    """Renders the vibrant ANSI ASCII logo for jz."""

    DEFAULT_CSS = """
    JZLogo {
        width: 18;
        height: 6;
        margin: 0 1 0 1;
        content-align: center middle;
    }
    """

    def render(self) -> RenderableType:
        table = Table.grid(padding=0)
        colors = ["#00f0ff", "#00d4ff", "#00b4d8", "#0096c7", "#0077b6", "#023e8a"]
        for i, line in enumerate(ASCII_LOGO):
            col = colors[i % len(colors)]
            table.add_row(Text(line, style=f"bold {col}"))
        return table


class SessionMetadata(Widget):
    """Displays CLI version, connected student account, profile, and current working path."""

    DEFAULT_CSS = """
    SessionMetadata {
        height: 6;
        width: 1fr;
        padding: 0 1;
        content-align: left middle;
    }
    """

    user_email = reactive("student@university.edu")
    active_profile = reactive("Default")
    current_path = reactive("")

    def __init__(self, config: Optional[AppConfig] = None, **kwargs):
        super().__init__(**kwargs)
        if config:
            self.user_email = config.user_email or "student@university.edu"
            self.active_profile = config.active_profile or "Default"
        try:
            cwd = Path.cwd()
            home = Path.home()
            # Replace home with ~ if under home
            if str(cwd).startswith(str(home)):
                self.current_path = "~" + str(cwd)[len(str(home)):]
            else:
                self.current_path = str(cwd)
        except Exception:
            self.current_path = os.getcwd()

    def render(self) -> RenderableType:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold cyan", justify="right", width=14)
        table.add_column(style="bright_white")

        table.add_row(
            Text("jz CLI", style="bold #00ff88"),
            Text(f"v{__version__}  ·  Cross-Platform Terminal Productivity", style="dim white"),
        )
        table.add_row(
            Text("Connected:", style="#00f0ff"),
            Text.assemble(
                (self.user_email, "bold bright_white"),
                ("  ·  Profile: ", "dim white"),
                (f"[{self.active_profile}]", "bold #ffb86c"),
            ),
        )
        table.add_row(
            Text("Workspace:", style="#bd93f9"),
            Text(self.current_path, style="dim #8be9fd"),
        )
        table.add_row(
            Text("Integrations:", style="#50fa7b"),
            Text.assemble(
                ("Google Calendar ", "bold #50fa7b"),
                ("●", "green"),
                ("  ·  Canvas LMS ", "bold #00f0ff"),
                ("●", "cyan"),
            ),
        )
        return table


class NoticeBanner(Widget):
    """
    Notice and tips banner with a solid vertical bar on the left,
    dismissible with Esc.
    """

    DEFAULT_CSS = """
    NoticeBanner {
        height: 3;
        margin: 0 1 1 1;
        background: #111827;
        padding: 0 1;
        border-left: wide #f1fa8c;
    }
    """

    visible_notice = reactive(True)
    tip_text = reactive(
        "Tip: Use /plan to auto-generate focus blocks from upcoming deadlines · Shift+Tab to switch mode · Esc to dismiss banner"
    )

    def dismiss(self) -> None:
        self.visible_notice = False
        self.display = False

    def render(self) -> RenderableType:
        if not self.visible_notice:
            return Text("")

        text = Text.assemble(
            ("▌ ", "bold #f1fa8c"),
            ("NOTICE: ", "bold #f1fa8c"),
            (self.tip_text, "white"),
            ("  [Esc to dismiss]", "dim italic white"),
        )
        return text


class HeaderView(Widget):
    """Combined Header widget containing Logo, Metadata, and Notice Banner."""

    DEFAULT_CSS = """
    HeaderView {
        height: auto;
        dock: top;
        background: #0d1117;
        border-bottom: heavy #30363d;
        padding: 0 1;
    }

    #top-row {
        height: 6;
        align: left middle;
    }
    """

    def __init__(self, config: Optional[AppConfig] = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.notice = NoticeBanner()

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-row"):
            yield JZLogo()
            yield SessionMetadata(config=self.config)
        yield self.notice

    def dismiss_notice(self) -> bool:
        if self.notice.visible_notice:
            self.notice.dismiss()
            return True
        return False
