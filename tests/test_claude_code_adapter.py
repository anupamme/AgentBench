"""Tests for Claude Code CLI adapter — uses mocked subprocess calls."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentbench.adapters.base import AgentConfig
from agentbench.adapters.claude_code import ClaudeCodeAdapter, ClaudeCodeNotFoundError
from agentbench.core.models import TaskSpec
from agentbench.trace.collector import TraceCollector
from agentbench.trace.events import EventType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(max_turns: int = 10, timeout_seconds: int = 600) -> TaskSpec:
    return TaskSpec.model_validate(
        {
            "id": "test-cc-task",
            "version": 1,
            "metadata": {
                "difficulty": "easy",
                "task_type": "bug_fix",
                "languages": ["python"],
                "estimated_human_time_minutes": 5,
                "source": "test",
            },
            "setup": {"repo": "/tmp/test", "commit": "HEAD"},
            "prompt": "Fix the bug.",
            "evaluation": {
                "primary": {
                    "type": "test_suite",
                    "command": "pytest",
                    "pass_condition": "exit_code == 0",
                }
            },
            "constraints": {
                "max_turns": max_turns,
                "max_tokens": 200000,
                "timeout_seconds": timeout_seconds,
                "network": False,
            },
        }
    )


def _make_mock_sandbox(workspace: str = "/tmp/workspace") -> MagicMock:
    mock = MagicMock()
    mock.host_workspace_path = Path(workspace)
    return mock


def _make_proc(lines: list[bytes], returncode: int = 0) -> AsyncMock:
    """Build a mock subprocess that yields the given output lines then EOF."""

    async def _readline_gen() -> asyncio.StreamReader:
        raise NotImplementedError  # not used directly

    mock_proc = AsyncMock()
    mock_proc.returncode = returncode

    # Build an async iterator that yields each line then stops
    async def _aiter(self: object) -> object:
        for line in lines:
            yield line

    reader = MagicMock()
    reader.__aiter__ = _aiter
    mock_proc.stdout = reader
    mock_proc.wait = AsyncMock(return_value=returncode)
    return mock_proc


# ---------------------------------------------------------------------------
# Unit tests — binary discovery
# ---------------------------------------------------------------------------


class TestClaudeCodeAdapterBinaryDiscovery:
    def test_adapter_name(self) -> None:
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter()
            assert adapter.name() == "claude-code"

    def test_claude_not_found_raises(self) -> None:
        with (
            patch("shutil.which", return_value=None),
            patch.object(Path, "exists", return_value=False),
            pytest.raises(ClaudeCodeNotFoundError),
        ):
            ClaudeCodeAdapter()

    def test_finds_via_which(self) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            adapter = ClaudeCodeAdapter()
            assert adapter._claude_path == "/usr/local/bin/claude"

    async def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter()
        with pytest.raises(OSError, match="ANTHROPIC_API_KEY"):
            await adapter.solve(
                _make_task(),
                _make_mock_sandbox(),
                MagicMock(),
                TraceCollector("r", "t", "claude-code"),
            )

    def test_finds_via_local_path(self) -> None:
        with (
            patch("shutil.which", return_value=None),
            patch.object(Path, "exists", return_value=True),
        ):
            adapter = ClaudeCodeAdapter()
            assert "claude" in adapter._claude_path


# ---------------------------------------------------------------------------
# Unit tests — Bedrock support
# ---------------------------------------------------------------------------


class TestBedrockSupport:
    @pytest.fixture
    def adapter(self) -> ClaudeCodeAdapter:
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            return ClaudeCodeAdapter(use_bedrock=True)

    def test_bedrock_sets_flag(self) -> None:
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter(use_bedrock=True)
        assert adapter._use_bedrock is True

    def test_bedrock_build_env_sets_var(
        self, adapter: ClaudeCodeAdapter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
        env = adapter._build_env()
        assert env["CLAUDE_CODE_USE_BEDROCK"] == "1"

    def test_bedrock_build_env_sets_region(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter(use_bedrock=True, aws_region="us-west-2")
        env = adapter._build_env()
        assert env["AWS_REGION"] == "us-west-2"

    def test_bedrock_region_does_not_override_when_none(
        self, adapter: ClaudeCodeAdapter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        env = adapter._build_env()
        # aws_region=None → existing env var should be untouched
        assert env["AWS_REGION"] == "eu-west-1"

    def test_bedrock_missing_credentials_raises(
        self, adapter: ClaudeCodeAdapter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.delenv("AWS_ROLE_ARN", raising=False)
        with pytest.raises(OSError, match="Bedrock authentication"):
            adapter._build_env()

    def test_bedrock_accepts_aws_profile(
        self, adapter: ClaudeCodeAdapter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_ROLE_ARN", raising=False)
        monkeypatch.setenv("AWS_PROFILE", "my-profile")
        env = adapter._build_env()  # should not raise
        assert env["CLAUDE_CODE_USE_BEDROCK"] == "1"

    def test_bedrock_accepts_role_arn(
        self, adapter: ClaudeCodeAdapter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.setenv("AWS_ROLE_ARN", "arn:aws:iam::123456789012:role/MyRole")
        env = adapter._build_env()  # should not raise
        assert env["CLAUDE_CODE_USE_BEDROCK"] == "1"

    def test_direct_api_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter(use_bedrock=False)
        with pytest.raises(OSError, match="ANTHROPIC_API_KEY"):
            adapter._build_env()


# ---------------------------------------------------------------------------
# Unit tests — _parse_stream_json_line
# ---------------------------------------------------------------------------


class TestParseStreamJsonLine:
    @pytest.fixture
    def adapter(self) -> ClaudeCodeAdapter:
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            return ClaudeCodeAdapter()

    @pytest.fixture
    def trace(self) -> TraceCollector:
        return TraceCollector("run-1", "task-1", "claude-code")

    def test_text_message_creates_thinking_event(
        self, adapter: ClaudeCodeAdapter, trace: TraceCollector
    ) -> None:
        line = json.dumps(
            {"type": "assistant", "message": {"type": "text", "text": "Let me look at the code."}}
        )
        adapter._parse_stream_json_line(line, trace)

        thinking = [e for e in trace.events if e.event_type == EventType.AGENT_THINKING]
        assert len(thinking) == 1
        assert thinking[0].data["content"] == "Let me look at the code."

    def test_tool_use_bash_creates_tool_call_and_command(
        self, adapter: ClaudeCodeAdapter, trace: TraceCollector
    ) -> None:
        line = json.dumps(
            {
                "type": "tool_use",
                "tool_use": {"name": "bash", "input": {"command": "cat main.py"}},
            }
        )
        adapter._parse_stream_json_line(line, trace)

        tool_events = [e for e in trace.events if e.event_type == EventType.TOOL_CALL]
        assert len(tool_events) == 1
        assert tool_events[0].data["tool"] == "bash"

        cmd_events = [e for e in trace.events if e.event_type == EventType.COMMAND_EXEC]
        assert len(cmd_events) == 1

    def test_tool_use_read_creates_file_read_event(
        self, adapter: ClaudeCodeAdapter, trace: TraceCollector
    ) -> None:
        line = json.dumps(
            {
                "type": "tool_use",
                "tool_use": {"name": "read_file", "input": {"path": "src/main.py"}},
            }
        )
        adapter._parse_stream_json_line(line, trace)

        file_read = [e for e in trace.events if e.event_type == EventType.FILE_READ]
        assert len(file_read) == 1
        assert file_read[0].data["path"] == "src/main.py"

    def test_tool_use_write_creates_file_write_event(
        self, adapter: ClaudeCodeAdapter, trace: TraceCollector
    ) -> None:
        line = json.dumps(
            {
                "type": "tool_use",
                "tool_use": {"name": "write_file", "input": {"path": "src/fix.py"}},
            }
        )
        adapter._parse_stream_json_line(line, trace)

        file_write = [e for e in trace.events if e.event_type == EventType.FILE_WRITE]
        assert len(file_write) == 1

    def test_tool_result_creates_tool_result_event(
        self, adapter: ClaudeCodeAdapter, trace: TraceCollector
    ) -> None:
        adapter._last_tool_name = "bash"
        line = json.dumps(
            {
                "type": "tool_result",
                "tool_result": {"content": "output text", "is_error": False},
            }
        )
        adapter._parse_stream_json_line(line, trace)

        result_events = [e for e in trace.events if e.event_type == EventType.TOOL_RESULT]
        assert len(result_events) == 1
        assert result_events[0].data["tool"] == "bash"

    def test_invalid_json_returns_none(
        self, adapter: ClaudeCodeAdapter, trace: TraceCollector
    ) -> None:
        result = adapter._parse_stream_json_line("not json {{", trace)
        assert result is None
        assert len(trace.events) == 0

    def test_unknown_type_returns_data_without_events(
        self, adapter: ClaudeCodeAdapter, trace: TraceCollector
    ) -> None:
        line = json.dumps({"type": "system", "data": "some system message"})
        result = adapter._parse_stream_json_line(line, trace)
        assert result is not None
        assert len(trace.events) == 0


# ---------------------------------------------------------------------------
# Integration tests — solve()
# ---------------------------------------------------------------------------


class TestClaudeCodeAdapterSolve:
    @pytest.fixture(autouse=True)
    def _set_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    async def test_solve_records_agent_start(self) -> None:
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter(AgentConfig(model="test-model"))
        trace = TraceCollector("run-1", "task-1", "claude-code")

        lines = [
            json.dumps({"type": "assistant", "message": {"type": "text", "text": "Done."}}).encode()
            + b"\n",
        ]
        mock_proc = _make_proc(lines, returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await adapter.solve(_make_task(), _make_mock_sandbox(), MagicMock(), trace)

        start_events = [e for e in trace.events if e.event_type == EventType.AGENT_START]
        assert len(start_events) == 1
        assert start_events[0].data["model"] == "test-model"
        assert start_events[0].data["provider"] == "anthropic"

    async def test_solve_bedrock_provider_in_agent_start(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
        bedrock_model = "us.anthropic.claude-sonnet-4-5-20251001-v1:0"
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter(AgentConfig(model=bedrock_model), use_bedrock=True)
        trace = TraceCollector("run-1", "task-1", "claude-code")

        mock_proc = _make_proc([], returncode=0)
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await adapter.solve(_make_task(), _make_mock_sandbox(), MagicMock(), trace)

        start_events = [e for e in trace.events if e.event_type == EventType.AGENT_START]
        assert start_events[0].data["provider"] == "bedrock"

    async def test_solve_records_agent_done(self) -> None:
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter(AgentConfig(model="test"))
        trace = TraceCollector("run-1", "task-1", "claude-code")

        mock_proc = _make_proc([], returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter.solve(_make_task(), _make_mock_sandbox(), MagicMock(), trace)

        done_events = [e for e in trace.events if e.event_type == EventType.AGENT_DONE]
        assert len(done_events) == 1
        assert result.completed is True
        assert result.reason == "completed"

    async def test_solve_nonzero_exit_returns_error(self) -> None:
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter(AgentConfig(model="test"))
        trace = TraceCollector("run-1", "task-1", "claude-code")

        mock_proc = _make_proc([], returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter.solve(_make_task(), _make_mock_sandbox(), MagicMock(), trace)

        assert result.completed is False
        assert result.reason == "error"

    async def test_solve_timeout_records_constraint_hit(self) -> None:
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter(AgentConfig(model="test"))
        trace = TraceCollector("run-1", "task-1", "claude-code")

        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.stdout = MagicMock()

        async def _empty_aiter(self: object) -> object:
            return
            yield  # make it an async generator

        mock_proc.stdout.__aiter__ = _empty_aiter
        # proc.wait() is called directly after proc.kill() — should succeed
        mock_proc.wait = AsyncMock(return_value=-9)
        mock_proc.kill = MagicMock()

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.wait_for", side_effect=asyncio.TimeoutError),
        ):
            result = await adapter.solve(
                _make_task(timeout_seconds=1), _make_mock_sandbox(), MagicMock(), trace
            )

        assert result.completed is False
        assert result.reason == "constraint_hit"
        assert result.constraint_hit == "timeout"

        constraint_events = [e for e in trace.events if e.event_type == EventType.CONSTRAINT_HIT]
        assert len(constraint_events) == 1

    async def test_solve_parses_stream_json_events(self) -> None:
        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter(AgentConfig(model="test"))
        trace = TraceCollector("run-1", "task-1", "claude-code")

        lines = [
            json.dumps(
                {"type": "assistant", "message": {"type": "text", "text": "Thinking..."}}
            ).encode()
            + b"\n",
            json.dumps(
                {
                    "type": "tool_use",
                    "tool_use": {"name": "bash", "input": {"command": "ls -la"}},
                }
            ).encode()
            + b"\n",
            json.dumps(
                {
                    "type": "tool_result",
                    "tool_result": {"content": "main.py\n", "is_error": False},
                }
            ).encode()
            + b"\n",
        ]
        mock_proc = _make_proc(lines, returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await adapter.solve(_make_task(), _make_mock_sandbox(), MagicMock(), trace)

        event_types = [e.event_type for e in trace.events]
        assert EventType.AGENT_THINKING in event_types
        assert EventType.TOOL_CALL in event_types
        assert EventType.TOOL_RESULT in event_types


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestClaudeCodeRegistry:
    def test_claude_code_registered(self) -> None:
        from agentbench.adapters.registry import list_adapters

        assert "claude-code" in list_adapters()

    def test_get_claude_code_adapter(self) -> None:
        from agentbench.adapters.registry import get_adapter

        with patch.object(ClaudeCodeAdapter, "_find_claude_binary", return_value="/usr/bin/claude"):
            adapter = get_adapter("claude-code", AgentConfig(model="test"))
        assert adapter.name() == "claude-code"
