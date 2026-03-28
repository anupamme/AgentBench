"""Tests for TerminalReporter using Rich console output capture."""

from __future__ import annotations

from io import StringIO
from typing import Any

import pytest
from rich.console import Console

from agentbench.reporting.terminal import TerminalReporter


def _silent_reporter() -> tuple[TerminalReporter, StringIO]:
    buf = StringIO()
    console = Console(file=buf, highlight=False, width=120)
    return TerminalReporter(console=console), buf


@pytest.fixture
def mock_passing_score() -> dict[str, Any]:
    """A flat score dict for a passing run."""
    return {
        "task_id": "python-bug-fix-calculator",
        "agent_name": "anthropic-api",
        "primary_pass": True,
        "failure_class": None,
        "total_tokens": 12345,
        "total_turns": 5,
        "wall_clock_seconds": 8.2,
        "process_score": 0.95,
        "difficulty": "easy",
    }


@pytest.fixture
def mock_failing_score() -> dict[str, Any]:
    """A flat score dict for a failing run."""
    return {
        "task_id": "py-debug-memory-leak",
        "agent_name": "anthropic-api",
        "primary_pass": False,
        "failure_class": "context_miss",
        "total_tokens": 89000,
        "total_turns": 22,
        "wall_clock_seconds": 45.3,
        "process_score": 0.40,
        "difficulty": "hard",
    }


# --- print_run_result ---


def test_print_run_result_pass(mock_passing_score: dict[str, Any]) -> None:
    reporter, buf = _silent_reporter()
    reporter.print_run_result(mock_passing_score)
    output = buf.getvalue()
    assert "✓" in output
    assert "python-bug-fix-calculator" in output


def test_print_run_result_fail(mock_failing_score: dict[str, Any]) -> None:
    reporter, buf = _silent_reporter()
    reporter.print_run_result(mock_failing_score)
    output = buf.getvalue()
    assert "✗" in output
    assert "context_miss" in output


# --- print_suite_summary ---


def _make_run(
    task_id: str,
    passed: bool,
    failure_class: str | None = None,
    tokens: int = 1000,
    turns: int = 5,
    wall_clock: float = 10.0,
    difficulty: str = "medium",
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "primary_pass": passed,
        "failure_class": failure_class,
        "total_tokens": tokens,
        "total_turns": turns,
        "wall_clock_seconds": wall_clock,
        "difficulty": difficulty,
    }


def test_print_suite_summary_rows() -> None:
    runs = [
        _make_run("task-alpha", passed=True),
        _make_run("task-beta", passed=True),
        _make_run("task-gamma", passed=False, failure_class="timeout_or_loop"),
        _make_run("task-delta", passed=True),
        _make_run("task-epsilon", passed=False, failure_class="context_miss"),
    ]
    reporter, buf = _silent_reporter()
    reporter.print_suite_summary(runs)
    output = buf.getvalue()
    for task_id in ["task-alpha", "task-beta", "task-gamma", "task-delta", "task-epsilon"]:
        assert task_id in output


def test_print_suite_summary_footer() -> None:
    runs = [
        _make_run("task-a", passed=True),
        _make_run("task-b", passed=True),
        _make_run("task-c", passed=True),
        _make_run("task-d", passed=False),
        _make_run("task-e", passed=False),
    ]
    reporter, buf = _silent_reporter()
    reporter.print_suite_summary(runs)
    output = buf.getvalue()
    # Footer should show 3 passes out of 5
    assert "3/5" in output
    assert "60.0%" in output


# --- print_failure_distribution ---


def test_print_failure_distribution_bars() -> None:
    failure_counts = {"context_miss": 15, "no_verification": 8}
    reporter, buf = _silent_reporter()
    reporter.print_failure_distribution(failure_counts)
    output = buf.getvalue()
    assert "context_miss" in output
    assert "no_verification" in output
    assert "█" in output


# --- print_agent_comparison ---


def test_print_agent_comparison_columns() -> None:
    experiment_summary: dict[str, Any] = {
        "by_agent": {
            "claude-api": [
                {"task_id": "task-a", "primary_pass": True, "total_tokens": 5000},
                {
                    "task_id": "task-b",
                    "primary_pass": False,
                    "failure_class": "timeout_or_loop",
                    "total_tokens": 90000,
                },
            ],
            "aider": [
                {
                    "task_id": "task-a",
                    "primary_pass": False,
                    "failure_class": "context_miss",
                    "total_tokens": 8000,
                },
                {"task_id": "task-b", "primary_pass": True, "total_tokens": 45000},
            ],
        }
    }
    reporter, buf = _silent_reporter()
    reporter.print_agent_comparison(experiment_summary)
    output = buf.getvalue()
    assert "claude-api" in output
    assert "aider" in output


# --- print_task_list ---


def test_print_task_list_rows() -> None:
    tasks: list[dict[str, Any]] = [
        {
            "id": "bug-fix-calc",
            "difficulty": "easy",
            "task_type": "bug_fix",
            "languages": ["python"],
            "tags": ["math"],
        },
        {
            "id": "refactor-auth",
            "difficulty": "medium",
            "task_type": "refactor",
            "languages": ["python", "js"],
            "tags": [],
        },
        {
            "id": "perf-query",
            "difficulty": "hard",
            "task_type": "performance",
            "languages": ["sql"],
            "tags": ["db"],
        },
    ]
    reporter, buf = _silent_reporter()
    reporter.print_task_list(tasks)
    output = buf.getvalue()
    assert "bug-fix-calc" in output
    assert "refactor-auth" in output
    assert "perf-query" in output
    assert "easy" in output
    assert "medium" in output
    assert "hard" in output


# --- print_experiment_comparison ---


def test_print_experiment_comparison_arrows() -> None:
    comparison: dict[str, Any] = {
        "agent_deltas": {
            "claude-api": {"a_rate": 0.72, "b_rate": 0.78, "delta": 0.06, "p_value": 0.03},
        },
        "flipped_pass_to_fail": [],
        "flipped_fail_to_pass": [
            {"task_id": "task-c", "agent": "claude-api", "prev_failure_class": "context_miss"}
        ],
        "failure_shifts": {},
    }
    reporter, buf = _silent_reporter()
    reporter.print_experiment_comparison(comparison)
    output = buf.getvalue()
    assert "↑" in output
