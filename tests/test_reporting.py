"""Tests for the reporting engine using synthetic RunData objects."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from agentbench.reporting.comparison import ComparisonEngine
from agentbench.reporting.data import ExperimentData, RunData
from agentbench.reporting.reporter import Reporter


def _make_run(
    task_id: str,
    agent_name: str,
    run_id: str,
    passed: bool,
    failure_category: str | None = None,
    total_tokens: int = 1000,
    total_turns: int = 5,
    wall_clock_seconds: float = 30.0,
) -> RunData:
    return RunData(
        task_id=task_id,
        agent_name=agent_name,
        run_id=run_id,
        passed=passed,
        score=None,
        result=None,
        failure_category=failure_category,
        total_tokens=total_tokens,
        total_turns=total_turns,
        wall_clock_seconds=wall_clock_seconds,
    )


def _make_experiment(*runs: RunData) -> ExperimentData:
    return ExperimentData(base_dir=Path("."), runs=list(runs))


def _silent_console() -> Console:
    return Console(file=StringIO(), highlight=False)


# --- ExperimentData helpers ---


def test_pass_rate_all_agents() -> None:
    data = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True),
        _make_run("task-b", "agent-1", "r2", passed=False),
    )
    assert data.pass_rate() == pytest.approx(0.5)


def test_pass_rate_by_agent() -> None:
    data = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True),
        _make_run("task-b", "agent-1", "r2", passed=False),
        _make_run("task-a", "agent-2", "r3", passed=True),
        _make_run("task-b", "agent-2", "r4", passed=True),
    )
    assert data.pass_rate("agent-1") == pytest.approx(0.5)
    assert data.pass_rate("agent-2") == pytest.approx(1.0)


def test_failure_distribution() -> None:
    data = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=False, failure_category="incomplete_fix"),
        _make_run("task-b", "agent-1", "r2", passed=False, failure_category="incomplete_fix"),
        _make_run("task-c", "agent-1", "r3", passed=False, failure_category="timeout_or_loop"),
    )
    dist = data.failure_distribution()
    assert dist["incomplete_fix"] == 2
    assert dist["timeout_or_loop"] == 1


def test_by_agent_grouping() -> None:
    data = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True),
        _make_run("task-b", "agent-2", "r2", passed=False),
    )
    groups = data.by_agent()
    assert set(groups.keys()) == {"agent-1", "agent-2"}
    assert len(groups["agent-1"]) == 1
    assert len(groups["agent-2"]) == 1


# --- Reporter ---


def test_summary_table_renders() -> None:
    data = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True),
        _make_run("task-b", "agent-1", "r2", passed=False, failure_category="context_miss"),
        _make_run("task-a", "agent-2", "r3", passed=True),
        _make_run("task-b", "agent-2", "r4", passed=True),
    )
    reporter = Reporter(_silent_console())
    reporter.summary_table(data)  # should not raise


def test_detail_table_renders() -> None:
    data = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True),
        _make_run("task-b", "agent-1", "r2", passed=False, failure_category="no_verification"),
    )
    reporter = Reporter(_silent_console())
    reporter.detail_table(data)  # should not raise


def test_failure_report_renders() -> None:
    data = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=False, failure_category="incomplete_fix"),
        _make_run("task-b", "agent-1", "r2", passed=False, failure_category="context_miss"),
    )
    reporter = Reporter(_silent_console())
    reporter.failure_report(data)  # should not raise


def test_markdown_report_contains_sections() -> None:
    data = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True, total_tokens=800),
        _make_run(
            "task-b",
            "agent-1",
            "r2",
            passed=False,
            failure_category="context_miss",
            total_tokens=1200,
        ),
    )
    reporter = Reporter(_silent_console())
    md = reporter.markdown_report(data)

    assert "## Summary" in md
    assert "## Failure Analysis" in md
    assert "## Efficiency Comparison" in md
    assert "## Per-Task Results" in md
    assert "agent-1" in md


# --- ComparisonEngine ---


def test_comparison_pass_rate_delta() -> None:
    baseline = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True),
        _make_run("task-b", "agent-1", "r2", passed=False),
    )
    candidate = _make_experiment(
        _make_run("task-a", "agent-2", "r3", passed=True),
        _make_run("task-b", "agent-2", "r4", passed=True),
    )
    engine = ComparisonEngine()
    result = engine.compare(baseline, candidate)
    assert result.baseline_pass_rate == pytest.approx(0.5)
    assert result.candidate_pass_rate == pytest.approx(1.0)
    assert result.pass_rate_delta == pytest.approx(0.5)


def test_comparison_mcnemar_p_value_range() -> None:
    baseline = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True),
        _make_run("task-b", "agent-1", "r2", passed=False),
        _make_run("task-c", "agent-1", "r3", passed=True),
        _make_run("task-d", "agent-1", "r4", passed=False),
    )
    candidate = _make_experiment(
        _make_run("task-a", "agent-2", "r5", passed=False),
        _make_run("task-b", "agent-2", "r6", passed=True),
        _make_run("task-c", "agent-2", "r7", passed=True),
        _make_run("task-d", "agent-2", "r8", passed=True),
    )
    engine = ComparisonEngine()
    result = engine.compare(baseline, candidate)
    assert 0.0 <= result.p_value <= 1.0


def test_unique_solves() -> None:
    baseline = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True),
        _make_run("task-b", "agent-1", "r2", passed=False),
    )
    candidate = _make_experiment(
        _make_run("task-a", "agent-2", "r3", passed=False),
        _make_run("task-b", "agent-2", "r4", passed=True),
    )
    engine = ComparisonEngine()
    result = engine.compare(baseline, candidate)
    assert "task-a" in result.unique_baseline_solves
    assert "task-b" in result.unique_candidate_solves


def test_comparison_print_no_error() -> None:
    baseline = _make_experiment(
        _make_run("task-a", "agent-1", "r1", passed=True, total_tokens=1000),
    )
    candidate = _make_experiment(
        _make_run("task-a", "agent-2", "r2", passed=True, total_tokens=500),
    )
    engine = ComparisonEngine()
    result = engine.compare(baseline, candidate)
    engine.print_comparison(result, _silent_console())  # should not raise
