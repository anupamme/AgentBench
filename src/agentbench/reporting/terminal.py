"""Rich terminal output for AgentBench results.

Provides formatted, colorized display for:
- Individual run results (single-line pass/fail summary)
- Suite/experiment summaries (table with per-task breakdown)
- Agent comparison tables (side-by-side pass/fail across agents)
- Failure distribution charts (horizontal bar chart)
- Experiment comparison deltas (colored arrows for improvements/regressions)
- Task listings (filterable table of available tasks)
"""
from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class TerminalReporter:
    """Generates formatted terminal output for results."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def print_run_result(self, score: dict[str, Any]) -> None:
        """Print a single-line result for a completed task run.

        Format:
          ✓ python-bug-fix-calculator    │ 12,345 tokens │ 5 turns │ 8.2s │ process: 0.95
          ✗ py-debug-memory-leak         │ 89,000 tokens │ 22 turns │ 45s │ context_miss
        """
        passed = bool(score.get("primary_pass", False))
        task_id = str(score.get("task_id", "unknown"))
        total_tokens = int(score.get("total_tokens", 0))
        total_turns = int(score.get("total_turns", 0))
        wall_clock = float(score.get("wall_clock_seconds", 0.0))
        process_score = float(score.get("process_score", 0.0))
        failure_class = score.get("failure_class") or score.get("failure_category")

        icon = "✓" if passed else "✗"
        icon_style = "green" if passed else "red"

        secs = int(wall_clock)
        time_str = f"{secs}s" if secs < 60 else f"{secs // 60}m {secs % 60}s"

        token_str = f"{total_tokens:,} tokens"

        if passed:
            suffix_text = Text(f"process: {process_score:.2f}", style="cyan")
        else:
            suffix_text = Text(str(failure_class or "unknown"), style="red")

        line = Text()
        line.append(f"{icon} ", style=icon_style)
        line.append(f"{task_id:<35}", style="bold")
        line.append(" │ ")
        line.append(token_str)
        line.append(" │ ")
        line.append(f"{total_turns} turns")
        line.append(" │ ")
        line.append(time_str)
        line.append(" │ ")
        line.append_text(suffix_text)

        self.console.print(line)

    def print_suite_summary(self, runs: list[dict[str, Any]], title: str = "Suite Results") -> None:
        """Print a summary table for a batch of runs.

        Columns: Task ID | Difficulty | Result | Tokens | Turns | Time | Failure
        Footer row with aggregates.
        """
        table = Table(title=title, show_footer=True)
        table.add_column("Task ID", style="bold", footer="TOTAL")
        table.add_column("Difficulty", justify="center", footer="—")
        table.add_column("Result", justify="center", footer="")
        table.add_column("Tokens", justify="right", footer="")
        table.add_column("Turns", justify="right", footer="")
        table.add_column("Time", justify="right", footer="")
        table.add_column("Failure", footer="—")

        total = len(runs)
        pass_count = 0
        token_sum = 0
        turns_sum = 0
        time_sum = 0.0

        for run in runs:
            passed = bool(run.get("primary_pass", run.get("passed", False)))
            task_id = str(run.get("task_id", "unknown"))
            difficulty = str(run.get("difficulty", "—"))
            total_tokens = int(run.get("total_tokens", 0))
            total_turns = int(run.get("total_turns", 0))
            wall_clock = float(run.get("wall_clock_seconds", 0.0))
            failure_class = run.get("failure_class") or run.get("failure_category") or "—"

            if passed:
                pass_count += 1
            token_sum += total_tokens
            turns_sum += total_turns
            time_sum += wall_clock

            icon = "[green]✓[/green]" if passed else "[red]✗[/red]"
            row_style = "green" if passed else "red"
            secs = int(wall_clock)
            time_str = f"{secs}s" if secs < 60 else f"{secs // 60}m {secs % 60}s"

            table.add_row(
                task_id,
                difficulty,
                icon,
                f"{total_tokens:,}",
                str(total_turns),
                time_str,
                "—" if passed else str(failure_class),
                style=row_style,
            )

        # Footer aggregates
        if total > 0:
            pct = pass_count / total * 100
            avg_tokens = token_sum / total
            avg_turns = turns_sum / total
            avg_time = time_sum / total
            avg_secs = int(avg_time)
            m, s = divmod(avg_secs, 60)
            avg_time_str = f"{avg_secs}s" if avg_secs < 60 else f"{m}m {s}s"
            table.columns[2].footer = f"{pass_count}/{total} ({pct:.1f}%)"
            table.columns[3].footer = f"{avg_tokens:,.0f} avg"
            table.columns[4].footer = f"{avg_turns:.1f} avg"
            table.columns[5].footer = f"{avg_time_str} avg"

        self.console.print(table)

    def print_agent_comparison(self, experiment_summary: dict[str, Any]) -> None:
        """Print a side-by-side agent comparison table.

        One column per agent showing pass/fail for each task.
        Footer rows show pass rate and avg tokens per agent.
        """
        by_agent: dict[str, list[dict[str, Any]]] = experiment_summary.get("by_agent", {})
        agents = list(by_agent.keys())

        # Build task → agent → run lookup
        all_task_ids: list[str] = []
        seen: set[str] = set()
        task_agent_map: dict[str, dict[str, dict[str, Any]]] = {}
        for agent, agent_runs in by_agent.items():
            for run in agent_runs:
                tid = str(run.get("task_id", "unknown"))
                if tid not in seen:
                    all_task_ids.append(tid)
                    seen.add(tid)
                task_agent_map.setdefault(tid, {})[agent] = run

        table = Table(title="Agent Comparison")
        table.add_column("Task", style="bold")
        for agent in agents:
            table.add_column(agent, justify="center")

        for task_id in sorted(all_task_ids):
            row: list[str] = [task_id]
            for agent in agents:
                agent_run: dict[str, Any] | None = task_agent_map.get(task_id, {}).get(agent)
                if agent_run is None:
                    row.append("[dim]—[/dim]")
                else:
                    passed = bool(agent_run.get("primary_pass", agent_run.get("passed", False)))
                    tokens = int(agent_run.get("total_tokens", 0))
                    tokens_k = tokens // 1000
                    failure_class = (
                        agent_run.get("failure_class") or agent_run.get("failure_category", "")
                    )
                    # Abbreviate long failure classes
                    if failure_class and len(str(failure_class)) > 12:
                        failure_class = str(failure_class)[:10] + ".."
                    if passed:
                        row.append(f"[green]✓ ({tokens_k}k)[/green]")
                    else:
                        row.append(f"[red]✗ {failure_class}[/red]")
            table.add_row(*row)

        # Summary rows
        table.add_section()
        pass_rate_row: list[str] = ["[bold]PASS RATE[/bold]"]
        avg_tokens_row: list[str] = ["[bold]AVG TOKENS[/bold]"]
        for agent in agents:
            agent_runs = by_agent.get(agent, [])
            if agent_runs:
                n = len(agent_runs)
                rate = sum(1 for r in agent_runs if r.get("primary_pass", r.get("passed"))) / n
                avg_tok = sum(int(r.get("total_tokens", 0)) for r in agent_runs) / n
                pass_rate_row.append(f"{rate * 100:.1f}%")
                avg_tokens_row.append(f"{avg_tok:,.0f}")
            else:
                pass_rate_row.append("—")
                avg_tokens_row.append("—")
        table.add_row(*pass_rate_row)
        table.add_row(*avg_tokens_row)

        self.console.print(table)

    def print_failure_distribution(self, failure_counts: dict[str, int]) -> None:
        """Print failure class distribution as horizontal bar chart."""
        if not failure_counts:
            self.console.print("[dim]No failures recorded.[/dim]")
            return

        sorted_failures = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)
        total = sum(failure_counts.values())
        max_count = sorted_failures[0][1]
        max_bar_width = 20

        header = Text(f"Failure Distribution ({total} failed runs)")
        header.stylize("bold")
        self.console.print(header)
        self.console.print("─" * 45)

        for cls, count in sorted_failures:
            filled = int(count / max_count * max_bar_width) if max_count > 0 else 0
            bar = "█" * filled + "░" * (max_bar_width - filled)
            pct = count / total * 100 if total > 0 else 0.0
            line = f"{cls:<20} {bar} {count:>3} ({pct:.1f}%)"
            self.console.print(line)

    def print_experiment_comparison(self, comparison: dict[str, Any]) -> None:
        """Print experiment comparison results showing deltas."""
        agent_deltas: dict[str, dict[str, Any]] = comparison.get("agent_deltas", {})
        flipped_pass_to_fail: list[dict[str, Any]] = comparison.get("flipped_pass_to_fail", [])
        flipped_fail_to_pass: list[dict[str, Any]] = comparison.get("flipped_fail_to_pass", [])
        failure_shifts: dict[str, dict[str, Any]] = comparison.get("failure_shifts", {})

        # Section 1: Pass Rate Changes
        self.console.print(Panel("[bold]Pass Rate Changes[/bold]"))
        for agent, delta in agent_deltas.items():
            a_rate = float(delta.get("a_rate", 0.0))
            b_rate = float(delta.get("b_rate", 0.0))
            d = float(delta.get("delta", b_rate - a_rate))
            p_val = float(delta.get("p_value", 1.0))
            sig_marker = "*" if p_val < 0.05 else ""
            if d > 0:
                arrow = Text("↑", style="green")
                delta_str = Text(f" +{d * 100:.1f}% (p={p_val:.2f}{sig_marker})", style="green")
            elif d < 0:
                arrow = Text("↓", style="red")
                delta_str = Text(f" {d * 100:.1f}% (p={p_val:.2f}{sig_marker})", style="red")
            else:
                arrow = Text("→")
                delta_str = Text(f" +0.0% (p={p_val:.2f}{sig_marker})")
            line = Text(f"  {agent:<20} {a_rate * 100:.1f}% → {b_rate * 100:.1f}%  ")
            line.append_text(arrow)
            line.append_text(delta_str)
            self.console.print(line)

        # Section 2: Tasks Flipped
        self.console.print()
        self.console.print("[bold]Tasks Flipped[/bold]")
        if flipped_pass_to_fail:
            names = ", ".join(f["task_id"] for f in flipped_pass_to_fail)
            self.console.print(f"  [red]✓→✗ (regressions):[/red] {names}")
        else:
            self.console.print("  [dim]No regressions.[/dim]")
        if flipped_fail_to_pass:
            names = ", ".join(f["task_id"] for f in flipped_fail_to_pass)
            self.console.print(f"  [green]✗→✓ (improvements):[/green] {names}")
        else:
            self.console.print("  [dim]No improvements.[/dim]")

        # Section 3: Failure Shifts
        if failure_shifts:
            self.console.print()
            self.console.print("[bold]Failure Shifts[/bold]")
            for cls, shift in failure_shifts.items():
                a_count = int(shift.get("a_count", 0))
                b_count = int(shift.get("b_count", 0))
                delta_val = int(shift.get("delta", b_count - a_count))
                delta_style = "green" if delta_val < 0 else ("red" if delta_val > 0 else "")
                sign = "+" if delta_val > 0 else ""
                delta_display = Text(f"({sign}{delta_val})", style=delta_style)
                line = Text(f"  {cls:<25} {a_count} → {b_count}  ")
                line.append_text(delta_display)
                self.console.print(line)

    def print_task_list(
        self, tasks: list[dict[str, Any]], stats: dict[str, dict[str, Any]] | None = None
    ) -> None:
        """Print a table of available tasks.

        Columns: ID | Difficulty | Type | Languages | Tags
        If stats dict is provided: add Pass Rate | Avg Tokens columns.
        """
        difficulty_styles = {
            "easy": "green",
            "medium": "yellow",
            "hard": "red",
            "expert": "bright_red",
        }

        table = Table(title="Available Tasks")
        table.add_column("ID", style="bold")
        table.add_column("Difficulty", justify="center")
        table.add_column("Type")
        table.add_column("Languages")
        table.add_column("Tags")
        if stats is not None:
            table.add_column("Pass Rate", justify="right")
            table.add_column("Avg Tokens", justify="right")

        for task in tasks:
            task_id = str(task.get("id", task.get("task_id", "unknown")))
            difficulty = str(task.get("difficulty", "—"))
            task_type = str(task.get("task_type", task.get("type", "—")))
            languages = ", ".join(task.get("languages", []))
            tags = ", ".join(task.get("tags", []))

            diff_style = difficulty_styles.get(difficulty.lower(), "")
            if diff_style:
                diff_display = f"[{diff_style}]{difficulty}[/{diff_style}]"
            else:
                diff_display = difficulty

            row: list[str] = [task_id, diff_display, task_type, languages, tags]

            if stats is not None:
                task_stats = stats.get(task_id, {})
                pass_rate = task_stats.get("pass_rate")
                avg_tokens = task_stats.get("avg_tokens")
                row.append(f"{pass_rate * 100:.1f}%" if pass_rate is not None else "—")
                row.append(f"{avg_tokens:,.0f}" if avg_tokens is not None else "—")

            table.add_row(*row)

        self.console.print(table)
