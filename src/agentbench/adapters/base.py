"""
Agent Adapter — abstract base class for agentic coding tool integrations.

Each adapter wraps a specific tool and implements solve() to attempt
a task in a sandbox while recording all actions to a TraceCollector.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentbench.core.models import TaskSpec
    from agentbench.sandbox.manager import Sandbox, SandboxManager
    from agentbench.trace.collector import TraceCollector


@dataclass
class AgentConfig:
    """Configuration for an agent adapter."""

    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.0
    max_tokens_per_response: int = 8192
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result of an agent's attempt to solve a task."""

    completed: bool                    # Did the agent signal it was done?
    reason: str                        # "completed", "gave_up", "constraint_hit", "error"
    total_turns: int                   # Number of interaction turns
    total_tokens_used: int             # Total tokens consumed
    wall_clock_seconds: float          # Total wall clock time
    error: str | None = None           # Error message if reason == "error"
    constraint_hit: str | None = None  # Which constraint if reason == "constraint_hit"


class AgentAdapter(ABC):
    """Abstract base class for agent adapters."""

    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()

    @abstractmethod
    async def solve(
        self,
        task: TaskSpec,
        sandbox: Sandbox,
        sandbox_manager: SandboxManager,
        trace: TraceCollector,
    ) -> AgentResult:
        """
        Attempt to solve the task in the given sandbox.

        The adapter must:
        1. Record an AGENT_START event to the trace
        2. Feed the task prompt to the agent
        3. Execute the agent's interaction loop:
           a. Receive the agent's response
           b. Execute any tool calls (bash commands, file edits) in the sandbox
           c. Record all events to the trace (TOOL_CALL, TOOL_RESULT, FILE_READ, etc.)
           d. Feed tool results back to the agent
           e. Check constraints after each turn
        4. Record an AGENT_DONE or CONSTRAINT_HIT event
        5. Return an AgentResult

        Args:
            task: The task specification
            sandbox: The sandbox to execute in
            sandbox_manager: Manager for executing commands in the sandbox
            trace: TraceCollector to record all actions

        Returns:
            AgentResult with completion status and statistics
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Return the adapter name (e.g., 'anthropic-api', 'claude-code', 'aider')."""
        ...

    def version(self) -> str:
        """Return the adapter version."""
        return "0.1.0"
