"""
Trace Collector — records every action an agent takes during a task run.

Captures tool calls, file reads/writes, shell commands, token usage,
and timing information for post-hoc analysis and failure classification.
"""
from __future__ import annotations


class TraceCollector:
    """Collects and stores trace events during an agent run."""

    def record(self, event_type: str, data: dict) -> None:
        raise NotImplementedError

    def summary(self) -> dict:
        raise NotImplementedError

    def to_json(self) -> str:
        raise NotImplementedError
