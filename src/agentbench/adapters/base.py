"""
Agent Adapter — pluggable interface for different agentic coding tools.

Each adapter wraps a specific tool (Claude API, Claude Code CLI, Aider, etc.)
and implements the solve() method to attempt a task in a sandbox.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class AgentAdapter(ABC):
    @abstractmethod
    async def solve(
        self,
        prompt: str,
        workspace: Path,
        sandbox: object,
        constraints: object,
        trace_collector: object,
    ) -> object: ...

    @abstractmethod
    def name(self) -> str: ...

    def version(self) -> str:
        return "0.0.0"

    def config(self) -> dict[str, object]:
        return {}
