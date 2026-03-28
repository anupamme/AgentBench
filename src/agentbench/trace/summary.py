"""
Trace Summary — aggregate statistics computed from a trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agentbench.trace.events import EventType, TraceEvent


@dataclass
class TraceSummary:
    """Aggregate statistics for a completed trace."""

    total_events: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    total_turns: int = 0  # number of TOOL_CALL events (proxy for turns)
    total_tool_calls: int = 0
    total_api_calls: int = 0  # number of events with token_usage
    files_read: list[str] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    commands_executed: int = 0
    test_runs: int = 0
    wall_clock_seconds: float = 0.0
    constraint_hit: str | None = None  # which constraint was hit, if any
    error_count: int = 0

    @classmethod
    def from_events(cls, events: list[TraceEvent]) -> TraceSummary:
        """Compute summary from a list of trace events."""
        summary = cls()
        summary.total_events = len(events)

        if not events:
            return summary

        files_read: dict[str, None] = {}
        files_written: dict[str, None] = {}
        files_deleted: dict[str, None] = {}

        for event in events:
            if event.token_usage is not None:
                summary.total_api_calls += 1
                summary.input_tokens += event.token_usage.input_tokens
                summary.output_tokens += event.token_usage.output_tokens
                summary.thinking_tokens += event.token_usage.thinking_tokens
                summary.total_tokens += event.token_usage.total_tokens

            et = event.event_type

            if et == EventType.TOOL_CALL:
                summary.total_tool_calls += 1
                summary.total_turns += 1

            elif et == EventType.FILE_READ:
                path = event.data.get("path", "")
                if path:
                    files_read[path] = None

            elif et == EventType.FILE_WRITE:
                path = event.data.get("path", "")
                if path:
                    files_written[path] = None

            elif et == EventType.FILE_DELETE:
                path = event.data.get("path", "")
                if path:
                    files_deleted[path] = None

            elif et == EventType.COMMAND_EXEC:
                summary.commands_executed += 1

            elif et == EventType.TEST_RUN:
                summary.test_runs += 1

            elif et == EventType.CONSTRAINT_HIT and summary.constraint_hit is None:
                summary.constraint_hit = event.data.get("constraint")

            elif et == EventType.ERROR:
                summary.error_count += 1

        summary.files_read = list(files_read)
        summary.files_written = list(files_written)
        summary.files_deleted = list(files_deleted)
        summary.wall_clock_seconds = (events[-1].timestamp - events[0].timestamp).total_seconds()

        return summary
