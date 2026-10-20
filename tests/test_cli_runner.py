"""
CLI command tests using Typer CliRunner.
"""

from typer.testing import CliRunner
from jz_cli.main import cli

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "jz CLI v0.1.0" in result.stdout


def test_cli_today():
    result = runner.invoke(cli, ["today"])
    assert result.exit_code == 0
    assert "Today's Agenda" in result.stdout
    assert "Canvas Deadlines Due Today" in result.stdout


def test_cli_canvas():
    result = runner.invoke(cli, ["canvas"])
    assert result.exit_code == 0
    assert "Canvas LMS" in result.stdout
    assert "CS 2110" in result.stdout


def test_cli_cal():
    result = runner.invoke(cli, ["cal", "--days", "3"])
    assert result.exit_code == 0
    assert "Google Calendar" in result.stdout


def test_cli_sync():
    result = runner.invoke(cli, ["sync"])
    assert result.exit_code == 0
    assert "Testing integrations" in result.stdout


def test_cli_config():
    result = runner.invoke(cli, ["config"])
    assert result.exit_code == 0
    assert "jz Configuration" in result.stdout
