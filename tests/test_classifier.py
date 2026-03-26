"""Tests for the failure classifier."""
from __future__ import annotations

import pytest
from agentbench.classification.classifier import FailureClassifier
from agentbench.classification.taxonomy import FailureCategory
from agentbench.scoring.models import (
    TaskScore, CorrectnessResult, QualityResult, EfficiencyResult, ProcessResult, SecondaryResult,
)
from agentbench.trace.collector import TraceCollector
from agentbench.trace.events import EventType
from agentbench.core.models import TaskSpec


def _make_task(**overrides) -> TaskSpec:
    raw = {
        "id": "test-task", "version": 1,
        "metadata": {"difficulty": "easy", "task_type": "bug_fix", "languages": ["python"],
                     "estimated_human_time_minutes": 5, "source": "test"},
        "setup": {"repo": "/tmp", "commit": "HEAD",
                  "files_to_highlight": overrides.pop("files_to_highlight", ["main.py"])},
        "prompt": "Fix the bug in the code.",
        "evaluation": {"primary": {"type": "test_suite", "command": "pytest", "pass_condition": "exit_code == 0"}},
    }
    raw.update(overrides)
    return TaskSpec.model_validate(raw)


def _make_score(primary_pass: bool = False, partial: float = 0.0, **kwargs) -> TaskScore:
    return TaskScore(
        task_id="test", agent_name="test", run_id="run-1",
        correctness=CorrectnessResult(
            primary_pass=primary_pass, partial_score=partial,
            secondary_results=kwargs.get("secondary", []),
        ),
        quality=QualityResult(diff_within_budget=kwargs.get("diff_within_budget", True)),
        efficiency=EfficiencyResult(),
        process=ProcessResult(),
        overall_pass=primary_pass,
    )


class TestFailureClassifier:
    def test_passing_task_returns_none(self):
        classifier = FailureClassifier()
        score = _make_score(primary_pass=True, partial=1.0)
        trace = TraceCollector("r", "t", "a")
        result = classifier.classify(score, trace, _make_task())
        assert result is None

    def test_timeout_detected(self):
        classifier = FailureClassifier()
        score = _make_score()
        trace = TraceCollector("r", "t", "a")
        trace.record_constraint_hit("timeout", 600, 601)
        result = classifier.classify(score, trace, _make_task())
        assert result is not None
        assert result.primary_category == FailureCategory.TIMEOUT_OR_LOOP

    def test_no_verification_detected(self):
        classifier = FailureClassifier()
        score = _make_score()
        trace = TraceCollector("r", "t", "a")
        trace.record(EventType.AGENT_START, {"prompt": "fix", "model": "t", "config": {}})
        trace.record_file_write("main.py", 100)
        trace.record(EventType.AGENT_DONE, {"reason": "completed"})
        result = classifier.classify(score, trace, _make_task())
        assert result is not None
        assert FailureCategory.NO_VERIFICATION in [result.primary_category] + result.secondary_categories

    def test_context_miss_detected(self):
        classifier = FailureClassifier()
        score = _make_score()
        trace = TraceCollector("r", "t", "a")
        trace.record(EventType.AGENT_START, {"prompt": "fix", "model": "t", "config": {}})
        trace.record_file_read("unrelated.py", 100)  # Read wrong file
        trace.record_file_write("unrelated.py", 120)
        trace.record_command("pytest")
        trace.record_command_output("1 failed", "", 1)
        trace.record(EventType.AGENT_DONE, {"reason": "completed"})

        task = _make_task(files_to_highlight=["main.py", "utils.py"])
        result = classifier.classify(score, trace, task)
        assert result is not None
        assert FailureCategory.CONTEXT_MISS in [result.primary_category] + result.secondary_categories

    def test_incomplete_fix_detected(self):
        classifier = FailureClassifier()
        score = _make_score(primary_pass=False, partial=0.6)
        trace = TraceCollector("r", "t", "a")
        trace.record(EventType.AGENT_START, {"prompt": "fix", "model": "t", "config": {}})
        trace.record_file_read("main.py", 100)
        trace.record_file_write("main.py", 120)
        trace.record_command("pytest")
        trace.record_command_output("3 passed, 2 failed", "", 1)
        trace.record(EventType.AGENT_DONE, {"reason": "completed"})

        result = classifier.classify(score, trace, _make_task())
        assert result is not None
        assert FailureCategory.INCOMPLETE_FIX in [result.primary_category] + result.secondary_categories

    def test_ignored_test_failure_detected(self):
        classifier = FailureClassifier()
        score = _make_score()
        trace = TraceCollector("r", "t", "a")
        trace.record(EventType.AGENT_START, {"prompt": "fix", "model": "t", "config": {}})
        trace.record_file_read("main.py", 100)
        trace.record_file_write("main.py", 120)
        trace.record_command("pytest")
        trace.record_command_output("2 passed, 1 failed", "", 1)  # Tests failed
        # Agent declares done without fixing
        trace.record(EventType.AGENT_DONE, {"reason": "completed"})

        result = classifier.classify(score, trace, _make_task())
        assert result is not None
        assert FailureCategory.IGNORED_TEST_FAILURE in [result.primary_category] + result.secondary_categories

    def test_unknown_fallback(self):
        classifier = FailureClassifier()
        score = _make_score()
        trace = TraceCollector("r", "t", "a")
        trace.record(EventType.AGENT_START, {"prompt": "fix", "model": "t", "config": {}})
        trace.record_file_read("main.py", 100)
        trace.record_file_write("main.py", 120)
        trace.record_command("pytest")
        trace.record_command_output("5 failed", "", 1)
        trace.record_file_write("main.py", 130)  # iterated
        trace.record_command("pytest")
        trace.record_command_output("5 failed", "", 1)
        trace.record(EventType.AGENT_DONE, {"reason": "completed"})

        result = classifier.classify(score, trace, _make_task())
        assert result is not None
        # Should still classify something, likely UNKNOWN or another match
