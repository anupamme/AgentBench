"""Tests for agent adapters."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentbench.adapters.base import AgentConfig
from agentbench.adapters.registry import AdapterNotFoundError, get_adapter, list_adapters


class TestAdapterRegistry:
    def test_list_adapters(self) -> None:
        adapters = list_adapters()
        assert "anthropic-api" in adapters

    def test_get_unknown_adapter(self) -> None:
        with pytest.raises(AdapterNotFoundError):
            get_adapter("nonexistent-adapter")

    def test_get_anthropic_adapter(self) -> None:
        adapter = get_adapter("anthropic-api", AgentConfig(model="test-model"))
        assert adapter.name() == "anthropic-api"
        assert adapter.config.model == "test-model"


class TestAnthropicAPIAdapter:
    """Unit tests for the Anthropic API adapter using mocked API calls."""

    @pytest.fixture
    def mock_anthropic_response(self) -> MagicMock:
        """Create a mock Anthropic API response."""
        response = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "I've analyzed the code and it looks correct."
        response.content = [text_block]
        return response

    @pytest.fixture
    def mock_tool_use_response(self) -> MagicMock:
        """Create a mock response with a tool call."""
        response = MagicMock()
        response.usage.input_tokens = 150
        response.usage.output_tokens = 80
        response.stop_reason = "tool_use"
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "bash"
        tool_block.input = {"command": "cat main.py"}
        tool_block.id = "tool_abc123"
        response.content = [tool_block]
        return response

    async def test_adapter_records_agent_start(
        self, mock_anthropic_response: MagicMock
    ) -> None:
        """The adapter should record an AGENT_START event."""
        from agentbench.adapters.anthropic_api import AnthropicAPIAdapter
        from agentbench.core.models import TaskSpec
        from agentbench.trace.collector import TraceCollector
        from agentbench.trace.events import EventType

        adapter = AnthropicAPIAdapter(AgentConfig(model="test"))
        trace = TraceCollector("run-1", "task-1", "anthropic-api")

        adapter._client = AsyncMock()
        adapter._client.messages.create = AsyncMock(return_value=mock_anthropic_response)

        task_raw = {
            "id": "test-adapter-task",
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
        }
        task = TaskSpec.model_validate(task_raw)

        mock_sandbox = MagicMock()
        mock_sandbox_manager = MagicMock()

        await adapter.solve(task, mock_sandbox, mock_sandbox_manager, trace)

        start_events = [e for e in trace.events if e.event_type == EventType.AGENT_START]
        assert len(start_events) == 1
        assert start_events[0].data["model"] == "test"

    async def test_adapter_returns_completed_on_end_turn(
        self, mock_anthropic_response: MagicMock
    ) -> None:
        """When the model responds with end_turn and no tool calls, adapter returns completed."""
        from agentbench.adapters.anthropic_api import AnthropicAPIAdapter
        from agentbench.core.models import TaskSpec
        from agentbench.trace.collector import TraceCollector

        adapter = AnthropicAPIAdapter(AgentConfig(model="test"))
        trace = TraceCollector("run-1", "task-1", "anthropic-api")
        adapter._client = AsyncMock()
        adapter._client.messages.create = AsyncMock(return_value=mock_anthropic_response)

        task_raw = {
            "id": "test-adapter-task",
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
        }
        task = TaskSpec.model_validate(task_raw)

        result = await adapter.solve(task, MagicMock(), MagicMock(), trace)
        assert result.completed is True
        assert result.reason == "completed"

    async def test_adapter_enforces_max_turns(self) -> None:
        """Adapter should stop when max_turns is reached."""
        from agentbench.adapters.anthropic_api import AnthropicAPIAdapter
        from agentbench.core.models import TaskSpec
        from agentbench.trace.collector import TraceCollector

        adapter = AnthropicAPIAdapter(AgentConfig(model="test"))
        trace = TraceCollector("run-1", "task-1", "anthropic-api")

        # Mock: always return a tool call (never completes)
        tool_response = MagicMock()
        tool_response.usage.input_tokens = 100
        tool_response.usage.output_tokens = 50
        tool_response.stop_reason = "tool_use"
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "bash"
        tool_block.input = {"command": "echo loop"}
        tool_block.id = "tool_loop"
        tool_response.content = [tool_block]

        adapter._client = AsyncMock()
        adapter._client.messages.create = AsyncMock(return_value=tool_response)

        mock_sandbox_manager = AsyncMock()
        mock_exec_result = MagicMock()
        mock_exec_result.exit_code = 0
        mock_exec_result.stdout = "loop"
        mock_exec_result.stderr = ""
        mock_exec_result.timed_out = False
        mock_exec_result.duration_ms = 10
        mock_sandbox_manager.exec = AsyncMock(return_value=mock_exec_result)

        task_raw = {
            "id": "test-max-turns",
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
                "max_turns": 3,
                "max_tokens": 999999,
                "timeout_seconds": 999,
                "network": False,
            },
        }
        task = TaskSpec.model_validate(task_raw)

        result = await adapter.solve(task, MagicMock(), mock_sandbox_manager, trace)
        assert result.completed is False
        assert result.reason == "constraint_hit"
        assert result.constraint_hit == "max_turns"
