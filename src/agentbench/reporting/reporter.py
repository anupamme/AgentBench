"""
Report Generator — produces formatted reports from evaluation results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Template
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from agentbench.reporting.data import ExperimentData

_MARKDOWN_TEMPLATE = """\
# Evaluation Report

## Summary

| Agent | Tasks | Pass Rate | Avg Tokens | Avg Turns | Avg Time (s) |
|-------|-------|-----------|------------|-----------|--------------|
{% for agent_name, runs in data.by_agent().items() -%}
{%- set pass_rate = (runs | selectattr('passed') | list | length) / runs | length -%}
{%- set avg_tokens = (runs | map(attribute='total_tokens') | sum) / runs | length -%}
{%- set avg_turns = (runs | map(attribute='total_turns') | sum) / runs | length -%}
{%- set avg_time = (runs | map(attribute='wall_clock_seconds') | sum) / runs | length -%}
| {{ agent_name }} | {{ runs | length }} | {{ "%.1f%%" | format(pass_rate * 100) }} | {{ "%.0f" | format(avg_tokens) }} | {{ "%.1f" | format(avg_turns) }} | {{ "%.1f" | format(avg_time) }} |
{% endfor %}

## Failure Analysis

| Agent | Failure Category | Count |
|-------|-----------------|-------|
{% for agent_name in data.by_agent().keys() -%}
{%- for category, count in data.failure_distribution(agent_name).items() -%}
| {{ agent_name }} | {{ category }} | {{ count }} |
{% endfor -%}
{% endfor %}

## Efficiency Comparison

| Agent | Avg Tokens | Avg Turns | Avg Time (s) |
|-------|------------|-----------|--------------|
{% for agent_name, runs in data.by_agent().items() -%}
{%- set avg_tokens = (runs | map(attribute='total_tokens') | sum) / runs | length -%}
{%- set avg_turns = (runs | map(attribute='total_turns') | sum) / runs | length -%}
{%- set avg_time = (runs | map(attribute='wall_clock_seconds') | sum) / runs | length -%}
| {{ agent_name }} | {{ "%.0f" | format(avg_tokens) }} | {{ "%.1f" | format(avg_turns) }} | {{ "%.1f" | format(avg_time) }} |
{% endfor %}

## Per-Task Results

| Task | Agent | Pass | Tokens | Turns | Failure |
|------|-------|------|--------|-------|---------|
{% for run in data.runs | sort(attribute='task_id') -%}
| {{ run.task_id }} | {{ run.agent_name }} | {{ "✓" if run.passed else "✗" }} | {{ run.total_tokens }} | {{ run.total_turns }} | {{ run.failure_category or "-" }} |
{% endfor %}
"""


class Reporter:
    """Generates reports in various formats."""

    def __init__(self, console: Console | None = None):
        self._console = console or Console()

    def summary_table(self, data: ExperimentData) -> None:
        """
        Print a Rich table to the terminal with per-agent summary.

        Columns:
        | Agent | Pass Rate | Avg Tokens | Avg Turns | Avg Time | Top Failure |
        """
        table = Table(title="Evaluation Results")
        table.add_column("Agent", style="bold")
        table.add_column("Pass Rate", justify="right")
        table.add_column("Avg Tokens", justify="right")
        table.add_column("Avg Turns", justify="right")
        table.add_column("Avg Time (s)", justify="right")
        table.add_column("Top Failure", style="red")

        for agent_name, runs in data.by_agent().items():
            pass_rate = sum(1 for r in runs if r.passed) / len(runs)
            avg_tokens = sum(r.total_tokens for r in runs) / len(runs)
            avg_turns = sum(r.total_turns for r in runs) / len(runs)
            avg_time = sum(r.wall_clock_seconds for r in runs) / len(runs)

            failures = [r.failure_category for r in runs if r.failure_category]
            top_failure = max(set(failures), key=failures.count) if failures else "-"

            table.add_row(
                agent_name,
                f"{pass_rate:.1%}",
                f"{avg_tokens:.0f}",
                f"{avg_turns:.1f}",
                f"{avg_time:.1f}",
                top_failure,
            )

        self._console.print(table)

    def detail_table(self, data: ExperimentData) -> None:
        """
        Print a per-task detail table.

        Columns:
        | Task | Agent | Pass | Tokens | Turns | Failure |
        """
        table = Table(title="Per-Task Results")
        table.add_column("Task")
        table.add_column("Agent")
        table.add_column("Pass", justify="center")
        table.add_column("Tokens", justify="right")
        table.add_column("Turns", justify="right")
        table.add_column("Failure")

        for run in sorted(data.runs, key=lambda r: (r.task_id, r.agent_name)):
            status = "✓" if run.passed else "✗"
            style = "green" if run.passed else "red"
            table.add_row(
                run.task_id,
                run.agent_name,
                f"[{style}]{status}[/{style}]",
                str(run.total_tokens),
                str(run.total_turns),
                run.failure_category or "-",
            )

        self._console.print(table)

    def markdown_report(self, data: ExperimentData) -> str:
        """
        Generate a full markdown report using a Jinja2 template.

        Sections:
        1. Summary — overall pass rates per agent
        2. Failure Analysis — failure category distribution per agent
        3. Efficiency Comparison — token/turn/time comparison
        4. Per-Task Results — full table
        """
        return str(Template(_MARKDOWN_TEMPLATE).render(data=data))

    def failure_report(self, data: ExperimentData) -> None:
        """
        Print a failure analysis table.

        | Failure Category | Count | % of Failures | Example Tasks |
        """
        table = Table(title="Failure Analysis")
        table.add_column("Failure Category", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("% of Failures", justify="right")
        table.add_column("Example Tasks")

        # Build category → example task IDs mapping
        category_tasks: dict[str, list[str]] = {}
        for run in data.runs:
            if run.failure_category:
                category_tasks.setdefault(run.failure_category, []).append(run.task_id)

        dist = data.failure_distribution()
        total_failures = sum(dist.values())

        for category, count in sorted(dist.items(), key=lambda x: x[1], reverse=True):
            pct = f"{count / total_failures:.1%}" if total_failures > 0 else "0.0%"
            examples = list(dict.fromkeys(category_tasks.get(category, [])))[:3]
            example_str = ", ".join(examples)
            table.add_row(category, str(count), pct, example_str)

        self._console.print(table)
