"""
Mock Agent Adapter — executes a pre-scripted sequence of actions.

Used for integration testing the pipeline without real API calls.
Each action in the script is a dict with:
- type: "bash" | "file_write" | "file_read" | "done"
- For "bash": {"command": str}
- For "file_write": {"path": str, "content": str}
- For "file_read": {"path": str}
- For "done": {}
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from agentbench.adapters.base import AgentAdapter, AgentConfig, AgentResult
from agentbench.trace.events import EventType

if TYPE_CHECKING:
    from agentbench.core.models import TaskSpec
    from agentbench.sandbox.manager import Sandbox, SandboxManager
    from agentbench.trace.collector import TraceCollector


class MockAdapter(AgentAdapter):
    """Adapter that replays a scripted sequence of actions."""

    def __init__(self, script: list[dict[str, Any]], config: AgentConfig | None = None):
        """
        Args:
            script: List of actions to execute in order.
                Each action is a dict like:
                {"type": "bash", "command": "cat main.py"}
                {"type": "file_write", "path": "main.py", "content": "..."}
                {"type": "file_read", "path": "main.py"}
                {"type": "done"}
        """
        super().__init__(config)
        self._script = script

    def name(self) -> str:
        return "mock"

    async def solve(
        self,
        task: TaskSpec,
        sandbox: Sandbox,
        sandbox_manager: SandboxManager,
        trace: TraceCollector,
    ) -> AgentResult:
        """Execute the scripted actions sequentially."""
        start_time = time.monotonic()
        turn_count = 0

        trace.record(EventType.AGENT_START, {
            "prompt": task.prompt,
            "model": "mock",
            "config": {"script_length": len(self._script)},
        })

        for action in self._script:
            action_type = action["type"]

            if action_type == "bash":
                command = action["command"]
                trace.record_command(command)
                result = await sandbox_manager.exec(sandbox, command, timeout=60)
                trace.record_command_output(
                    result.stdout, result.stderr, result.exit_code, result.duration_ms
                )
                turn_count += 1

            elif action_type == "file_read":
                path = action["path"]
                result = await sandbox_manager.exec(sandbox, f"cat {path}", timeout=30)
                trace.record_file_read(path, len(result.stdout.encode()))

            elif action_type == "file_write":
                path = action["path"]
                content = action["content"]
                import base64
                encoded = base64.b64encode(content.encode()).decode()
                cmd = (
                    f"python3 -c \"import base64,pathlib; "
                    f"pathlib.Path('{path}').write_text("
                    f"base64.b64decode('{encoded}').decode())\""
                )
                await sandbox_manager.exec(sandbox, cmd, timeout=30)
                trace.record_file_write(path, len(content.encode()), is_new=False)

            elif action_type == "done":
                trace.record(EventType.AGENT_DONE, {"reason": "completed"})
                return AgentResult(
                    completed=True,
                    reason="completed",
                    total_turns=turn_count,
                    total_tokens_used=0,
                    wall_clock_seconds=time.monotonic() - start_time,
                )

        trace.record(EventType.AGENT_DONE, {"reason": "script_exhausted"})
        return AgentResult(
            completed=True,
            reason="completed",
            total_turns=turn_count,
            total_tokens_used=0,
            wall_clock_seconds=time.monotonic() - start_time,
        )
