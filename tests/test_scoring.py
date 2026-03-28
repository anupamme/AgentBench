"""Tests for the multi-dimensional scoring pipeline."""
from __future__ import annotations

import pytest

from agentbench.scoring.models import (
    CorrectnessResult,
    EfficiencyResult,
    ProcessResult,
    QualityResult,
    TaskScore,
)
from agentbench.scoring.scorer import Scorer


class TestParsePartialScore:
    def test_pytest_passed_and_failed(self):
        scorer = Scorer()
        output = "===== 3 passed, 1 failed in 0.5s ====="
        assert scorer._parse_partial_score(output) == 0.75

    def test_pytest_all_passed(self):
        scorer = Scorer()
        output = "===== 5 passed in 0.3s ====="
        assert scorer._parse_partial_score(output) == 1.0

    def test_jest_output(self):
        scorer = Scorer()
        output = "Tests: 8 passed, 2 failed, 10 total"
        assert scorer._parse_partial_score(output) == 0.8

    def test_failed_before_passed(self):
        scorer = Scorer()
        output = "===== 1 failed, 5 passed in 0.5s ====="
        assert scorer._parse_partial_score(output) == pytest.approx(5 / 6)

    def test_no_pattern_returns_zero(self):
        scorer = Scorer()
        assert scorer._parse_partial_score("random output") == 0.0

    def test_passed_with_failures_in_output_not_false_positive(self):
        scorer = Scorer()
        # "5 passed" is present but so is "failed" — must not return 1.0
        output = "1 failed, 5 passed in 0.5s"
        assert scorer._parse_partial_score(output) == pytest.approx(5 / 6)


class TestProcessScoring:
    def test_read_before_edit_detected(self):
        """When FILE_READ comes before FILE_WRITE, read_before_edit should be True."""
        from agentbench.core.models import TaskSpec
        from agentbench.trace.collector import TraceCollector
        from agentbench.trace.events import EventType

        trace = TraceCollector("run-1", "task-1", "test")
        trace.record(EventType.AGENT_START, {"prompt": "fix", "model": "test", "config": {}})
        trace.record_file_read("main.py", 100)
        trace.record_file_write("main.py", 120)
        trace.record_command("pytest")
        trace.record_command_output("1 passed", "", 0)
        trace.record(EventType.AGENT_DONE, {"reason": "completed"})

        scorer = Scorer()
        task_raw = {
            "id": "test-task", "version": 1,
            "metadata": {"difficulty": "easy", "task_type": "bug_fix", "languages": ["python"],
                         "estimated_human_time_minutes": 5, "source": "test"},
            "setup": {"repo": "/tmp", "commit": "HEAD", "files_to_highlight": ["main.py"]},
            "prompt": "Fix the bug in main.py.",
            "evaluation": {"primary": {
                "type": "test_suite", "command": "pytest", "pass_condition": "exit_code == 0",
            }},
        }
        task = TaskSpec.model_validate(task_raw)
        result = scorer._score_process(trace, task)
        assert result.read_before_edit is True

    def test_no_read_before_edit(self):
        """When FILE_WRITE comes first, read_before_edit should be False."""
        from agentbench.core.models import TaskSpec
        from agentbench.trace.collector import TraceCollector
        from agentbench.trace.events import EventType

        trace = TraceCollector("run-1", "task-1", "test")
        trace.record(EventType.AGENT_START, {"prompt": "fix", "model": "test", "config": {}})
        trace.record_file_write("main.py", 120)
        trace.record(EventType.AGENT_DONE, {"reason": "completed"})

        scorer = Scorer()
        task_raw = {
            "id": "test-task", "version": 1,
            "metadata": {"difficulty": "easy", "task_type": "bug_fix", "languages": ["python"],
                         "estimated_human_time_minutes": 5, "source": "test"},
            "setup": {"repo": "/tmp", "commit": "HEAD"},
            "prompt": "Fix the bug in main.py.",
            "evaluation": {"primary": {
                "type": "test_suite", "command": "pytest", "pass_condition": "exit_code == 0",
            }},
        }
        task = TaskSpec.model_validate(task_raw)
        result = scorer._score_process(trace, task)
        assert result.read_before_edit is False


class TestTaskScore:
    def test_to_dict(self):
        score = TaskScore(
            task_id="test", agent_name="mock", run_id="run-1",
            correctness=CorrectnessResult(primary_pass=True, partial_score=1.0),
            quality=QualityResult(lint_clean=True),
            efficiency=EfficiencyResult(total_tokens=500, total_turns=3),
            process=ProcessResult(read_before_edit=True, ran_tests_before_done=True),
            overall_pass=True,
        )
        d = score.to_dict()
        assert d["task_id"] == "test"
        assert d["correctness"]["primary_pass"] is True
        assert d["efficiency"]["total_tokens"] == 500
