"""Tests for the trace capture system."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from agentbench.trace.collector import TraceCollector
from agentbench.trace.events import EventType, TokenUsage, TraceEvent

if TYPE_CHECKING:
    from pathlib import Path


class TestTraceEvent:
    def test_to_dict_and_back(self):
        event = TraceEvent(
            timestamp=datetime(2026, 3, 24, 10, 0, 0, tzinfo=UTC),
            event_type=EventType.FILE_READ,
            data={"path": "main.py", "size_bytes": 100},
            duration_ms=5,
            sequence_number=0,
        )
        d = event.to_dict()
        restored = TraceEvent.from_dict(d)
        assert restored.event_type == EventType.FILE_READ
        assert restored.data["path"] == "main.py"
        assert restored.duration_ms == 5

    def test_to_dict_with_token_usage(self):
        event = TraceEvent(
            timestamp=datetime.now(UTC),
            event_type=EventType.TOOL_CALL,
            data={"tool": "bash", "input": {"command": "ls"}},
            token_usage=TokenUsage(input_tokens=100, output_tokens=50, thinking_tokens=25),
        )
        d = event.to_dict()
        assert d["token_usage"]["total_tokens"] == 175
        restored = TraceEvent.from_dict(d)
        assert restored.token_usage is not None
        assert restored.token_usage.total_tokens == 175


class TestTokenUsage:
    def test_total_tokens(self):
        t = TokenUsage(input_tokens=100, output_tokens=50, thinking_tokens=25)
        assert t.total_tokens == 175

    def test_defaults_to_zero(self):
        t = TokenUsage()
        assert t.total_tokens == 0


class TestTraceCollector:
    def test_record_event(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        event = tc.record(EventType.FILE_READ, {"path": "main.py", "size_bytes": 100})
        assert event.event_type == EventType.FILE_READ
        assert event.sequence_number == 0
        assert tc.event_count == 1

    def test_sequence_numbers_increment(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        e1 = tc.record(EventType.FILE_READ, {"path": "a.py"})
        e2 = tc.record(EventType.FILE_WRITE, {"path": "b.py"})
        e3 = tc.record(EventType.COMMAND_EXEC, {"command": "ls"})
        assert e1.sequence_number == 0
        assert e2.sequence_number == 1
        assert e3.sequence_number == 2

    def test_convenience_methods(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        tc.record_file_read("main.py", 100)
        tc.record_file_write("main.py", 120, is_new=False)
        tc.record_command("pytest", "/workspace")
        tc.record_command_output("OK", "", 0, duration_ms=500)
        tc.record_error("something broke", "RuntimeError")
        assert tc.event_count == 5
        assert tc.events[0].event_type == EventType.FILE_READ
        assert tc.events[4].event_type == EventType.ERROR

    def test_to_json_and_back(self, tmp_path: Path):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        tc.record_file_read("main.py", 100)
        tc.record_tool_call(
            "bash", {"command": "ls"}, TokenUsage(input_tokens=50, output_tokens=20)
        )
        tc.record_command_output("file1.py\n", "", 0)

        # Save
        trace_path = tmp_path / "trace.json"
        tc.save(trace_path)

        # Load
        loaded = TraceCollector.load(trace_path)
        assert loaded.run_id == "run-1"
        assert loaded.task_id == "task-1"
        assert loaded.agent_name == "test"
        assert loaded.event_count == 3
        assert loaded.events[1].token_usage is not None
        assert loaded.events[1].token_usage.input_tokens == 50

    def test_to_json_is_valid_json(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        tc.record_file_read("main.py")
        json_str = tc.to_json()
        parsed = json.loads(json_str)
        assert parsed["run_id"] == "run-1"
        assert len(parsed["events"]) == 1

    def test_events_returns_copy(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        tc.record_file_read("main.py")
        events = tc.events
        events.clear()
        assert tc.event_count == 1  # original not affected

    def test_record_constraint_hit(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        tc.record_constraint_hit("max_tokens", limit=50000, actual=50001)
        assert tc.events[0].event_type == EventType.CONSTRAINT_HIT
        assert tc.events[0].data["constraint"] == "max_tokens"

    def test_record_test_run_and_result(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        tc.record_test_run("pytest tests/", "pytest")
        tc.record_test_result(passed=5, failed=1, errors=0, output="...", duration_ms=3000)
        assert tc.events[0].event_type == EventType.TEST_RUN
        assert tc.events[1].data["passed"] == 5


class TestTraceSummary:
    def test_summary_from_events(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        tc.record(EventType.AGENT_START, {"prompt": "fix bug", "model": "test", "config": {}})
        tc.record_file_read("main.py", 100)
        tc.record_file_read("utils.py", 200)
        tc.record_file_write("main.py", 150)
        tc.record_tool_call(
            "bash", {"command": "pytest"}, TokenUsage(input_tokens=100, output_tokens=50)
        )
        tc.record_command("pytest")
        tc.record_command_output("OK", "", 0)
        tc.record_test_run("pytest")
        tc.record(EventType.AGENT_DONE, {"reason": "completed"})

        summary = tc.summary()
        assert summary.total_events == 9
        assert summary.total_tokens == 150
        assert summary.total_tool_calls == 1
        assert "main.py" in summary.files_read
        assert "utils.py" in summary.files_read
        assert "main.py" in summary.files_written
        assert summary.commands_executed == 1
        assert summary.test_runs == 1

    def test_empty_trace_summary(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        summary = tc.summary()
        assert summary.total_events == 0
        assert summary.total_tokens == 0

    def test_summary_constraint_hit(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        tc.record_constraint_hit("timeout", limit=600, actual=601)
        summary = tc.summary()
        assert summary.constraint_hit == "timeout"


class TestTimeline:
    def test_to_timeline_produces_string(self):
        tc = TraceCollector(run_id="run-1", task_id="task-1", agent_name="test")
        tc.record_file_read("main.py")
        tc.record_command("pytest")
        timeline = tc.to_timeline()
        assert isinstance(timeline, str)
        assert "FILE_READ" in timeline
        assert "COMMAND_EXEC" in timeline
        assert "main.py" in timeline
