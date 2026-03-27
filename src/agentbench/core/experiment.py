"""
Experiment configuration — defines multi-agent comparison experiments.
"""
from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentExperimentConfig:
    name: str
    adapter: str
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.0
    max_tokens_per_response: int = 8192
    extra: dict = field(default_factory=dict)


@dataclass
class ExperimentConfig:
    name: str
    suite: str                               # Suite name or path
    runs_per_task: int = 1                   # Number of runs per task per agent
    agents: list[AgentExperimentConfig] = field(default_factory=list)
    parallelism: int = 1

    @classmethod
    def load(cls, path: Path) -> ExperimentConfig:
        """Load experiment config from a YAML file."""
        with open(path) as f:
            raw = yaml.safe_load(f)
        agents = [AgentExperimentConfig(**a) for a in raw.get("agents", [])]
        return cls(
            name=raw["name"],
            suite=raw["suite"],
            runs_per_task=raw.get("runs_per_task", 1),
            agents=agents,
            parallelism=raw.get("parallelism", 1),
        )
