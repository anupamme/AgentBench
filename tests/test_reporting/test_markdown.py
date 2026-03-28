"""Tests for MarkdownReporter using Jinja2 templates."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agentbench.reporting.markdown import MarkdownReporter

if TYPE_CHECKING:
    from pathlib import Path


def _make_suite_summary(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "name": "test-experiment",
        "created_at": "2026-03-28",
        "suite_name": "python-bugs",
        "total_tasks": 2,
        "total_runs": 4,
        "total_failed": 2,
        "by_agent": {
            "claude-api": {
                "pass_rate": 0.75,
                "avg_tokens": 12345,
                "avg_turns": 6.5,
                "avg_wall_clock": 15.3,
                "avg_process_score": 0.82,
            }
        },
        "by_difficulty": {
            "easy": {
                "by_agent": {
                    "claude-api": {"total": 2, "passed": 2, "pass_rate": 1.0}
                }
            }
        },
        "by_failure_class": {"context_miss": 1, "timeout_or_loop": 1},
        "all_runs": [
            {
                "task_id": "bug-fix-a",
                "difficulty": "easy",
                "agent_name": "claude-api",
                "primary_pass": True,
                "total_tokens": 10000,
                "total_turns": 5,
                "wall_clock_seconds": 12.1,
                "failure_class": None,
            },
            {
                "task_id": "bug-fix-b",
                "difficulty": "easy",
                "agent_name": "claude-api",
                "primary_pass": False,
                "total_tokens": 14690,
                "total_turns": 8,
                "wall_clock_seconds": 18.5,
                "failure_class": "context_miss",
            },
        ],
    }
    base.update(overrides)
    return base


def _make_comparison() -> dict[str, Any]:
    return {
        "agent_deltas": {
            "claude-api": {"a_rate": 0.72, "b_rate": 0.78, "delta": 0.06, "p_value": 0.03},
        },
        "flipped_pass_to_fail": [
            {"task_id": "task-a", "agent": "claude-api", "failure_class": "context_miss"},
            {"task_id": "task-b", "agent": "claude-api", "failure_class": "timeout_or_loop"},
        ],
        "flipped_fail_to_pass": [],
        "failure_shifts": {
            "context_miss": {"a_count": 15, "b_count": 10, "delta": -5},
        },
    }


# --- Suite report ---

def test_suite_report_sections() -> None:
    reporter = MarkdownReporter()
    md = reporter.generate_suite_report(_make_suite_summary())
    assert "## Summary" in md
    assert "## Failure Analysis" in md
    assert "## Per-Task Results" in md


def test_suite_report_valid_markdown_tables() -> None:
    reporter = MarkdownReporter()
    md = reporter.generate_suite_report(_make_suite_summary())
    # There should be pipe-delimited lines overall
    all_pipe_lines = [line for line in md.splitlines() if line.strip().startswith("|")]
    assert len(all_pipe_lines) > 0
    # Extract just the Summary table (lines between "## Summary" and next "##" heading)
    lines = md.splitlines()
    in_summary = False
    summary_table_lines: list[str] = []
    for line in lines:
        if line.startswith("## Summary"):
            in_summary = True
            continue
        if in_summary:
            if line.startswith("##"):
                break
            if line.strip().startswith("|"):
                summary_table_lines.append(line)
    assert len(summary_table_lines) > 1, "Summary table should have header + separator + data rows"
    # Within the summary table, all pipe-delimited lines should have consistent column count
    col_counts = [line.count("|") for line in summary_table_lines if not line.strip().startswith("|---")]
    assert len(set(col_counts)) == 1, f"Inconsistent column counts in Summary table: {col_counts}"


# --- Comparison report ---

def test_comparison_report_regressions() -> None:
    reporter = MarkdownReporter()
    comparison = _make_comparison()
    exp_a: dict[str, Any] = {"name": "exp-a", "created_at": "2026-03-01"}
    exp_b: dict[str, Any] = {"name": "exp-b", "created_at": "2026-03-15"}
    md = reporter.generate_comparison_report(comparison, exp_a, exp_b)
    # 2 regressions in flipped_pass_to_fail → 2 data rows in the table
    assert "task-a" in md
    assert "task-b" in md
    assert "Regressions" in md


# --- save ---

def test_save_writes_file(tmp_path: Path) -> None:
    reporter = MarkdownReporter()
    content = "# Test\n\nHello world."
    output_path = tmp_path / "reports" / "output.md"
    reporter.save(content, output_path)
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == content


# --- Edge cases ---

def test_empty_experiment_no_crash() -> None:
    reporter = MarkdownReporter()
    empty_summary: dict[str, Any] = {
        "name": "empty",
        "created_at": "2026-03-28",
        "suite_name": "empty-suite",
        "total_tasks": 0,
        "total_runs": 0,
        "total_failed": 0,
        "by_agent": {},
        "by_difficulty": {},
        "by_failure_class": {},
        "all_runs": [],
    }
    md = reporter.generate_suite_report(empty_summary)
    assert "## Summary" in md
    assert "## Failure Analysis" in md
    assert "## Per-Task Results" in md


# --- Custom filters ---

def test_custom_filters() -> None:
    reporter = MarkdownReporter()
    env = reporter.env
    assert env.filters["format_pct"](0.756) == "75.6%"
    assert env.filters["format_tokens"](12345) == "12,345"
