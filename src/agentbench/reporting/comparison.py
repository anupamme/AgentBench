"""
Comparison Engine — compares two result sets with statistical significance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from agentbench.reporting.data import ExperimentData, RunData


@dataclass
class ComparisonResult:
    baseline_agent: str
    candidate_agent: str
    baseline_pass_rate: float
    candidate_pass_rate: float
    pass_rate_delta: float
    p_value: float                      # from McNemar's test
    is_significant: bool                # p_value < 0.05
    unique_baseline_solves: list[str]   # tasks only baseline solved
    unique_candidate_solves: list[str]  # tasks only candidate solved
    token_efficiency_ratio: float       # candidate_avg_tokens / baseline_avg_tokens


def _mcnemar_p_value(b: int, c: int) -> float:
    """Compute p-value from McNemar's test with continuity correction."""
    if b + c == 0:
        return 1.0
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    try:
        from scipy.stats import chi2 as chi2_dist  # type: ignore[import-untyped]
        return float(chi2_dist.sf(chi2, 1))
    except ImportError:
        # Simple approximation: p ≈ exp(-chi2/2) for 1 degree of freedom
        return math.exp(-0.5 * chi2)


class ComparisonEngine:
    """Compares two result sets with statistical testing."""

    def compare(
        self, baseline: ExperimentData, candidate: ExperimentData
    ) -> ComparisonResult:
        """
        Compare baseline and candidate results.

        1. Determine agent names (first agent found in each dataset)
        2. Match tasks present in both datasets
        3. Build paired pass/fail vectors
        4. Run McNemar's test
        5. Identify unique solves and efficiency ratios
        """
        baseline_agents = list(baseline.by_agent().keys())
        candidate_agents = list(candidate.by_agent().keys())

        baseline_agent = baseline_agents[0] if baseline_agents else "baseline"
        candidate_agent = candidate_agents[0] if candidate_agents else "candidate"

        # Build task→RunData maps (take the first run per task per agent)
        def best_run_by_task(runs: list[RunData]) -> dict[str, RunData]:
            result: dict[str, RunData] = {}
            for run in runs:
                if run.task_id not in result:
                    result[run.task_id] = run
            return result

        baseline_by_task = best_run_by_task(baseline.by_agent().get(baseline_agent, []))
        candidate_by_task = best_run_by_task(candidate.by_agent().get(candidate_agent, []))

        # Only compare tasks present in both
        common_tasks = sorted(set(baseline_by_task) & set(candidate_by_task))

        b_pass = [baseline_by_task[t].passed for t in common_tasks]
        c_pass = [candidate_by_task[t].passed for t in common_tasks]

        baseline_pass_rate = sum(b_pass) / len(b_pass) if b_pass else 0.0
        candidate_pass_rate = sum(c_pass) / len(c_pass) if c_pass else 0.0
        pass_rate_delta = candidate_pass_rate - baseline_pass_rate

        # McNemar contingency: b = baseline-only solves, c = candidate-only solves
        b_only = sum(1 for bp, cp in zip(b_pass, c_pass) if bp and not cp)
        c_only = sum(1 for bp, cp in zip(b_pass, c_pass) if not bp and cp)

        p_value = _mcnemar_p_value(b_only, c_only)
        is_significant = p_value < 0.05

        unique_baseline_solves = [
            t for t, bp, cp in zip(common_tasks, b_pass, c_pass) if bp and not cp
        ]
        unique_candidate_solves = [
            t for t, bp, cp in zip(common_tasks, b_pass, c_pass) if not bp and cp
        ]

        # Token efficiency ratio
        baseline_tokens = [baseline_by_task[t].total_tokens for t in common_tasks]
        candidate_tokens = [candidate_by_task[t].total_tokens for t in common_tasks]
        baseline_avg_tokens = sum(baseline_tokens) / len(baseline_tokens) if baseline_tokens else 0
        candidate_avg_tokens = sum(candidate_tokens) / len(candidate_tokens) if candidate_tokens else 0
        token_efficiency_ratio = (
            candidate_avg_tokens / baseline_avg_tokens if baseline_avg_tokens > 0 else 1.0
        )

        return ComparisonResult(
            baseline_agent=baseline_agent,
            candidate_agent=candidate_agent,
            baseline_pass_rate=baseline_pass_rate,
            candidate_pass_rate=candidate_pass_rate,
            pass_rate_delta=pass_rate_delta,
            p_value=p_value,
            is_significant=is_significant,
            unique_baseline_solves=unique_baseline_solves,
            unique_candidate_solves=unique_candidate_solves,
            token_efficiency_ratio=token_efficiency_ratio,
        )

    def print_comparison(self, result: ComparisonResult, console=None) -> None:  # type: ignore[no-untyped-def]
        """Print a formatted comparison report."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        con: Console = console or Console()

        sig_marker = " *" if result.is_significant else ""
        delta_sign = "+" if result.pass_rate_delta >= 0 else ""
        delta_style = "green" if result.pass_rate_delta > 0 else ("red" if result.pass_rate_delta < 0 else "")

        # Summary table
        table = Table(title="Pass Rate Comparison")
        table.add_column("Agent", style="bold")
        table.add_column("Pass Rate", justify="right")

        table.add_row(result.baseline_agent, f"{result.baseline_pass_rate:.1%}")
        delta_str = f"[{delta_style}]{delta_sign}{result.pass_rate_delta:.1%}[/{delta_style}]{sig_marker}" if delta_style else f"{delta_sign}{result.pass_rate_delta:.1%}{sig_marker}"
        table.add_row(result.candidate_agent, f"{result.candidate_pass_rate:.1%}  Δ {delta_str}")
        con.print(table)

        # Significance
        sig_text = "significant (p < 0.05)" if result.is_significant else "not significant"
        con.print(f"  McNemar's test: p = {result.p_value:.4f} — [bold]{sig_text}[/bold]")

        # Unique solves
        if result.unique_baseline_solves:
            con.print(f"\n  [cyan]Only {result.baseline_agent} solved:[/cyan] {', '.join(result.unique_baseline_solves)}")
        if result.unique_candidate_solves:
            con.print(f"  [cyan]Only {result.candidate_agent} solved:[/cyan] {', '.join(result.unique_candidate_solves)}")

        # Efficiency
        ratio = result.token_efficiency_ratio
        ratio_style = "green" if ratio < 1.0 else ("red" if ratio > 1.0 else "")
        ratio_str = f"[{ratio_style}]{ratio:.2f}x[/{ratio_style}]" if ratio_style else f"{ratio:.2f}x"
        con.print(f"\n  Token efficiency ratio (candidate/baseline): {ratio_str}")

        # Recommendation
        con.print()
        if result.is_significant and result.pass_rate_delta > 0:
            con.print(Panel(f"[green]Recommendation: {result.candidate_agent} is significantly better.[/green]"))
        elif result.is_significant and result.pass_rate_delta < 0:
            con.print(Panel(f"[red]Recommendation: {result.baseline_agent} is significantly better.[/red]"))
        else:
            con.print(Panel("[yellow]Recommendation: No statistically significant difference detected.[/yellow]"))
