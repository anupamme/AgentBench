"""Tests for the run orchestrator."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentbench.adapters.base import AgentConfig, AgentResult
from agentbench.classification.taxonomy import FailureCategory, FailureClassification
from agentbench.core.models import TaskSpec
from agentbench.core.orchestrator import Orchestrator, RunResult
from agentbench.sandbox.manager import FileDiff, Sandbox, SandboxStatus
from agentbench.scoring.models import (
    CorrectnessResult,
    EfficiencyResult,
    ProcessResult,
    QualityResult,
    TaskScore,
)
from agentbench.trace.collector import TraceCollector


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

TASK_RAW = {
    "id": "test-orch-task",
    "version": 1,
    "metadata": {
        "difficulty": "easy",
        "task_type": "bug_fix",
        "languages": ["python"],
        "estimated_human_time_minutes": 5,
        "source": "test",
    },
    "setup": {"repo": "/tmp/test", "commit": "HEAD"},
    "prompt": "Fix the bug.",
    "evaluation": {
        "primary": {
            "type": "test_suite",
            "command": "pytest",
            "pass_condition": "exit_code == 0",
        }
    },
}


def _make_task(task_id: str = "test-orch-task") -> TaskSpec:
    raw = dict(TASK_RAW)
    raw["id"] = task_id
    return TaskSpec.model_validate(raw)


def _make_score(task_id: str, pass_: bool) -> TaskScore:
    return TaskScore(
        task_id=task_id,
        agent_name="mock",
        run_id="run-test",
        correctness=CorrectnessResult(primary_pass=pass_),
        quality=QualityResult(),
        efficiency=EfficiencyResult(),
        process=ProcessResult(),
        overall_pass=pass_,
    )


def _make_mock_sandbox() -> Sandbox:
    return Sandbox(
        container_id="cid-test",
        task_id="test-orch-task",
        workspace_path="/workspace",
        host_workspace_path=Path("/tmp/ws"),
        status=SandboxStatus.READY,
    )


def _make_mock_sandbox_manager(sandbox: Sandbox) -> MagicMock:
    """Build a SandboxManager mock whose session() yields the given sandbox."""
    mgr = MagicMock()
    mgr.snapshot_diff = AsyncMock(
        return_value=FileDiff(files_modified=["main.py"], raw_diff="--- a\n+++ b")
    )

    @asynccontextmanager
    async def _session(task: TaskSpec) -> AsyncIterator[Sandbox]:
        yield sandbox

    mgr.session = _session
    return mgr


def _make_mock_adapter(agent_result: AgentResult | None = None) -> MagicMock:
    if agent_result is None:
        agent_result = AgentResult(
            completed=True,
            reason="completed",
            total_turns=2,
            total_tokens_used=500,
            wall_clock_seconds=1.0,
        )
    adapter = MagicMock()
    adapter.name.return_value = "mock"
    adapter.config = AgentConfig()
    adapter.solve = AsyncMock(return_value=agent_result)
    return adapter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunSingleSuccess:
    async def test_returns_run_result_with_score(self, tmp_path: Path) -> None:
        task = _make_task()
        sandbox = _make_mock_sandbox()
        mgr = _make_mock_sandbox_manager(sandbox)
        adapter = _make_mock_adapter()
        score = _make_score(task.id, pass_=True)

        with (
            patch("agentbench.core.orchestrator.SandboxManager", return_value=mgr),
            patch(
                "agentbench.core.orchestrator.Scorer.score",
                new_callable=lambda: lambda *a, **k: AsyncMock(return_value=score)(),
            ),
        ):
            # Patch Scorer.score as an async method on the instance
            orchestrator = Orchestrator(output_dir=tmp_path, sandbox_manager=mgr)
            orchestrator._scorer.score = AsyncMock(return_value=score)
            orchestrator._classifier.classify = MagicMock(return_value=None)

            result = await orchestrator.run_single(task, adapter)

        assert result.task_id == task.id
        assert result.agent_name == "mock"
        assert result.run_id.startswith("run-")
        assert result.score is score
        assert result.error is None

    async def test_output_files_stored(self, tmp_path: Path) -> None:
        """trace.json, result.json, diff.patch, metadata.json must all be written."""
        task = _make_task()
        sandbox = _make_mock_sandbox()
        mgr = _make_mock_sandbox_manager(sandbox)
        adapter = _make_mock_adapter()
        score = _make_score(task.id, pass_=True)

        orchestrator = Orchestrator(output_dir=tmp_path, sandbox_manager=mgr)
        orchestrator._scorer.score = AsyncMock(return_value=score)
        orchestrator._classifier.classify = MagicMock(return_value=None)

        result = await orchestrator.run_single(task, adapter)
        assert result.trace_path is not None

        run_dir = result.trace_path.parent
        assert (run_dir / "trace.json").exists()
        assert (run_dir / "result.json").exists()
        assert (run_dir / "diff.patch").exists()
        assert (run_dir / "metadata.json").exists()

        # Spot-check metadata content
        meta = json.loads((run_dir / "metadata.json").read_text())
        assert meta["task_id"] == task.id

    async def test_directory_structure(self, tmp_path: Path) -> None:
        """Run dir must follow results/<task-id>/<agent>/<run-id>/ layout."""
        task = _make_task("dir-struct-task")
        sandbox = _make_mock_sandbox()
        mgr = _make_mock_sandbox_manager(sandbox)
        adapter = _make_mock_adapter()
        score = _make_score(task.id, pass_=True)

        orchestrator = Orchestrator(output_dir=tmp_path, sandbox_manager=mgr)
        orchestrator._scorer.score = AsyncMock(return_value=score)
        orchestrator._classifier.classify = MagicMock(return_value=None)

        result = await orchestrator.run_single(task, adapter)

        # trace_path is tmp_path/<task-id>/mock/<run-id>/trace.json
        parts = result.trace_path.parts
        assert parts[-1] == "trace.json"
        assert parts[-2] == result.run_id
        assert parts[-3] == "mock"
        assert parts[-4] == task.id


class TestRunSingleErrorHandling:
    async def test_adapter_exception_yields_error_result(self, tmp_path: Path) -> None:
        task = _make_task()
        sandbox = _make_mock_sandbox()
        mgr = _make_mock_sandbox_manager(sandbox)

        adapter = _make_mock_adapter()
        adapter.solve = AsyncMock(side_effect=RuntimeError("adapter exploded"))

        orchestrator = Orchestrator(output_dir=tmp_path, sandbox_manager=mgr)

        result = await orchestrator.run_single(task, adapter)

        assert result.error is not None
        assert "adapter exploded" in result.error
        assert result.score is None
        assert result.failure_classification is None
        assert result.agent_result.reason == "error"
        assert result.agent_result.completed is False


class TestRunSuiteSequential:
    async def test_returns_all_results(self, tmp_path: Path) -> None:
        tasks = [_make_task(f"task-{i}") for i in range(3)]
        sandboxes = [_make_mock_sandbox() for _ in tasks]

        # Reuse same mgr stub (session just yields its sandbox)
        mgr = MagicMock()
        mgr.snapshot_diff = AsyncMock(return_value=FileDiff(raw_diff=""))

        call_idx = 0

        @asynccontextmanager
        async def _session(task: TaskSpec) -> AsyncIterator[Sandbox]:
            nonlocal call_idx
            yield sandboxes[call_idx % len(sandboxes)]
            call_idx += 1

        mgr.session = _session

        adapter = _make_mock_adapter()
        orchestrator = Orchestrator(output_dir=tmp_path, sandbox_manager=mgr)
        orchestrator._scorer.score = AsyncMock(
            side_effect=[_make_score(t.id, True) for t in tasks]
        )
        orchestrator._classifier.classify = MagicMock(return_value=None)

        results = await orchestrator.run_suite(tasks, adapter, parallelism=1)

        assert len(results) == 3
        task_ids = {r.task_id for r in results}
        assert task_ids == {"task-0", "task-1", "task-2"}


class TestRunSuiteParallel:
    async def test_parallel_returns_all_results(self, tmp_path: Path) -> None:
        tasks = [_make_task(f"par-task-{i}") for i in range(4)]

        mgr = MagicMock()
        mgr.snapshot_diff = AsyncMock(return_value=FileDiff(raw_diff=""))

        @asynccontextmanager
        async def _session(task: TaskSpec) -> AsyncIterator[Sandbox]:
            yield _make_mock_sandbox()

        mgr.session = _session

        adapter = _make_mock_adapter()
        orchestrator = Orchestrator(output_dir=tmp_path, sandbox_manager=mgr)

        # Side effects need to handle 4 concurrent calls
        scores = [_make_score(t.id, True) for t in tasks]
        orchestrator._scorer.score = AsyncMock(side_effect=scores)
        orchestrator._classifier.classify = MagicMock(return_value=None)

        results = await orchestrator.run_suite(tasks, adapter, parallelism=2)

        assert len(results) == 4
        returned_ids = {r.task_id for r in results}
        expected_ids = {f"par-task-{i}" for i in range(4)}
        assert returned_ids == expected_ids


class TestFailureClassification:
    async def test_failure_classification_assigned_for_failing_run(
        self, tmp_path: Path
    ) -> None:
        task = _make_task()
        sandbox = _make_mock_sandbox()
        mgr = _make_mock_sandbox_manager(sandbox)
        adapter = _make_mock_adapter()
        score = _make_score(task.id, pass_=False)

        expected_classification = FailureClassification(
            primary_category=FailureCategory.NO_VERIFICATION,
            confidence=0.9,
            evidence=["No test commands found in trace"],
        )

        orchestrator = Orchestrator(output_dir=tmp_path, sandbox_manager=mgr)
        orchestrator._scorer.score = AsyncMock(return_value=score)
        orchestrator._classifier.classify = MagicMock(return_value=expected_classification)

        result = await orchestrator.run_single(task, adapter)

        assert result.failure_classification is expected_classification
        orchestrator._classifier.classify.assert_called_once()
        call_args = orchestrator._classifier.classify.call_args[0]
        assert call_args[0] is score
        assert isinstance(call_args[1], TraceCollector)
        assert call_args[2] is task

    async def test_no_classification_for_passing_run(self, tmp_path: Path) -> None:
        task = _make_task()
        sandbox = _make_mock_sandbox()
        mgr = _make_mock_sandbox_manager(sandbox)
        adapter = _make_mock_adapter()
        score = _make_score(task.id, pass_=True)

        orchestrator = Orchestrator(output_dir=tmp_path, sandbox_manager=mgr)
        orchestrator._scorer.score = AsyncMock(return_value=score)
        # Real classifier returns None for passing runs
        orchestrator._classifier.classify = MagicMock(return_value=None)

        result = await orchestrator.run_single(task, adapter)

        assert result.failure_classification is None
