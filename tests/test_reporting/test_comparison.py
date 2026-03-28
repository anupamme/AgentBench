"""Tests for ExperimentComparator, mcnemar_test, and bootstrap_confidence_interval."""
from __future__ import annotations

import pytest

from agentbench.reporting.comparison import (
    AgentDelta,
    ComparisonResult,
    ExperimentComparator,
    TaskFlip,
)
from agentbench.reporting.data import RunData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run(
    task_id: str,
    agent_name: str,
    passed: bool,
    failure_category: str | None = None,
    run_id: str = "r1",
) -> RunData:
    return RunData(
        task_id=task_id,
        agent_name=agent_name,
        run_id=run_id,
        passed=passed,
        score=None,
        result=None,
        failure_category=failure_category,
    )


class MockStore:
    def __init__(self) -> None:
        self._runs: dict[str, list[RunData]] = {}

    def add(self, exp_id: str, run: RunData) -> None:
        self._runs.setdefault(exp_id, []).append(run)

    def query_runs(self, experiment_id: str, limit: int = 10000) -> list[RunData]:
        return self._runs.get(experiment_id, [])[:limit]


# ---------------------------------------------------------------------------
# mcnemar_test
# ---------------------------------------------------------------------------

def test_mcnemar_no_discordance() -> None:
    p = ExperimentComparator.mcnemar_test(0, 0)
    assert p == pytest.approx(1.0)


def test_mcnemar_symmetric() -> None:
    p = ExperimentComparator.mcnemar_test(10, 10)
    assert p > 0.5


def test_mcnemar_asymmetric_significant() -> None:
    p = ExperimentComparator.mcnemar_test(20, 5)
    assert p < 0.05


def test_mcnemar_small_sample_exact() -> None:
    # n=3 < 25 → exact binomial path
    p = ExperimentComparator.mcnemar_test(3, 0)
    assert 0.0 <= p <= 1.0


def test_mcnemar_continuity_correction() -> None:
    # n = 15+2 = 17... use n >= 25: 15 vs 2 → n=17, still < 25. Use 20 vs 2 → n=22 < 25.
    # Use 15 vs 10 → n=25, chi-squared path
    p = ExperimentComparator.mcnemar_test(15, 10)
    assert 0.0 <= p <= 1.0
    # 15 vs 2 → n=17 exact. For chi2 path, use 14 vs 11 → n=25
    p2 = ExperimentComparator.mcnemar_test(14, 11)
    assert 0.0 <= p2 <= 1.0


# ---------------------------------------------------------------------------
# bootstrap_confidence_interval
# ---------------------------------------------------------------------------

def test_bootstrap_ci_contains_true_mean() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    estimate, lower, upper = ExperimentComparator.bootstrap_confidence_interval(values)
    assert estimate == pytest.approx(3.0)
    assert lower <= 3.0 <= upper


def test_bootstrap_ci_reproducible() -> None:
    values = [0.1, 0.5, 0.9, 0.3, 0.7]
    r1 = ExperimentComparator.bootstrap_confidence_interval(values, seed=42)
    r2 = ExperimentComparator.bootstrap_confidence_interval(values, seed=42)
    assert r1 == r2


def test_bootstrap_ci_empty() -> None:
    result = ExperimentComparator.bootstrap_confidence_interval([])
    assert result == (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# ExperimentComparator.compare
# ---------------------------------------------------------------------------

def test_compare_identifies_regressions() -> None:
    store = MockStore()
    store.add("exp-a", _make_run("task-1", "agent-x", passed=True))
    store.add("exp-b", _make_run("task-1", "agent-x", passed=False, failure_category="context_miss"))

    comparator = ExperimentComparator()
    result = comparator.compare("exp-a", "exp-b", store)

    flip_tasks = [f.task_id for f in result.flipped_pass_to_fail]
    assert "task-1" in flip_tasks


def test_compare_identifies_improvements() -> None:
    store = MockStore()
    store.add("exp-a", _make_run("task-2", "agent-x", passed=False, failure_category="wrong_diagnosis"))
    store.add("exp-b", _make_run("task-2", "agent-x", passed=True))

    comparator = ExperimentComparator()
    result = comparator.compare("exp-a", "exp-b", store)

    flip_tasks = [f.task_id for f in result.flipped_fail_to_pass]
    assert "task-2" in flip_tasks


def test_compare_computes_correct_deltas() -> None:
    store = MockStore()
    # exp-a: 2/4 pass = 0.5
    store.add("exp-a", _make_run("task-1", "agent-x", passed=True))
    store.add("exp-a", _make_run("task-2", "agent-x", passed=True))
    store.add("exp-a", _make_run("task-3", "agent-x", passed=False))
    store.add("exp-a", _make_run("task-4", "agent-x", passed=False))
    # exp-b: 3/4 pass = 0.75
    store.add("exp-b", _make_run("task-1", "agent-x", passed=True))
    store.add("exp-b", _make_run("task-2", "agent-x", passed=True))
    store.add("exp-b", _make_run("task-3", "agent-x", passed=True))
    store.add("exp-b", _make_run("task-4", "agent-x", passed=False))

    comparator = ExperimentComparator()
    result = comparator.compare("exp-a", "exp-b", store)

    assert len(result.agent_deltas) == 1
    delta = result.agent_deltas[0]
    assert delta.agent_name == "agent-x"
    assert delta.a_pass_rate == pytest.approx(0.5)
    assert delta.b_pass_rate == pytest.approx(0.75)
    assert delta.delta == pytest.approx(0.25)
    assert delta.delta > 0  # improvement


def test_compare_failure_shifts() -> None:
    store = MockStore()
    # exp-a: 5 context_miss failures
    for i in range(5):
        store.add("exp-a", _make_run(f"task-{i}", "agent-x", passed=False, failure_category="context_miss"))
    # exp-b: 3 context_miss failures (2 improved)
    for i in range(3):
        store.add("exp-b", _make_run(f"task-{i}", "agent-x", passed=False, failure_category="context_miss"))
    for i in range(3, 5):
        store.add("exp-b", _make_run(f"task-{i}", "agent-x", passed=True))

    comparator = ExperimentComparator()
    result = comparator.compare("exp-a", "exp-b", store)

    assert "context_miss" in result.failure_shifts
    shift = result.failure_shifts["context_miss"]
    assert shift["a_count"] == 5
    assert shift["b_count"] == 3
    assert shift["delta"] == -2


def test_compare_unique_solves() -> None:
    store = MockStore()
    # task-5 only in exp-b
    store.add("exp-a", _make_run("task-1", "agent-x", passed=True))
    store.add("exp-b", _make_run("task-1", "agent-x", passed=True))
    store.add("exp-b", _make_run("task-5", "agent-x", passed=True))

    comparator = ExperimentComparator()
    result = comparator.compare("exp-a", "exp-b", store)

    assert "task-5" in result.unique_b
    assert "task-5" not in result.unique_a


def test_comparison_result_to_dict() -> None:
    result = ComparisonResult(
        exp_a_id="exp-a",
        exp_b_id="exp-b",
        exp_a_name="Experiment A",
        exp_b_name="Experiment B",
        agent_deltas=[
            AgentDelta(
                agent_name="agent-x",
                a_pass_rate=0.5,
                b_pass_rate=0.75,
                delta=0.25,
                a_pass_b_fail=1,
                a_fail_b_pass=2,
                p_value=0.3,
                significant=False,
            )
        ],
        flipped_pass_to_fail=[
            TaskFlip(
                task_id="task-1",
                agent_name="agent-x",
                direction="pass_to_fail",
                failure_class="context_miss",
            )
        ],
        flipped_fail_to_pass=[],
        failure_shifts={"context_miss": {"a_count": 5, "b_count": 3, "delta": -2}},
        unique_a=[],
        unique_b=["task-5"],
    )

    d = result.to_dict()
    assert d["exp_a_id"] == "exp-a"
    assert d["exp_b_id"] == "exp-b"
    assert "agent_deltas" in d
    assert len(d["agent_deltas"]) == 1
    assert d["agent_deltas"][0]["agent_name"] == "agent-x"
    assert "flipped_pass_to_fail" in d
    assert d["flipped_pass_to_fail"][0]["task_id"] == "task-1"
    assert "flipped_fail_to_pass" in d
    assert "failure_shifts" in d
    assert "unique_a" in d
    assert "unique_b" in d
    assert d["unique_b"] == ["task-5"]
