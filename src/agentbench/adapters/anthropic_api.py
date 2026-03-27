"""
Raw Anthropic API Adapter — calls Claude via the Messages API with tool use.

This is the reference adapter implementation. It provides Claude with two tools:
- bash: execute shell commands in the sandbox
- file_editor: read, create, or overwrite files in the workspace

The adapter manages the full conversation loop, tracks token usage,
and enforces constraints (turn limit, token budget, wall clock timeout).
"""
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

import anthropic

from agentbench.adapters.base import AgentAdapter, AgentConfig, AgentResult
from agentbench.trace.events import EventType, TokenUsage

if TYPE_CHECKING:
    from pathlib import Path

    from agentbench.core.models import TaskSpec
    from agentbench.sandbox.manager import Sandbox, SandboxManager
    from agentbench.trace.collector import TraceCollector


# Tool definitions for the Claude API
TOOLS: list[dict[str, Any]] = [
    {
        "name": "bash",
        "description": (
            "Execute a shell command in the workspace. Use this to run tests, "
            "install packages, inspect files with cat/grep/find, and execute scripts. "
            "The working directory is /workspace (the project root)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "file_editor",
        "description": (
            "Read or write files in the workspace. "
            "Use action='read' to read a file's contents. "
            "Use action='write' to create or overwrite a file with new content. "
            "Use action='append' to append content to an existing file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "append"],
                    "description": "The operation to perform",
                },
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace root",
                },
                "content": {
                    "type": "string",
                    "description": "File content (required for write/append, ignored for read)",
                },
            },
            "required": ["action", "path"],
        },
    },
]

SYSTEM_PROMPT = """You are an expert software engineer tasked with solving a coding challenge.
You have access to a workspace with the project's source code.

Available tools:
- bash: Run shell commands (tests, grep, find, etc.)
- file_editor: Read, write, or append to files

Strategy:
1. First, understand the problem by reading relevant files and running tests
2. Identify the root cause
3. Implement a fix
4. Run the tests to verify your fix works
5. If tests fail, iterate

Important:
- Always run the tests before declaring you're done
- Make minimal, focused changes
- Don't modify test files unless the task explicitly asks you to
- If you get stuck, try a different approach rather than repeating the same thing
"""

_TEST_KEYWORDS = ("pytest", "jest", "npm test", "python -m pytest", "go test", "cargo test")


class AnthropicAPIAdapter(AgentAdapter):
    """Adapter that calls Claude via the Anthropic Messages API with tool use.

    Supports two providers:
    - Direct Anthropic API (default): set ANTHROPIC_API_KEY env var or pass api_key.
    - AWS Bedrock: pass use_bedrock=True. Credentials are read from the standard AWS
      env vars (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION) or from
      ~/.aws/credentials. Pass aws_region to override the region.
      Use a Bedrock model ID in AgentConfig, e.g.:
        "us.anthropic.claude-sonnet-4-5-20251001-v1:0"
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        api_key: str | None = None,
        use_bedrock: bool = False,
        aws_region: str | None = None,
    ):
        super().__init__(config)
        # Allow use_bedrock / aws_region to come from config.extra when instantiated
        # via the registry (which only passes config=).
        extra = self.config.extra
        _use_bedrock = use_bedrock or bool(extra.get("use_bedrock", False))
        _aws_region = aws_region or extra.get("aws_region")
        if _use_bedrock:
            self._client: anthropic.AsyncAnthropic | anthropic.AsyncAnthropicBedrock = (
                anthropic.AsyncAnthropicBedrock(aws_region=_aws_region)
            )
        else:
            self._client = anthropic.AsyncAnthropic(api_key=api_key)

    def name(self) -> str:
        return "anthropic-api"

    async def solve(
        self,
        task: TaskSpec,
        sandbox: Sandbox,
        sandbox_manager: SandboxManager,
        trace: TraceCollector,
    ) -> AgentResult:
        """Run the agentic loop using Claude's Messages API."""
        start_time = time.monotonic()
        turn_count = 0
        total_tokens = 0

        trace.record(EventType.AGENT_START, {
            "prompt": task.prompt,
            "model": self.config.model,
            "config": self.config.extra,
        })

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": task.prompt}
        ]

        while True:
            elapsed = time.monotonic() - start_time

            # --- Check constraints ---
            if turn_count >= task.constraints.max_turns:
                trace.record_constraint_hit("max_turns", task.constraints.max_turns, turn_count)
                return AgentResult(
                    completed=False,
                    reason="constraint_hit",
                    total_turns=turn_count,
                    total_tokens_used=total_tokens,
                    wall_clock_seconds=elapsed,
                    constraint_hit="max_turns",
                )
            if total_tokens >= task.constraints.max_tokens:
                trace.record_constraint_hit("max_tokens", task.constraints.max_tokens, total_tokens)
                return AgentResult(
                    completed=False,
                    reason="constraint_hit",
                    total_turns=turn_count,
                    total_tokens_used=total_tokens,
                    wall_clock_seconds=elapsed,
                    constraint_hit="max_tokens",
                )
            if elapsed >= task.constraints.timeout_seconds:
                trace.record_constraint_hit("timeout", task.constraints.timeout_seconds, elapsed)
                return AgentResult(
                    completed=False,
                    reason="constraint_hit",
                    total_turns=turn_count,
                    total_tokens_used=total_tokens,
                    wall_clock_seconds=elapsed,
                    constraint_hit="timeout",
                )

            # --- Call Claude API ---
            try:
                api_start = time.monotonic()
                response = await self._client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens_per_response,
                    temperature=self.config.temperature,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,  # type: ignore[arg-type]
                    messages=messages,
                )
                api_duration_ms = int((time.monotonic() - api_start) * 1000)
            except Exception as e:
                trace.record_error(str(e), type(e).__name__)
                return AgentResult(
                    completed=False,
                    reason="error",
                    total_turns=turn_count,
                    total_tokens_used=total_tokens,
                    wall_clock_seconds=time.monotonic() - start_time,
                    error=str(e),
                )

            # --- Track token usage ---
            token_usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            total_tokens += token_usage.total_tokens

            # --- Process response blocks ---
            tool_results: list[dict[str, Any]] = []
            has_tool_use = False

            for block in response.content:
                if block.type == "text" and block.text.strip():
                    trace.record(
                        EventType.AGENT_THINKING,
                        {"content": block.text},
                        token_usage=token_usage,
                    )
                elif block.type == "tool_use":
                    has_tool_use = True
                    trace.record_tool_call(
                        block.name,
                        block.input,
                        token_usage=token_usage,
                        duration_ms=api_duration_ms,
                    )

                    tool_output, is_error = await self._execute_tool(
                        block.name, block.input, sandbox, sandbox_manager, trace
                    )
                    trace.record_tool_result(block.name, tool_output, is_error=is_error)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_output,
                        "is_error": is_error,
                    })

            # --- Update messages ---
            messages.append({"role": "assistant", "content": response.content})

            if has_tool_use and tool_results:
                messages.append({"role": "user", "content": tool_results})
            elif response.stop_reason == "end_turn":
                trace.record(EventType.AGENT_DONE, {"reason": "completed"})
                return AgentResult(
                    completed=True,
                    reason="completed",
                    total_turns=turn_count,
                    total_tokens_used=total_tokens,
                    wall_clock_seconds=time.monotonic() - start_time,
                )

            turn_count += 1

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        sandbox: Sandbox,
        sandbox_manager: SandboxManager,
        trace: TraceCollector,
    ) -> tuple[str, bool]:
        """Execute a tool call in the sandbox. Returns (output_string, is_error)."""
        if tool_name == "bash":
            command: str = tool_input["command"]
            trace.record_command(command)

            result = await sandbox_manager.exec(sandbox, command, timeout=120)

            trace.record_command_output(
                result.stdout, result.stderr, result.exit_code, result.duration_ms
            )

            if any(kw in command for kw in _TEST_KEYWORDS):
                trace.record_test_run(command)

            output = result.stdout
            if result.stderr:
                output = output + "\n" + result.stderr if output else result.stderr

            return output, result.exit_code != 0

        elif tool_name == "file_editor":
            action: str = tool_input["action"]
            path: str = tool_input["path"]

            if action == "read":
                result = await sandbox_manager.exec(sandbox, f"cat {path}", timeout=30)
                trace.record_file_read(path, len(result.stdout))
                if result.exit_code != 0:
                    return result.stderr or f"Error reading {path}", True
                return result.stdout, False

            elif action in ("write", "append"):
                content: str = tool_input.get("content", "")
                is_new = action == "write"
                await self._write_file(sandbox, path, content, append=not is_new)
                trace.record_file_write(path, len(content), is_new=is_new)
                msg = "File written successfully" if is_new else "Content appended successfully"
                return msg, False

            else:
                return f"Unknown file_editor action: {action}", True

        else:
            return f"Unknown tool: {tool_name}", True

    def _resolve_workspace_path(self, sandbox: Sandbox, path: str) -> Path:
        """Map a container-side path (absolute or relative) to the host filesystem."""
        workspace_prefix = sandbox.workspace_path  # e.g. "/workspace"
        if path.startswith(workspace_prefix + "/"):
            rel = path[len(workspace_prefix) + 1:]
        elif path == workspace_prefix:
            rel = ""
        else:
            # Relative path or unknown absolute path — treat as relative to workspace
            rel = path.lstrip("/")
        return sandbox.host_workspace_path / rel

    async def _write_file(
        self, sandbox: Sandbox, path: str, content: str, append: bool = False
    ) -> None:
        """Write or append content to a file via the host-side workspace mount.

        Writing directly to host_workspace_path (which is bind-mounted as /workspace
        in the container) avoids ARG_MAX limits that would affect exec-based approaches
        for large files.
        """
        host_path = self._resolve_workspace_path(sandbox, path)

        def _do_write() -> None:
            host_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            host_path.open(mode).write(content)

        await asyncio.to_thread(_do_write)
