"""
Report Data Loader — reads stored results into analysis-ready structures.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunData:
    task_id: str
    agent_name: str
    run_id: str
    passed: bool
    score: dict | None              # TaskScore.to_dict() format
    result: dict | None             # AgentResult dict
    failure_category: str | None    # FailureCategory value
    total_tokens: int = 0
    total_turns: int = 0
    wall_clock_seconds: float = 0.0


@dataclass
class ExperimentData:
    """All results from a single experiment or result directory."""
    base_dir: Path
    runs: list[RunData] = field(default_factory=list)

    @classmethod
    def load(cls, results_dir: Path) -> ExperimentData:
        """
        Walk results_dir recursively and load all run data.

        Expected structure:
        results_dir/
        ├── task-id-1/
        │   └── agent-name/
        │       └── run-xxx/
        │           ├── score.json
        │           ├── result.json
        │           └── metadata.json
        """
        experiment = cls(base_dir=results_dir)

        if not results_dir.is_dir():
            return experiment

        for task_dir in sorted(results_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            for agent_dir in sorted(task_dir.iterdir()):
                if not agent_dir.is_dir():
                    continue
                for run_dir in sorted(agent_dir.iterdir()):
                    if not run_dir.is_dir():
                        continue

                    task_id = task_dir.name
                    agent_name = agent_dir.name
                    run_id = run_dir.name

                    score_data: dict | None = None
                    result_data: dict | None = None

                    score_path = run_dir / "score.json"
                    if score_path.exists():
                        score_data = json.loads(score_path.read_text())

                    result_path = run_dir / "result.json"
                    if result_path.exists():
                        result_data = json.loads(result_path.read_text())

                    # Derive pass/fail
                    if score_data is not None:
                        passed = bool(score_data.get("overall_pass", False))
                    elif result_data is not None:
                        passed = bool(result_data.get("completed", False))
                    else:
                        passed = False

                    # Derive efficiency stats
                    if score_data is not None:
                        eff = score_data.get("efficiency", {})
                        total_tokens = int(eff.get("total_tokens", 0))
                        total_turns = int(eff.get("total_turns", 0))
                        wall_clock_seconds = float(eff.get("wall_clock_seconds", 0.0))
                    elif result_data is not None:
                        total_tokens = int(result_data.get("total_tokens_used", 0))
                        total_turns = int(result_data.get("total_turns", 0))
                        wall_clock_seconds = float(result_data.get("wall_clock_seconds", 0.0))
                    else:
                        total_tokens = 0
                        total_turns = 0
                        wall_clock_seconds = 0.0

                    failure_category = score_data.get("failure_category") if score_data else None

                    experiment.runs.append(RunData(
                        task_id=task_id,
                        agent_name=agent_name,
                        run_id=run_id,
                        passed=passed,
                        score=score_data,
                        result=result_data,
                        failure_category=failure_category,
                        total_tokens=total_tokens,
                        total_turns=total_turns,
                        wall_clock_seconds=wall_clock_seconds,
                    ))

        return experiment

    def by_agent(self) -> dict[str, list[RunData]]:
        """Group runs by agent name."""
        groups: dict[str, list[RunData]] = {}
        for run in self.runs:
            groups.setdefault(run.agent_name, []).append(run)
        return groups

    def by_task(self) -> dict[str, list[RunData]]:
        """Group runs by task ID."""
        groups: dict[str, list[RunData]] = {}
        for run in self.runs:
            groups.setdefault(run.task_id, []).append(run)
        return groups

    def pass_rate(self, agent: str | None = None) -> float:
        """Overall pass rate, optionally filtered by agent."""
        runs = [r for r in self.runs if agent is None or r.agent_name == agent]
        if not runs:
            return 0.0
        return sum(1 for r in runs if r.passed) / len(runs)

    def failure_distribution(self, agent: str | None = None) -> dict[str, int]:
        """Count of each failure category."""
        runs = [r for r in self.runs if agent is None or r.agent_name == agent]
        counts: dict[str, int] = {}
        for run in runs:
            if run.failure_category:
                counts[run.failure_category] = counts.get(run.failure_category, 0) + 1
        return counts
