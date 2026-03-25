"""
Trace event types and schemas.

Every action an agent takes during a task run is recorded as a TraceEvent
with a specific EventType and typed payload.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    # Agent reasoning
    AGENT_THINKING = "agent_thinking"       # Model reasoning/planning output
    AGENT_MESSAGE = "agent_message"         # Agent's conversational message

    # Tool usage
    TOOL_CALL = "tool_call"                 # Agent invoked a tool
    TOOL_RESULT = "tool_result"             # Tool returned a result

    # File operations
    FILE_READ = "file_read"                 # Agent read a file
    FILE_WRITE = "file_write"              # Agent created or modified a file
    FILE_DELETE = "file_delete"            # Agent deleted a file

    # Shell operations
    COMMAND_EXEC = "command_exec"           # Agent executed a shell command
    COMMAND_OUTPUT = "command_output"       # Output from a shell command

    # Test operations
    TEST_RUN = "test_run"                  # Agent ran a test suite
    TEST_RESULT = "test_result"            # Test suite results

    # Lifecycle
    AGENT_START = "agent_start"            # Agent began working on the task
    AGENT_DONE = "agent_done"              # Agent signaled completion
    ERROR = "error"                        # An error occurred
    CONSTRAINT_HIT = "constraint_hit"      # A constraint was hit (timeout, token limit, etc.)


@dataclass
class TokenUsage:
    """Token consumption for a single API call."""
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0  # for models with extended thinking
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.thinking_tokens


@dataclass
class TraceEvent:
    """A single recorded event in an agent's trace."""
    timestamp: datetime
    event_type: EventType
    data: dict[str, Any]
    duration_ms: int = 0
    token_usage: TokenUsage | None = None
    sequence_number: int = 0  # auto-assigned by TraceCollector

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        result: dict[str, Any] = {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "sequence_number": self.sequence_number,
        }
        if self.token_usage:
            result["token_usage"] = {
                "input_tokens": self.token_usage.input_tokens,
                "output_tokens": self.token_usage.output_tokens,
                "thinking_tokens": self.token_usage.thinking_tokens,
                "cache_read_tokens": self.token_usage.cache_read_tokens,
                "cache_write_tokens": self.token_usage.cache_write_tokens,
                "total_tokens": self.token_usage.total_tokens,
            }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraceEvent:
        """Deserialize from a JSON-compatible dict."""
        token_usage = None
        if "token_usage" in data:
            tu = data["token_usage"]
            token_usage = TokenUsage(
                input_tokens=tu.get("input_tokens", 0),
                output_tokens=tu.get("output_tokens", 0),
                thinking_tokens=tu.get("thinking_tokens", 0),
                cache_read_tokens=tu.get("cache_read_tokens", 0),
                cache_write_tokens=tu.get("cache_write_tokens", 0),
            )
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=EventType(data["event_type"]),
            data=data["data"],
            duration_ms=data.get("duration_ms", 0),
            token_usage=token_usage,
            sequence_number=data.get("sequence_number", 0),
        )
