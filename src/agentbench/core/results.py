"""
Results Storage — organizes evaluation run outputs on disk.

Directory structure for a run:
results/<experiment-name>/<task-id>/<agent>/<run-id>/
├── trace.json          # full trace
├── result.json         # AgentResult + TaskScore (once scoring exists)
├── diff.patch          # workspace diff
└── metadata.json       # task spec, agent config, timestamps
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from agentbench.adapters.base import AgentConfig, AgentResult
    from agentbench.classification.taxonomy import FailureClassification
    from agentbench.core.models import TaskSpec
    from agentbench.sandbox.manager import FileDiff
    from agentbench.scoring.models import TaskScore
    from agentbench.trace.collector import TraceCollector


class RunStorage:
    """Manages storage for a single evaluation run."""

    def __init__(self, base_dir: Path, task_id: str, agent_name: str, run_id: str):
        self.run_dir = base_dir / task_id / agent_name / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def save_trace(self, trace: TraceCollector) -> Path:
        path = self.run_dir / "trace.json"
        trace.save(path)
        return path

    def save_result(self, result: AgentResult) -> Path:
        path = self.run_dir / "result.json"
        path.write_text(json.dumps(asdict(result), indent=2, default=str))
        return path

    def save_diff(self, diff: FileDiff) -> Path:
        path = self.run_dir / "diff.patch"
        path.write_text(diff.raw_diff)
        return path

    def save_metadata(self, task: TaskSpec, agent_config: AgentConfig) -> Path:
        path = self.run_dir / "metadata.json"
        metadata: dict[str, Any] = {
            "task_id": task.id,
            "task_version": task.version,
            "agent_config": asdict(agent_config),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        path.write_text(json.dumps(metadata, indent=2, default=str))
        return path

    def load_trace(self) -> TraceCollector:
        from agentbench.trace.collector import TraceCollector

        return TraceCollector.load(self.run_dir / "trace.json")

    def save_score(self, score: TaskScore, failure: FailureClassification | None) -> Path:
        path = self.run_dir / "score.json"
        data: dict[str, Any] = {
            **asdict(score),
            "failure_category": failure.primary_category.value if failure else None,
        }
        path.write_text(json.dumps(data, indent=2, default=str))
        return path

    def load_result(self) -> dict[str, Any]:
        return json.loads((self.run_dir / "result.json").read_text())  # type: ignore[no-any-return]
