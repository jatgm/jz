"""
Integration tests for the JZApp Textual TUI.
"""

import pytest
from jz_cli.config import AppConfig
from jz_cli.ui.app import JZApp


@pytest.mark.asyncio
async def test_app_lifecycle_and_default_view():
    cfg = AppConfig(demo_mode=True)
    app = JZApp(config=cfg)

    async with app.run_test() as pilot:
        # Check initial view
        assert app.current_view == "today"

        # Check prompt box mode
        assert app.prompt_box.current_mode == "Plan"

        # Cycle modes
        app.action_cycle_prompt_mode()
        assert app.prompt_box.current_mode == "Command"

        app.action_cycle_prompt_mode()
        assert app.prompt_box.current_mode == "Ask"

        app.action_cycle_prompt_mode()
        assert app.prompt_box.current_mode == "Plan"


@pytest.mark.asyncio
async def test_app_slash_commands():
    cfg = AppConfig(demo_mode=True)
    app = JZApp(config=cfg)

    async with app.run_test() as pilot:
        # Test /canvas
        app._handle_slash_command("/canvas")
        await pilot.pause()
        assert app.current_view == "canvas"

        # Test /cal
        app._handle_slash_command("/cal")
        await pilot.pause()
        assert app.current_view == "cal"

        # Test /plan
        app._handle_slash_command("/plan")
        await pilot.pause()
        assert app.current_view == "plan"

        # Test /config
        app._handle_slash_command("/config")
        await pilot.pause()
        assert app.current_view in ("config", "connect")

        # Test /help
        app._handle_slash_command("/help")
        await pilot.pause()
        assert app.current_view == "help"

        # Test /today
        app._handle_slash_command("/today")
        await pilot.pause()
        assert app.current_view == "today"


@pytest.mark.asyncio
async def test_app_time_block_command():
    cfg = AppConfig(demo_mode=True)
    app = JZApp(config=cfg)

    async with app.run_test() as pilot:
        app._execute_time_block("2h CS 2110 Midterm prep")
        await pilot.pause()
        assert "CS 2110 Midterm prep" in app.prompt_box.feedback.feedback_text


@pytest.mark.asyncio
async def test_app_escape_and_ask_mode():
    cfg = AppConfig(demo_mode=True)
    app = JZApp(config=cfg)

    async with app.run_test() as pilot:
        # Switch to help then escape back to today
        app._handle_slash_command("/help")
        await pilot.pause()
        assert app.current_view == "help"

        app.action_handle_escape()
        await pilot.pause()
        assert app.current_view == "today"

        # Test /connect
        app._handle_slash_command("/connect")
        await pilot.pause()
        assert app.current_view == "connect"

        # Test /paths
        app._handle_slash_command("/paths")
        await pilot.pause()
        assert "Tracked paths" in app.prompt_box.feedback.feedback_text

        # Test ask mode queries
        app._handle_ask_prompt("What is due today?")
        assert "Due today" in app.prompt_box.feedback.feedback_text or "No assignments due today" in app.prompt_box.feedback.feedback_text

        app._handle_ask_prompt("When is my next class?")
        assert "Next event" in app.prompt_box.feedback.feedback_text or "No more classes" in app.prompt_box.feedback.feedback_text


