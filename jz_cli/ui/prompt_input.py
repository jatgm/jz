"""
Interactive Prompt Box & Footer Status Bar for jz CLI:
- Distinct neon-bordered outline box (Cursor / Claude Code style)
- Mode toggle indicator (◉ Plan / ◉ Command / ◉ Ask) with Shift+Tab cycling
- Command history navigation (Up / Down arrows)
- Sleek footer shortcuts & sync status bar
"""

from __future__ import annotations

from typing import List, Optional

from rich.align import Align
from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input


MODES = ["Plan", "Command", "Ask"]
MODE_COLORS = {
    "Plan": "#50fa7b",      # Neon Green
    "Command": "#00f0ff",   # Cyan
    "Ask": "#bd93f9",       # Purple
}
MODE_PLACEHOLDERS = {
    "Plan": "Plan mode: type /plan, /block 2h study, or ask for focus schedules...",
    "Command": "Command mode: type /today, /canvas, /cal, /sync, /config, or /help...",
    "Ask": "Ask mode: 'What is due tonight?', 'When is my next class?', 'Am I free at 2pm?'...",
}


class ModeIndicator(Widget):
    """Renders the mode toggle indicator directly beneath the input box."""

    DEFAULT_CSS = """
    ModeIndicator {
        height: 1;
        margin: 0 1 0 1;
        padding: 0 1;
    }
    """

    current_mode = reactive("Plan")

    def render(self) -> RenderableType:
        color = MODE_COLORS.get(self.current_mode, "#50fa7b")
        text = Text.assemble(
            (f"◉ {self.current_mode} ", f"bold {color}"),
            ("(shift+tab to cycle modes: Plan · Command · Ask)", "dim white"),
        )
        return text


class PromptFeedback(Widget):
    """Displays output feedback or messages from executed commands."""

    DEFAULT_CSS = """
    PromptFeedback {
        height: auto;
        max-height: 4;
        margin: 0 1;
        padding: 0 1;
        background: #161b22;
        border-left: wide #00ff88;
        display: none;
    }
    """

    feedback_text = reactive("")
    feedback_style = reactive("bold #00ff88")

    def show_message(self, text: str, style: str = "bold #00ff88") -> None:
        self.feedback_text = text
        self.feedback_style = style
        self.display = True

    def clear(self) -> None:
        self.feedback_text = ""
        self.display = False

    def render(self) -> RenderableType:
        if not self.feedback_text:
            return Text("")
        return Text(self.feedback_text, style=self.feedback_style)


class CustomInput(Input):
    """Input widget customized with history navigation and mode cycle forwarding."""

    class ModeCycleRequested(Message):
        """Message fired when Shift+Tab or Tab is pressed inside input."""
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history: List[str] = []
        self.history_index: int = -1
        self.current_draft: str = ""

    def add_to_history(self, command: str) -> None:
        cmd = command.strip()
        if cmd and (not self.history or self.history[-1] != cmd):
            self.history.append(cmd)
        self.history_index = -1
        self.current_draft = ""

    def action_history_up(self) -> None:
        if not self.history:
            return

        if self.history_index == -1:
            self.current_draft = self.value
            self.history_index = len(self.history) - 1
        elif self.history_index > 0:
            self.history_index -= 1

        self.value = self.history[self.history_index]
        self.cursor_position = len(self.value)

    def action_history_down(self) -> None:
        if self.history_index == -1:
            return

        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.value = self.history[self.history_index]
        else:
            self.history_index = -1
            self.value = self.current_draft

        self.cursor_position = len(self.value)


class PromptBox(Widget):
    """
    Interactive prompt container with neon rounded border,
    dynamic placeholder, history, and mode indicator.
    """

    DEFAULT_CSS = """
    PromptBox {
        height: auto;
        dock: bottom;
        background: #0d1117;
        padding: 0 1;
    }

    #input-frame {
        border: round #00ff88;
        background: #0d1117;
        height: 3;
        margin: 0 1;
        padding: 0 1;
    }

    #prompt-text-input {
        background: transparent;
        border: none;
        height: 1;
        padding: 0;
        color: #ffffff;
    }

    #prompt-text-input:focus {
        border: none;
    }
    """

    current_mode = reactive("Plan")

    class CommandSubmitted(Message):
        """Event emitted when a prompt command is submitted."""
        def __init__(self, command: str, mode: str) -> None:
            super().__init__()
            self.command = command
            self.mode = mode

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode_indicator = ModeIndicator()
        self.feedback = PromptFeedback()
        self.text_input = CustomInput(
            id="prompt-text-input",
            placeholder=MODE_PLACEHOLDERS["Plan"],
        )

    def compose(self) -> ComposeResult:
        yield self.feedback
        with Container(id="input-frame"):
            yield self.text_input
        yield self.mode_indicator

    def cycle_mode(self) -> str:
        """Cycle between Plan -> Command -> Ask modes."""
        curr_idx = MODES.index(self.current_mode) if self.current_mode in MODES else 0
        next_idx = (curr_idx + 1) % len(MODES)
        self.current_mode = MODES[next_idx]
        self.mode_indicator.current_mode = self.current_mode

        # Update input border and placeholder
        color = MODE_COLORS[self.current_mode]
        input_frame = self.query_one("#input-frame", Container)
        input_frame.styles.border = ("round", color)
        self.text_input.placeholder = MODE_PLACEHOLDERS[self.current_mode]

        return self.current_mode

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        if not cmd:
            return
        self.text_input.add_to_history(cmd)
        self.text_input.value = ""
        self.post_message(self.CommandSubmitted(command=cmd, mode=self.current_mode))

    def focus_input(self) -> None:
        self.text_input.focus()


class FooterStatusBar(Widget):
    """
    Bottom footer status bar with quick shortcuts hint on the left
    and live sync status on the right.
    """

    DEFAULT_CSS = """
    FooterStatusBar {
        height: 1;
        dock: bottom;
        background: #161b22;
        color: #8b949e;
        padding: 0 2;
    }
    """

    gcal_sync_status = reactive("Synced")
    canvas_sync_status = reactive("Synced")
    system_status = reactive("Idle")

    def render(self) -> RenderableType:
        table = Table.grid(expand=True)
        table.add_column("shortcuts", justify="left")
        table.add_column("sync_status", justify="right")

        # Shortcuts hint
        shortcuts = Text.assemble(
            ("? ", "bold #50fa7b"),
            ("help  ·  ", "dim white"),
            ("/ ", "bold #00f0ff"),
            ("commands  ·  ", "dim white"),
            ("@ ", "bold #bd93f9"),
            ("context  ·  ", "dim white"),
            ("! ", "bold #ffb86c"),
            ("shell  ·  ", "dim white"),
            ("q ", "bold #ff5555"),
            ("quit", "dim white"),
        )

        # Sync status
        gcal_col = "green" if self.gcal_sync_status == "Synced" else "yellow"
        canvas_col = "green" if self.canvas_sync_status == "Synced" else "yellow"
        sys_col = "cyan" if self.system_status == "Idle" else "bold yellow"

        sync_info = Text.assemble(
            ("Google Cal: ", "dim white"),
            (f"{self.gcal_sync_status} ● ", gcal_col),
            (" ·  Canvas: ", "dim white"),
            (f"{self.canvas_sync_status} ● ", canvas_col),
            (" ·  Status: ", "dim white"),
            (self.system_status, sys_col),
        )

        table.add_row(shortcuts, sync_info)
        return table
