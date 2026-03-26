"""
Claude Code CLI Adapter — wraps the `claude` CLI tool.

Invokes Claude Code as a subprocess with the task prompt, captures its
structured JSON output, and maps actions to trace events.

Prerequisites:
- `claude` CLI must be installed and on PATH
- ANTHROPIC_API_KEY must be set in the environment

Claude Code CLI usage:
    claude -p "your prompt here" --output-format stream-json --max-turns N

The --output-format stream-json flag produces one JSON object per line with
tool calls, file edits, and reasoning. This adapter parses that output.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentbench.adapters.base import AgentAdapter, AgentConfig, AgentResult
from agentbench.trace.events import EventType, TokenUsage

if TYPE_CHECKING:
    from agentbench.core.models import TaskSpec
    from agentbench.sandbox.manager import Sandbox, SandboxManager
    from agentbench.trace.collector import TraceCollector


class ClaudeCodeNotFoundError(Exception):
    """Raised when the claude CLI is not found on PATH."""


class ClaudeCodeAdapter(AgentAdapter):
    """Adapter that invokes Claude Code CLI as a subprocess."""

    def __init__(self, config: AgentConfig | None = None):
        super().__init__(config)
        self._claude_path = self._find_claude_binary()
        # Tracks the most recently seen tool name to correlate tool_result events
        self._last_tool_name: str = ""

    def name(self) -> str:
        return "claude-code"

    def _find_claude_binary(self) -> str:
        """
        Find the `claude` binary on PATH.

        Checks:
          1. `claude` via shutil.which (covers PATH and aliases)
          2. ~/.claude/local/claude (common npm global install location)

        Raises ClaudeCodeNotFoundError if not found.
        """
        path = shutil.which("claude")
        if path:
            return path

        local_path = Path("~/.claude/local/claude").expanduser()
        if local_path.exists():
            return str(local_path)

        raise ClaudeCodeNotFoundError(
            "Could not find the `claude` CLI on PATH or at ~/.claude/local/claude. "
            "Install it with: npm install -g @anthropic-ai/claude-code"
        )

    async def solve(
        self,
        task: TaskSpec,
        sandbox: Sandbox,
        sandbox_manager: SandboxManager,
        trace: TraceCollector,
    ) -> AgentResult:
        """Run Claude Code CLI on the task and capture its stream-json output."""
        start_time = time.monotonic()
        total_turns = 0
        total_tokens = 0

        trace.record(
            EventType.AGENT_START,
            {"model": self.config.model, "task_id": task.id, "adapter": self.name()},
        )

        cmd = [
            self._claude_path,
            "-p", task.prompt,
            "--output-format", "stream-json",
            "--max-turns", str(task.constraints.max_turns),
            "--model", self.config.model,
        ]

        cwd = str(sandbox.host_workspace_path)
        cmd.extend(["--cwd", cwd])

        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )

        assert proc.stdout is not None

        # Reset per-solve state
        self._last_tool_name = ""

        # Read and parse stream-json output line by line
        async for raw_line in proc.stdout:
            line = raw_line.decode(errors="replace").strip()
            if not line:
                continue
            event_data = self._parse_stream_json_line(line, trace)
            if event_data:
                msg_type = event_data.get("type", "")
                if msg_type == "assistant":
                    total_turns += 1
                elif msg_type == "result":
                    usage = event_data.get("usage", {})
                    total_tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

        completed = False
        reason = "error"
        error: str | None = None
        constraint_hit: str | None = None

        try:
            await asyncio.wait_for(proc.wait(), timeout=task.constraints.timeout_seconds)
            if proc.returncode == 0:
                completed = True
                reason = "completed"
            else:
                reason = "error"
                error = f"claude exited with code {proc.returncode}"
                trace.record(EventType.ERROR, {"message": error, "exit_code": proc.returncode})
        except TimeoutError:
            proc.kill()
            await proc.wait()
            reason = "constraint_hit"
            constraint_hit = "timeout"
            trace.record_constraint_hit(
                "timeout",
                task.constraints.timeout_seconds,
                task.constraints.timeout_seconds,
            )

        wall_clock = time.monotonic() - start_time

        trace.record(
            EventType.AGENT_DONE,
            {
                "completed": completed,
                "reason": reason,
                "total_turns": total_turns,
                "total_tokens": total_tokens,
                "wall_clock_seconds": wall_clock,
            },
        )

        return AgentResult(
            completed=completed,
            reason=reason,
            total_turns=total_turns,
            total_tokens_used=total_tokens,
            wall_clock_seconds=wall_clock,
            error=error,
            constraint_hit=constraint_hit,
        )

    def _parse_stream_json_line(
        self, line: str, trace: TraceCollector
    ) -> dict[str, Any] | None:
        """
        Parse a single line of Claude Code's stream-json output and record trace events.

        Returns the parsed dict so the caller can inspect type fields (e.g. to count turns),
        or None if the line could not be parsed.
        """
        try:
            data: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            return None

        msg_type = data.get("type", "")

        if msg_type == "assistant":
            message = data.get("message", {})
            # message may be a dict with type/text, or a list of content blocks
            if isinstance(message, dict):
                if message.get("type") == "text":
                    trace.record(EventType.AGENT_THINKING, {"content": message.get("text", "")})
                elif message.get("type") == "thinking":
                    trace.record(EventType.AGENT_THINKING, {"content": message.get("thinking", "")})
            elif isinstance(message, list):
                for block in message:
                    if isinstance(block, dict) and block.get("type") == "text":
                        trace.record(EventType.AGENT_THINKING, {"content": block.get("text", "")})

        elif msg_type == "tool_use":
            tool_info = data.get("tool_use", {})
            tool_name: str = tool_info.get("name", "unknown")
            tool_input: dict[str, Any] = tool_info.get("input", {})
            self._last_tool_name = tool_name

            trace.record_tool_call(tool_name, tool_input)

            name_lower = tool_name.lower()
            if name_lower in ("bash", "execute_command"):
                command = tool_input.get("command", tool_input.get("cmd", ""))
                trace.record_command(str(command), working_dir="")
            elif any(kw in name_lower for kw in ("read", "view")):
                file_path = tool_input.get("path", tool_input.get("file_path", ""))
                trace.record_file_read(str(file_path))
            elif any(
                kw in name_lower for kw in ("write", "edit", "create", "str_replace", "patch")
            ):
                file_path = tool_input.get("path", tool_input.get("file_path", ""))
                trace.record_file_write(str(file_path))

        elif msg_type == "tool_result":
            result_info = data.get("tool_result", {})
            content = result_info.get("content", "")
            is_error = bool(result_info.get("is_error", False))
            trace.record_tool_result(self._last_tool_name or "unknown", str(content), is_error)
            if self._last_tool_name.lower() in ("bash", "execute_command"):
                trace.record_command_output(
                    stdout=str(content),
                    stderr="",
                    exit_code=1 if is_error else 0,
                )

        elif msg_type == "result":
            usage = data.get("usage", {})
            if usage:
                token_usage = TokenUsage(
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
                trace.record(
                    EventType.AGENT_THINKING,
                    {"content": data.get("result", ""), "token_usage": token_usage.__dict__},
                )

        return data
