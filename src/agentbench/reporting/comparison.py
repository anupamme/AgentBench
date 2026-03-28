"""
Comparison Engine — compares two result sets with statistical significance.

Provides:
- SimpleComparisonResult / ComparisonEngine: pairwise agent comparison (existing)
- AgentDelta, TaskFlip, ComparisonResult, ExperimentComparator: multi-agent
  experiment comparison with McNemar's test and bootstrap CIs (new)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentbench.reporting.data import ExperimentData, RunData


# ---------------------------------------------------------------------------
# Legacy pairwise comparison (preserved; renamed to SimpleComparisonResult)
# ---------------------------------------------------------------------------

@dataclass
class SimpleComparisonResult:
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
    ) -> SimpleComparisonResult:
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
        b_only = sum(1 for bp, cp in zip(b_pass, c_pass, strict=False) if bp and not cp)
        c_only = sum(1 for bp, cp in zip(b_pass, c_pass, strict=False) if not bp and cp)

        p_value = _mcnemar_p_value(b_only, c_only)
        is_significant = p_value < 0.05

        unique_baseline_solves = [
            t for t, bp, cp in zip(common_tasks, b_pass, c_pass, strict=False) if bp and not cp
        ]
        unique_candidate_solves = [
            t for t, bp, cp in zip(common_tasks, b_pass, c_pass, strict=False) if not bp and cp
        ]

        # Token efficiency ratio
        baseline_tokens = [baseline_by_task[t].total_tokens for t in common_tasks]
        candidate_tokens = [candidate_by_task[t].total_tokens for t in common_tasks]
        baseline_avg_tokens = sum(baseline_tokens) / len(baseline_tokens) if baseline_tokens else 0
        candidate_avg_tokens = (
            sum(candidate_tokens) / len(candidate_tokens) if candidate_tokens else 0
        )
        token_efficiency_ratio = (
            candidate_avg_tokens / baseline_avg_tokens if baseline_avg_tokens > 0 else 1.0
        )

        return SimpleComparisonResult(
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

    def print_comparison(self, result: SimpleComparisonResult, console=None) -> None:  # type: ignore[no-untyped-def]
        """Print a formatted comparison report."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        con: Console = console or Console()

        sig_marker = " *" if result.is_significant else ""
        delta_sign = "+" if result.pass_rate_delta >= 0 else ""
        if result.pass_rate_delta > 0:
            delta_style = "green"
        elif result.pass_rate_delta < 0:
            delta_style = "red"
        else:
            delta_style = ""

        # Summary table
        table = Table(title="Pass Rate Comparison")
        table.add_column("Agent", style="bold")
        table.add_column("Pass Rate", justify="right")

        table.add_row(result.baseline_agent, f"{result.baseline_pass_rate:.1%}")
        if delta_style:
            delta_str = (
                f"[{delta_style}]{delta_sign}{result.pass_rate_delta:.1%}"
                f"[/{delta_style}]{sig_marker}"
            )
        else:
            delta_str = f"{delta_sign}{result.pass_rate_delta:.1%}{sig_marker}"
        table.add_row(result.candidate_agent, f"{result.candidate_pass_rate:.1%}  Δ {delta_str}")
        con.print(table)

        # Significance
        sig_text = "significant (p < 0.05)" if result.is_significant else "not significant"
        con.print(f"  McNemar's test: p = {result.p_value:.4f} — [bold]{sig_text}[/bold]")

        # Unique solves
        if result.unique_baseline_solves:
            solves = ", ".join(result.unique_baseline_solves)
            con.print(f"\n  [cyan]Only {result.baseline_agent} solved:[/cyan] {solves}")
        if result.unique_candidate_solves:
            solves = ", ".join(result.unique_candidate_solves)
            con.print(f"  [cyan]Only {result.candidate_agent} solved:[/cyan] {solves}")

        # Efficiency
        ratio = result.token_efficiency_ratio
        ratio_style = "green" if ratio < 1.0 else ("red" if ratio > 1.0 else "")
        ratio_str = f"[{ratio_style}]{ratio:.2f}x[/{ratio_style}]" if ratio_style else f"{ratio:.2f}x"  # noqa: E501
        con.print(f"\n  Token efficiency ratio (candidate/baseline): {ratio_str}")

        # Recommendation
        con.print()
        if result.is_significant and result.pass_rate_delta > 0:
            con.print(Panel(
                f"[green]Recommendation: {result.candidate_agent} is significantly better.[/green]"
            ))
        elif result.is_significant and result.pass_rate_delta < 0:
            con.print(Panel(
                f"[red]Recommendation: {result.baseline_agent} is significantly better.[/red]"
            ))
        else:
            con.print(Panel(
                "[yellow]Recommendation: No statistically significant difference detected.[/yellow]"
            ))


# ---------------------------------------------------------------------------
# New multi-agent experiment comparator
# ---------------------------------------------------------------------------

@dataclass
class AgentDelta:
    """Pass rate delta for one agent across two experiments."""
    agent_name: str
    a_pass_rate: float
    b_pass_rate: float
    delta: float           # b_pass_rate - a_pass_rate (positive = improvement)
    a_pass_b_fail: int     # Regressions
    a_fail_b_pass: int     # Improvements
    p_value: float
    significant: bool      # p_value < 0.05


@dataclass
class TaskFlip:
    """A task that changed outcome between experiments."""
    task_id: str
    agent_name: str
    direction: str         # "pass_to_fail" or "fail_to_pass"
    failure_class: str     # failure_class in the failing experiment


@dataclass
class ComparisonResult:
    """Complete result of comparing two experiments."""
    exp_a_id: str
    exp_b_id: str
    exp_a_name: str
    exp_b_name: str

    agent_deltas: list[AgentDelta]
    flipped_pass_to_fail: list[TaskFlip]    # Regressions
    flipped_fail_to_pass: list[TaskFlip]    # Improvements
    failure_shifts: dict[str, dict[str, Any]]
    # {"context_miss": {"a_count": 15, "b_count": 10, "delta": -5}, ...}
    unique_a: list[str]    # Task IDs only solved in exp_a
    unique_b: list[str]    # Task IDs only solved in exp_b

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "exp_a_id": self.exp_a_id,
            "exp_b_id": self.exp_b_id,
            "exp_a_name": self.exp_a_name,
            "exp_b_name": self.exp_b_name,
            "agent_deltas": [
                {
                    "agent_name": d.agent_name,
                    "a_pass_rate": d.a_pass_rate,
                    "b_pass_rate": d.b_pass_rate,
                    "delta": d.delta,
                    "a_pass_b_fail": d.a_pass_b_fail,
                    "a_fail_b_pass": d.a_fail_b_pass,
                    "p_value": d.p_value,
                    "significant": d.significant,
                }
                for d in self.agent_deltas
            ],
            "flipped_pass_to_fail": [
                {
                    "task_id": f.task_id,
                    "agent_name": f.agent_name,
                    "direction": f.direction,
                    "failure_class": f.failure_class,
                }
                for f in self.flipped_pass_to_fail
            ],
            "flipped_fail_to_pass": [
                {
                    "task_id": f.task_id,
                    "agent_name": f.agent_name,
                    "direction": f.direction,
                    "failure_class": f.failure_class,
                }
                for f in self.flipped_fail_to_pass
            ],
            "failure_shifts": self.failure_shifts,
            "unique_a": self.unique_a,
            "unique_b": self.unique_b,
        }


class ExperimentComparator:
    """Compares two experiment runs with statistical testing."""

    def compare(self, exp_a_id: str, exp_b_id: str, store: Any) -> ComparisonResult:
        """Perform full comparison between two experiments.

        store must implement: query_runs(experiment_id, limit) -> list[RunData-like]
        """
        a_runs: list[Any] = store.query_runs(experiment_id=exp_a_id, limit=10000)
        b_runs: list[Any] = store.query_runs(experiment_id=exp_b_id, limit=10000)

        # Group by (task_id, agent_name) -> list of runs
        def group_runs(runs: list[Any]) -> dict[tuple[str, str], list[Any]]:
            groups: dict[tuple[str, str], list[Any]] = {}
            for run in runs:
                key = (run.task_id, run.agent_name)
                groups.setdefault(key, []).append(run)
            return groups

        a_groups = group_runs(a_runs)
        b_groups = group_runs(b_runs)

        # Majority vote: a task config is "passed" if >50% of runs pass
        def majority_pass(runs: list[Any]) -> bool:
            if not runs:
                return False
            passes = sum(1 for r in runs if r.passed)
            return passes > len(runs) / 2

        def failure_class_for(runs: list[Any]) -> str:
            for run in runs:
                fc = getattr(run, "failure_category", None) or getattr(run, "failure_class", None)
                if fc:
                    return str(fc)
            return "unknown"

        # Collect all agents
        all_agents = sorted(
            {key[1] for key in a_groups} | {key[1] for key in b_groups}
        )

        agent_deltas: list[AgentDelta] = []
        flipped_pass_to_fail: list[TaskFlip] = []
        flipped_fail_to_pass: list[TaskFlip] = []

        for agent in all_agents:
            # Tasks present in both experiments for this agent
            a_tasks = {t for (t, a) in a_groups if a == agent}
            b_tasks = {t for (t, a) in b_groups if a == agent}
            common = sorted(a_tasks & b_tasks)

            a_pass_map = {t: majority_pass(a_groups[(t, agent)]) for t in a_tasks}
            b_pass_map = {t: majority_pass(b_groups[(t, agent)]) for t in b_tasks}

            if not common and not a_tasks and not b_tasks:
                continue

            a_total = len(a_tasks)
            b_total = len(b_tasks)
            a_pass_count = sum(1 for t in a_tasks if a_pass_map[t])
            b_pass_count = sum(1 for t in b_tasks if b_pass_map[t])

            a_pass_rate = a_pass_count / a_total if a_total else 0.0
            b_pass_rate = b_pass_count / b_total if b_total else 0.0
            delta = b_pass_rate - a_pass_rate

            # Paired disagreements on common tasks
            a_pass_b_fail = sum(
                1 for t in common if a_pass_map[t] and not b_pass_map[t]
            )
            a_fail_b_pass = sum(
                1 for t in common if not a_pass_map[t] and b_pass_map[t]
            )
            p_value = ExperimentComparator.mcnemar_test(a_pass_b_fail, a_fail_b_pass)

            agent_deltas.append(AgentDelta(
                agent_name=agent,
                a_pass_rate=a_pass_rate,
                b_pass_rate=b_pass_rate,
                delta=delta,
                a_pass_b_fail=a_pass_b_fail,
                a_fail_b_pass=a_fail_b_pass,
                p_value=p_value,
                significant=p_value < 0.05,
            ))

            # Task flips
            for task in common:
                a_passed = a_pass_map[task]
                b_passed = b_pass_map[task]
                if a_passed and not b_passed:
                    fc = failure_class_for(b_groups[(task, agent)])
                    flipped_pass_to_fail.append(TaskFlip(
                        task_id=task,
                        agent_name=agent,
                        direction="pass_to_fail",
                        failure_class=fc,
                    ))
                elif not a_passed and b_passed:
                    fc = failure_class_for(a_groups[(task, agent)])
                    flipped_fail_to_pass.append(TaskFlip(
                        task_id=task,
                        agent_name=agent,
                        direction="fail_to_pass",
                        failure_class=fc,
                    ))

        # Failure class distribution shifts
        def count_failures(runs: list[Any]) -> dict[str, int]:
            counts: dict[str, int] = {}
            for run in runs:
                if not run.passed:
                    fc = (
                        getattr(run, "failure_category", None)
                        or getattr(run, "failure_class", None)
                    )
                    if fc:
                        counts[str(fc)] = counts.get(str(fc), 0) + 1
            return counts

        a_failures = count_failures(a_runs)
        b_failures = count_failures(b_runs)
        all_failure_classes = sorted(set(a_failures) | set(b_failures))
        failure_shifts: dict[str, dict[str, Any]] = {}
        for fc in all_failure_classes:
            a_count = a_failures.get(fc, 0)
            b_count = b_failures.get(fc, 0)
            failure_shifts[fc] = {
                "a_count": a_count,
                "b_count": b_count,
                "delta": b_count - a_count,
            }

        # Unique solves: tasks solved by any agent in one exp but not the other
        a_solved = {t for (t, _), runs in a_groups.items() if majority_pass(runs)}
        b_solved = {t for (t, _), runs in b_groups.items() if majority_pass(runs)}
        unique_a = sorted(a_solved - b_solved)
        unique_b = sorted(b_solved - a_solved)

        return ComparisonResult(
            exp_a_id=exp_a_id,
            exp_b_id=exp_b_id,
            exp_a_name=exp_a_id,
            exp_b_name=exp_b_id,
            agent_deltas=agent_deltas,
            flipped_pass_to_fail=flipped_pass_to_fail,
            flipped_fail_to_pass=flipped_fail_to_pass,
            failure_shifts=failure_shifts,
            unique_a=unique_a,
            unique_b=unique_b,
        )

    @staticmethod
    def mcnemar_test(a_pass_b_fail: int, a_fail_b_pass: int) -> float:
        """McNemar's test for paired nominal data.

        Returns two-sided p-value.
        Uses exact binomial for n < 25, chi-squared approximation for n >= 25.
        """
        n = a_pass_b_fail + a_fail_b_pass
        if n == 0:
            return 1.0

        b = a_pass_b_fail

        if n < 25:
            # Exact binomial: X ~ Binomial(n, 0.5), two-sided
            half = 0.5 ** n
            # P(X <= b)
            p_le = sum(math.comb(n, k) * half for k in range(b + 1))
            # P(X >= b)
            p_ge = sum(math.comb(n, k) * half for k in range(b, n + 1))
            p_value = 2.0 * min(p_le, p_ge)
        else:
            # Chi-squared approximation with continuity correction
            chi2_stat = (abs(a_pass_b_fail - a_fail_b_pass) - 1) ** 2 / n
            p_value = math.erfc(math.sqrt(chi2_stat / 2))

        return max(0.0, min(1.0, p_value))

    @staticmethod
    def bootstrap_confidence_interval(
        values: list[float],
        confidence: float = 0.95,
        n_bootstrap: int = 10000,
        seed: int = 42,
    ) -> tuple[float, float, float]:
        """Bootstrap confidence interval for a mean.

        Returns (point_estimate, lower_bound, upper_bound).
        """
        if not values:
            return (0.0, 0.0, 0.0)

        random.seed(seed)
        point_estimate = sum(values) / len(values)

        bootstrap_means = []
        for _ in range(n_bootstrap):
            resample = random.choices(values, k=len(values))
            bootstrap_means.append(sum(resample) / len(resample))

        bootstrap_means.sort()
        alpha = 1.0 - confidence
        lower_idx = int(alpha / 2 * n_bootstrap)
        upper_idx = int((1.0 - alpha / 2) * n_bootstrap)
        # Clamp indices to valid range
        lower_idx = max(0, min(lower_idx, len(bootstrap_means) - 1))
        upper_idx = max(0, min(upper_idx, len(bootstrap_means) - 1))

        return (point_estimate, bootstrap_means[lower_idx], bootstrap_means[upper_idx])
