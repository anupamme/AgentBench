# Agent Adapter Guide

This guide explains how to add a new agent adapter to AgentBench.

## AgentAdapter Interface

All adapters inherit from `AgentAdapter` in `src/agentbench/adapters/base.py`.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentConfig:
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.0
    max_tokens_per_response: int = 8192
    extra: dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentResult:
    completed: bool           # Did the agent signal completion?
    reason: str               # "completed" | "gave_up" | "constraint_hit" | "error"
    total_turns: int          # Number of interaction turns
    total_tokens_used: int    # Total tokens consumed
    wall_clock_seconds: float # Wall clock time
    error: str | None = None
    constraint_hit: str | None = None

class AgentAdapter(ABC):
    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()

    @abstractmethod
    async def solve(
        self,
        task: TaskSpec,
        sandbox: Sandbox,
        sandbox_manager: SandboxManager,
        trace: TraceCollector,
    ) -> AgentResult: ...

    @abstractmethod
    def name(self) -> str: ...

    def version(self) -> str:
        return "0.1.0"
```

## Walk-Through: A Minimal Adapter

Here is a complete, minimal adapter that calls the Anthropic API with tool use:

```python
"""Minimal Anthropic API adapter example."""
from __future__ import annotations

import time

import anthropic

from agentbench.adapters.base import AgentAdapter, AgentConfig, AgentResult
from agentbench.core.models import TaskSpec
from agentbench.sandbox.manager import Sandbox, SandboxManager
from agentbench.trace.collector import TraceCollector
from agentbench.trace.events import EventType


class MinimalAnthropicAdapter(AgentAdapter):
    """Calls the Anthropic API with a bash tool and iterates until done."""

    def name(self) -> str:
        return "minimal-anthropic"

    async def solve(
        self,
        task: TaskSpec,
        sandbox: Sandbox,
        sandbox_manager: SandboxManager,
        trace: TraceCollector,
    ) -> AgentResult:
        client = anthropic.Anthropic()
        start = time.monotonic()

        trace.record(EventType.AGENT_START, {
            "model": self.config.model,
            "prompt_length": len(task.prompt),
        })

        bash_tool = {
            "name": "bash",
            "description": "Run a bash command in the workspace.",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        }

        messages = [{"role": "user", "content": task.prompt}]
        total_tokens = 0
        turns = 0

        while turns < task.constraints.max_turns:
            response = client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens_per_response,
                tools=[bash_tool],
                messages=messages,
            )
            total_tokens += response.usage.input_tokens + response.usage.output_tokens
            turns += 1

            # Append assistant message
            messages.append({"role": "assistant", "content": response.content})

            # Check if we're done (no tool calls)
            if response.stop_reason == "end_turn":
                trace.record(EventType.AGENT_DONE, {"reason": "completed"})
                return AgentResult(
                    completed=True,
                    reason="completed",
                    total_turns=turns,
                    total_tokens_used=total_tokens,
                    wall_clock_seconds=time.monotonic() - start,
                )

            # Execute tool calls
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                command = block.input["command"]
                trace.record(EventType.TOOL_CALL, {
                    "tool": "bash",
                    "command": command,
                })

                result = await sandbox_manager.exec(sandbox, command)

                trace.record(EventType.TOOL_RESULT, {
                    "stdout": result.stdout[:2000],
                    "stderr": result.stderr[:500],
                    "exit_code": result.exit_code,
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result.stdout + result.stderr,
                })

            messages.append({"role": "user", "content": tool_results})

        trace.record(EventType.CONSTRAINT_HIT, {"constraint": "max_turns"})
        return AgentResult(
            completed=False,
            reason="constraint_hit",
            total_turns=turns,
            total_tokens_used=total_tokens,
            wall_clock_seconds=time.monotonic() - start,
            constraint_hit="max_turns",
        )
```

## How to Register a Custom Adapter

Open `src/agentbench/adapters/registry.py` and add your adapter to the `ADAPTER_REGISTRY` dict:

```python
from agentbench.adapters.my_adapter import MinimalAnthropicAdapter

ADAPTER_REGISTRY: dict[str, type[AgentAdapter]] = {
    "anthropic-api": AnthropicAPIAdapter,
    "claude-code": ClaudeCodeAdapter,
    "mock": MockAdapter,
    "minimal-anthropic": MinimalAnthropicAdapter,  # <-- add this
}
```

Then use it via the CLI:

```bash
agentbench run --task my-task --agent minimal-anthropic
```

## Trace Events to Record

Your adapter should record these events as it runs. All are defined in `src/agentbench/trace/events.py`:

| Event | When to record |
|---|---|
| `AGENT_START` | Before sending the first message to the agent |
| `TOOL_CALL` | Before executing each tool call |
| `TOOL_RESULT` | After receiving the tool result |
| `FILE_READ` | When the agent reads a file |
| `FILE_WRITE` | When the agent writes a file |
| `COMMAND_EXEC` | When the agent runs a shell command (non-test) |
| `TEST_RUN` | When the agent runs tests (detected from command pattern) |
| `AGENT_DONE` | When the agent signals completion |
| `CONSTRAINT_HIT` | When a constraint (max_turns, max_tokens, timeout) is hit |

## Tips for Parsing Agent Outputs

**Detecting test runs** — Check if the command matches common test runner patterns:
```python
TEST_PATTERNS = ["pytest", "python -m pytest", "npm test", "go test", "cargo test"]
event_type = EventType.TEST_RUN if any(p in command for p in TEST_PATTERNS) else EventType.COMMAND_EXEC
```

**Truncating large outputs** — Sandbox outputs can be very large. Truncate before recording to keep trace files manageable:
```python
trace.record(EventType.TOOL_RESULT, {
    "stdout": result.stdout[:4000],
    "truncated": len(result.stdout) > 4000,
})
```

**Token budget enforcement** — Check `task.constraints.max_tokens` and return a `constraint_hit` result if exceeded:
```python
if total_tokens >= task.constraints.max_tokens:
    trace.record(EventType.CONSTRAINT_HIT, {"constraint": "max_tokens"})
    return AgentResult(completed=False, reason="constraint_hit",
                       constraint_hit="max_tokens", ...)
```

**Timeout enforcement** — Use `asyncio.wait_for` or check elapsed time after each turn:
```python
elapsed = time.monotonic() - start
if elapsed >= task.constraints.timeout_seconds:
    trace.record(EventType.CONSTRAINT_HIT, {"constraint": "timeout"})
    return AgentResult(completed=False, reason="constraint_hit",
                       constraint_hit="timeout", ...)
```
