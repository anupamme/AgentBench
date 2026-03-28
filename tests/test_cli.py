"""Tests for the CLI interface."""
from __future__ import annotations

from typer.testing import CliRunner

from agentbench.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "agentbench" in result.stdout.lower() or "eval" in result.stdout.lower()


def test_run_requires_task_or_suite():
    result = runner.invoke(app, ["run", "--agent", "test"])
    assert result.exit_code != 0
    assert "task" in result.stdout.lower() or "suite" in result.stdout.lower()


def test_validate_missing_file():
    result = runner.invoke(app, ["validate", "fake.yaml"])
    assert result.exit_code != 0
    assert "fake.yaml" in result.stdout.lower()


def test_report_empty_dir():
    result = runner.invoke(app, ["report", "fake_dir/"])
    assert result.exit_code != 0
