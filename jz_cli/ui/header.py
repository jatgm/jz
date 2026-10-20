"""
Clean, minimal header widget for jz CLI:
Compact 3-line ASCII logo and session metadata.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget

from jz_cli import __version__
from jz_cli.config import AppConfig

COMPACT_LOGO = [
    " ██╗███████╗",
    " ██║  ███╔╝ ",
    "╚██║ ██████╗",
]


class JZLogo(Widget):
    """Renders a sleek, compact 3-line ANSI logo."""

    DEFAULT_CSS = """
    JZLogo {
        width: 14;
        height: 3;
        margin: 0 1 0 0;
        content-align: left middle;
    }
    """

    def render(self) -> RenderableType:
        table = Table.grid(padding=0)
        colors = ["#00f0ff", "#00d4ff", "#00b4d8"]
        for i, line in enumerate(COMPACT_LOGO):
            table.add_row(Text(line, style=f"bold {colors[i]}"))
        return table


class SessionMetadata(Widget):
    """Displays CLI version, connected account, and connection indicators."""

    DEFAULT_CSS = """
    SessionMetadata {
        height: 3;
        width: 1fr;
        padding: 0 1;
        content-align: left middle;
    }
    """

    user_email = reactive("")
    active_profile = reactive("Default")
    gcal_connected = reactive(False)
    canvas_connected = reactive(False)

    def __init__(self, config: Optional[AppConfig] = None, **kwargs):
        super().__init__(**kwargs)
        if config:
            self.user_email = config.user_email or "Not signed in"
            self.active_profile = config.active_profile or "Default"
            self.gcal_connected = config.is_google_configured
            self.canvas_connected = config.is_canvas_configured

    def render(self) -> RenderableType:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold bright_white")

        # Line 1: Title & Version
        title_line = Text.assemble(
            ("jz ", "bold #00ff88"),
            (f"v{__version__}  ·  ", "dim white"),
            (self.user_email if self.user_email else "No account connected", "bright_white"),
            (f"  [{self.active_profile}]", "dim yellow"),
        )
        table.add_row(title_line)

        # Line 2: Status
        gcal_badge = ("Google Cal: Connected ●", "bold green") if self.gcal_connected else ("Google Cal: Disconnected ○", "dim white")
        canvas_badge = ("Canvas: Connected ●", "bold cyan") if self.canvas_connected else ("Canvas: Disconnected ○", "dim white")

        status_line = Text.assemble(
            gcal_badge,
            ("   ", "dim white"),
            canvas_badge,
            ("   ·   Type ", "dim white"),
            ("/connect", "bold #00f0ff"),
            (" to link or ", "dim white"),
            ("/help", "bold #50fa7b"),
            (" for commands", "dim white"),
        )
        table.add_row(status_line)

        return table


class NoticeBanner(Widget):
    """Optional notice banner."""
    visible_notice = reactive(False)

    def dismiss(self) -> None:
        self.visible_notice = False
        self.display = False

    def render(self) -> RenderableType:
        return Text("")


class HeaderView(Widget):
    """Combined minimalist Header."""

    DEFAULT_CSS = """
    HeaderView {
        height: 4;
        dock: top;
        background: transparent;
        border-bottom: solid #21262d;
        padding: 0 1;
        margin-bottom: 1;
    }
    """

    def __init__(self, config: Optional[AppConfig] = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.metadata = SessionMetadata(config=self.config)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield JZLogo()
            yield self.metadata

    def dismiss_notice(self) -> bool:
        return False
