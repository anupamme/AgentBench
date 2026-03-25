"""
Trace Collector — the primary interface for recording agent actions.

Agent adapters call methods on TraceCollector to record events as they happen.
The collector assigns sequence numbers, timestamps, and stores events in memory.
After a run, the trace can be serialized to JSON and written to disk.
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from agentbench.trace.events import EventType, TokenUsage, TraceEvent
from agentbench.trace.summary import TraceSummary

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


class TraceCollector:
    """Collects trace events during an agent run."""

    def __init__(self, run_id: str, task_id: str, agent_name: str):
        self.run_id = run_id
        self.task_id = task_id
        self.agent_name = agent_name
        self._events: list[TraceEvent] = []
        self._sequence: int = 0
        self._start_time: datetime | None = None

    @property
    def events(self) -> list[TraceEvent]:
        """Return a copy of the recorded events."""
        return list(self._events)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def record(
        self,
        event_type: EventType,
        data: dict[str, Any],
        duration_ms: int = 0,
        token_usage: TokenUsage | None = None,
    ) -> TraceEvent:
        """Record a single trace event."""
        now = datetime.now(UTC)
        if self._start_time is None:
            self._start_time = now

        event = TraceEvent(
            timestamp=now,
            event_type=event_type,
            data=data,
            duration_ms=duration_ms,
            token_usage=token_usage,
            sequence_number=self._sequence,
        )
        self._events.append(event)
        self._sequence += 1
        return event

    # --- Convenience methods ---

    def record_file_read(self, path: str, size_bytes: int = 0) -> TraceEvent:
        return self.record(EventType.FILE_READ, {"path": path, "size_bytes": size_bytes})

    def record_file_write(
        self, path: str, size_bytes: int = 0, is_new: bool = False
    ) -> TraceEvent:
        return self.record(
            EventType.FILE_WRITE,
            {"path": path, "size_bytes": size_bytes, "is_new": is_new},
        )

    def record_command(self, command: str, working_dir: str = "") -> TraceEvent:
        return self.record(
            EventType.COMMAND_EXEC, {"command": command, "working_dir": working_dir}
        )

    def record_command_output(
        self, stdout: str, stderr: str, exit_code: int, duration_ms: int = 0
    ) -> TraceEvent:
        return self.record(
            EventType.COMMAND_OUTPUT,
            {"stdout": stdout, "stderr": stderr, "exit_code": exit_code},
            duration_ms=duration_ms,
        )

    def record_tool_call(
        self,
        tool: str,
        input_data: dict[str, Any],
        token_usage: TokenUsage | None = None,
        duration_ms: int = 0,
    ) -> TraceEvent:
        return self.record(
            EventType.TOOL_CALL,
            {"tool": tool, "input": input_data},
            duration_ms=duration_ms,
            token_usage=token_usage,
        )

    def record_tool_result(self, tool: str, output: str, is_error: bool = False) -> TraceEvent:
        return self.record(
            EventType.TOOL_RESULT, {"tool": tool, "output": output, "is_error": is_error}
        )

    def record_test_run(self, command: str, framework: str = "pytest") -> TraceEvent:
        return self.record(EventType.TEST_RUN, {"command": command, "framework": framework})

    def record_test_result(
        self, passed: int, failed: int, errors: int, output: str, duration_ms: int = 0
    ) -> TraceEvent:
        return self.record(
            EventType.TEST_RESULT,
            {"passed": passed, "failed": failed, "errors": errors, "output": output},
            duration_ms=duration_ms,
        )

    def record_error(self, message: str, error_type: str = "", traceback: str = "") -> TraceEvent:
        return self.record(
            EventType.ERROR, {"message": message, "type": error_type, "traceback": traceback}
        )

    def record_constraint_hit(self, constraint: str, limit: Any, actual: Any) -> TraceEvent:
        return self.record(
            EventType.CONSTRAINT_HIT, {"constraint": constraint, "limit": limit, "actual": actual}
        )

    @contextmanager
    def timed_event(
        self,
        event_type: EventType,
        data: dict[str, Any],
        token_usage: TokenUsage | None = None,
    ) -> Generator[TraceEvent, None, None]:
        """Context manager that records an event with automatic duration measurement."""
        start = time.monotonic()
        event = TraceEvent(
            timestamp=datetime.now(UTC),
            event_type=event_type,
            data=data,
            token_usage=token_usage,
            sequence_number=self._sequence,
        )
        self._sequence += 1
        self._events.append(event)
        try:
            yield event
        finally:
            event.duration_ms = int((time.monotonic() - start) * 1000)

    # --- Summarization and serialization ---

    def summary(self) -> TraceSummary:
        """Compute aggregate statistics from the recorded events."""
        return TraceSummary.from_events(self._events)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full trace to a JSON-compatible dict."""
        s = self.summary()
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "event_count": len(self._events),
            "summary": {
                "total_tokens": s.total_tokens,
                "total_tool_calls": s.total_tool_calls,
                "wall_clock_seconds": s.wall_clock_seconds,
            },
            "events": [e.to_dict() for e in self._events],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: Path) -> None:
        """Write the trace to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())

    @classmethod
    def load(cls, path: Path) -> TraceCollector:
        """Load a trace from a JSON file."""
        raw = json.loads(path.read_text())
        collector = cls(
            run_id=raw["run_id"],
            task_id=raw["task_id"],
            agent_name=raw["agent_name"],
        )
        collector._events = [TraceEvent.from_dict(e) for e in raw["events"]]
        collector._sequence = len(collector._events)
        return collector

    def to_timeline(self, max_width: int = 120) -> str:
        """Generate a human-readable timeline string."""
        if not self._events:
            return ""

        lines: list[str] = []
        origin = self._events[0].timestamp

        for event in self._events:
            offset = (event.timestamp - origin).total_seconds()
            minutes = int(offset // 60)
            seconds = offset % 60
            timestamp_str = f"[{minutes:02d}:{seconds:06.3f}]"

            event_label = event.event_type.value.upper().ljust(14)
            description = self._describe_event(event)

            line = f"{timestamp_str} {event_label} | {description}"
            if len(line) > max_width:
                line = line[: max_width - 1] + "…"
            lines.append(line)

        return "\n".join(lines)

    def _describe_event(self, event: TraceEvent) -> str:
        d = event.data
        et = event.event_type

        if et == EventType.FILE_READ:
            return f"Read {d.get('path', '')} ({d.get('size_bytes', 0)} bytes)"
        elif et == EventType.FILE_WRITE:
            return f"Wrote {d.get('path', '')} ({d.get('size_bytes', 0)} bytes)"
        elif et == EventType.FILE_DELETE:
            return f"Deleted {d.get('path', '')}"
        elif et == EventType.COMMAND_EXEC:
            return f"$ {d.get('command', '')}"
        elif et == EventType.COMMAND_OUTPUT:
            return f"exit_code={d.get('exit_code', '')}"
        elif et == EventType.TOOL_CALL:
            tool = d.get("tool", "")
            inp = str(d.get("input", ""))
            tokens = ""
            if event.token_usage:
                tokens = f" (tokens: {event.token_usage.total_tokens})"
            return f"{tool}: {inp}{tokens}"
        elif et == EventType.TOOL_RESULT:
            tool = d.get("tool", "")
            output = str(d.get("output", ""))
            return f"{tool} → {output[:50]}"
        elif et == EventType.TEST_RUN:
            return str(d.get("command", ""))
        elif et == EventType.TEST_RESULT:
            return f"{d.get('passed', 0)} passed, {d.get('failed', 0)} failed"
        elif et == EventType.AGENT_START:
            return f"Started task (model: {d.get('model', '')})"
        elif et == EventType.AGENT_DONE:
            return f"Done: {d.get('reason', '')}"
        elif et == EventType.ERROR:
            return f"ERROR: {d.get('message', '')}"
        elif et == EventType.CONSTRAINT_HIT:
            return (
                f"Constraint hit: {d.get('constraint', '')} "
                f"(limit={d.get('limit')}, actual={d.get('actual')})"
            )
        else:
            return str(d)
