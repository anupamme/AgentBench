"""Tests for TraceViewer."""
from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from agentbench.reporting.trace_viewer import TraceViewer
from agentbench.trace.collector import TraceCollector
from agentbench.trace.events import EventType, TokenUsage


@pytest.fixture
def sample_trace() -> TraceCollector:
    """A trace with 3 turns and mixed event types."""
    tc = TraceCollector(run_id="test-run", task_id="test-task", agent_name="test-agent")
    # Turn 0
    tc.record(EventType.AGENT_START, {"agent_name": "test-agent", "agent_version": "1.0", "config": {}})
    tc.record(EventType.FILE_READ, {"path": "src/main.py", "lines_read": 45, "size_bytes": 1200})
    tc.record(EventType.AGENT_THINKING, {"content": "I see the bug on line 23 where division uses //"})
    tc.record(EventType.FILE_READ, {"path": "tests/test_main.py", "lines_read": 30, "size_bytes": 800})
    tc.new_turn()
    # Turn 1
    tc.record(EventType.FILE_WRITE, {"path": "src/main.py", "lines_changed": 2, "diff": "-a // b\n+a / b"})
    tc.record(EventType.COMMAND_EXEC, {"command": "python -m pytest tests/ -v", "workdir": "/workspace"})
    tc.record(
        EventType.TEST_RESULT,
        {
            "exit_code": 0,
            "tests_passed": 5,
            "tests_failed": 0,
            "tests_skipped": 0,
            "output": "5 passed",
            "failures": [],
        },
        token_usage=TokenUsage(input_tokens=5000, output_tokens=2000),
    )
    tc.new_turn()
    # Turn 2
    tc.record(EventType.AGENT_DONE, {"reason": "completed"})
    return tc


def _viewer_and_buf() -> tuple[TraceViewer, StringIO]:
    buf = StringIO()
    console = Console(file=buf, highlight=False, width=120)
    return TraceViewer(console=console), buf


# --- show_timeline tests ---

def test_show_timeline_renders_all_turns(sample_trace: TraceCollector) -> None:
    viewer, buf = _viewer_and_buf()
    viewer.show_timeline(sample_trace)
    output = buf.getvalue()
    assert "Turn 0" in output
    assert "Turn 1" in output
    assert "Turn 2" in output


def test_show_timeline_shows_icons(sample_trace: TraceCollector) -> None:
    viewer, buf = _viewer_and_buf()
    viewer.show_timeline(sample_trace)
    output = buf.getvalue()
    # FILE_READ icon
    assert "📖" in output
    # FILE_WRITE icon
    assert "✏️" in output
    # TEST_RESULT icon
    assert "📊" in output


def test_show_timeline_shows_summary(sample_trace: TraceCollector) -> None:
    viewer, buf = _viewer_and_buf()
    viewer.show_timeline(sample_trace)
    output = buf.getvalue()
    assert "3 turns" in output
    assert "tokens" in output


# --- show_events tests ---

def test_show_events_filters_by_type(sample_trace: TraceCollector) -> None:
    viewer, buf = _viewer_and_buf()
    viewer.show_events(sample_trace, event_types=[EventType.FILE_READ])
    output = buf.getvalue()
    # Should see file paths for the 2 FILE_READ events
    assert "src/main.py" in output
    assert "tests/test_main.py" in output
    # Should NOT see AGENT_THINKING or COMMAND_EXEC content
    assert "COMMAND_EXEC" not in output
    assert "FILE_WRITE" not in output


def test_show_events_shows_filter_count(sample_trace: TraceCollector) -> None:
    viewer, buf = _viewer_and_buf()
    viewer.show_events(sample_trace, event_types=[EventType.FILE_READ])
    output = buf.getvalue()
    assert "Showing 2 events (filtered from" in output


# --- show_turn tests ---

def test_show_turn_detail_shows_full_content(sample_trace: TraceCollector) -> None:
    viewer, buf = _viewer_and_buf()
    viewer.show_turn(sample_trace, turn_number=0)
    output = buf.getvalue()
    # Full thinking content should be present (not truncated)
    assert "I see the bug on line 23 where division uses //" in output


# --- show_files_touched tests ---

def test_show_files_touched_tree(sample_trace: TraceCollector) -> None:
    viewer, buf = _viewer_and_buf()
    viewer.show_files_touched(sample_trace)
    output = buf.getvalue()
    assert "src/main.py" in output or "main.py" in output
    assert "test_main.py" in output


# --- show_token_breakdown tests ---

def test_show_token_breakdown_bars(sample_trace: TraceCollector) -> None:
    viewer, buf = _viewer_and_buf()
    viewer.show_token_breakdown(sample_trace)
    output = buf.getvalue()
    # Bar chart characters
    assert "█" in output
    assert "Total:" in output


# --- helper tests ---

def test_format_relative_time_zero() -> None:
    import datetime

    viewer, _ = _viewer_and_buf()
    from agentbench.trace.events import TraceEvent

    base = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    event = TraceEvent(
        timestamp=base,
        event_type=EventType.AGENT_START,
        data={},
    )
    result = viewer._format_relative_time(event, base)
    assert result == "00:00.000"


def test_format_relative_time_seconds() -> None:
    import datetime

    viewer, _ = _viewer_and_buf()
    from agentbench.trace.events import TraceEvent

    base = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    event = TraceEvent(
        timestamp=base + datetime.timedelta(seconds=1.5),
        event_type=EventType.AGENT_START,
        data={},
    )
    result = viewer._format_relative_time(event, base)
    assert result == "00:01.500"


def test_format_relative_time_over_minute() -> None:
    import datetime

    viewer, _ = _viewer_and_buf()
    from agentbench.trace.events import TraceEvent

    base = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    event = TraceEvent(
        timestamp=base + datetime.timedelta(seconds=65),
        event_type=EventType.AGENT_START,
        data={},
    )
    result = viewer._format_relative_time(event, base)
    assert result == "01:05.000"


def test_detect_lexer_python() -> None:
    viewer, _ = _viewer_and_buf()
    assert viewer._detect_lexer("foo.py") == "python"


def test_detect_lexer_typescript() -> None:
    viewer, _ = _viewer_and_buf()
    assert viewer._detect_lexer("app.ts") == "typescript"
    assert viewer._detect_lexer("app.tsx") == "typescript"


def test_detect_lexer_go() -> None:
    viewer, _ = _viewer_and_buf()
    assert viewer._detect_lexer("main.go") == "go"


def test_detect_lexer_unknown() -> None:
    viewer, _ = _viewer_and_buf()
    assert viewer._detect_lexer("file.xyz") == "text"
