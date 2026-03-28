"""
Run Orchestrator — executes evaluation runs and manages the pipeline.

Pipeline per task:
1. Load task spec
2. Create sandbox
3. Initialize trace collector
4. Run agent adapter
5. Score the result
6. Classify failures (if failed)
7. Store all outputs
8. Teardown sandbox
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from agentbench.adapters.base import AgentAdapter, AgentResult
from agentbench.classification.classifier import FailureClassifier
from agentbench.core.results import RunStorage
from agentbench.sandbox.manager import SandboxManager
from agentbench.scoring.scorer import Scorer
from agentbench.trace.collector import TraceCollector

if TYPE_CHECKING:
    from agentbench.classification.taxonomy import FailureClassification
    from agentbench.core.models import TaskSpec
    from agentbench.scoring.models import TaskScore


@dataclass
class RunResult:
    """Complete result of a single task run."""

    task_id: str
    agent_name: str
    run_id: str
    agent_result: AgentResult
    score: TaskScore | None
    failure_classification: FailureClassification | None
    trace_path: Path | None
    error: str | None = None


class Orchestrator:
    """Orchestrates evaluation runs."""

    def __init__(
        self,
        output_dir: Path = Path("results"),
        sandbox_manager: SandboxManager | None = None,
    ):
        self.output_dir = output_dir
        self._sandbox_manager = sandbox_manager or SandboxManager()
        self._scorer = Scorer()
        self._classifier = FailureClassifier()

    async def run_single(
        self,
        task: TaskSpec,
        adapter: AgentAdapter,
    ) -> RunResult:
        """
        Execute a single task with a single agent.

        Steps:
        1. Generate a unique run_id (UUID)
        2. Create sandbox
        3. Create TraceCollector
        4. Call adapter.solve()
        5. Score the result (in the sandbox, before teardown)
        6. Classify failure if applicable
        7. Capture filesystem diff
        8. Store all outputs via RunStorage
        9. Teardown sandbox
        10. Return RunResult

        Error handling: if any step fails, catch the exception, record it,
        teardown the sandbox, and return RunResult with error set.
        """
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        storage = RunStorage(self.output_dir, task.id, adapter.name(), run_id)

        try:
            async with self._sandbox_manager.session(task) as sandbox:
                trace = TraceCollector(run_id, task.id, adapter.name())

                # Run agent
                agent_result = await adapter.solve(task, sandbox, self._sandbox_manager, trace)

                # Score
                score = await self._scorer.score(
                    task, sandbox, self._sandbox_manager, trace, run_id, adapter.name()
                )

                # Classify failure
                failure = self._classifier.classify(score, trace, task)

                # Capture diff
                diff = await self._sandbox_manager.snapshot_diff(sandbox)

                # Store results
                trace_path = storage.save_trace(trace)
                storage.save_result(agent_result)
                storage.save_diff(diff)
                storage.save_metadata(task, adapter.config)
                storage.save_score(score, failure)

                return RunResult(
                    task_id=task.id,
                    agent_name=adapter.name(),
                    run_id=run_id,
                    agent_result=agent_result,
                    score=score,
                    failure_classification=failure,
                    trace_path=trace_path,
                )

        except Exception as e:
            return RunResult(
                task_id=task.id,
                agent_name=adapter.name(),
                run_id=run_id,
                agent_result=AgentResult(
                    completed=False,
                    reason="error",
                    total_turns=0,
                    total_tokens_used=0,
                    wall_clock_seconds=0,
                    error=str(e),
                ),
                score=None,
                failure_classification=None,
                trace_path=None,
                error=str(e),
            )

    async def run_suite(
        self,
        tasks: list[TaskSpec],
        adapter: AgentAdapter,
        parallelism: int = 1,
    ) -> list[RunResult]:
        """
        Run multiple tasks, optionally in parallel.

        If parallelism == 1: run sequentially.
        If parallelism > 1: use asyncio.Semaphore to limit concurrent runs.

        Displays progress using rich.progress.Progress bar.
        """
        from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

        results: list[RunResult] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True,
        ) as progress:
            progress_task = progress.add_task(
                f"Running {len(tasks)} task(s) with {adapter.name()}...",
                total=len(tasks),
            )

            if parallelism <= 1:
                for task in tasks:
                    result = await self.run_single(task, adapter)
                    results.append(result)
                    progress.advance(progress_task)
            else:
                semaphore = asyncio.Semaphore(parallelism)

                async def run_with_semaphore(task: TaskSpec) -> RunResult:
                    async with semaphore:
                        result = await self.run_single(task, adapter)
                        progress.advance(progress_task)
                        return result

                results = list(
                    await asyncio.gather(*[run_with_semaphore(t) for t in tasks])
                )

        return results
