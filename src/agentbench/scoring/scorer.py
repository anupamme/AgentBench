"""
Multi-dimensional scoring pipeline.

Takes a completed run (sandbox + trace + eval spec) and produces a TaskScore
across four dimensions: correctness, quality, efficiency, process.
"""
from __future__ import annotations

import re

from agentbench.core.models import TaskSpec, EvalType
from agentbench.sandbox.manager import Sandbox, SandboxManager, FileDiff
from agentbench.trace.collector import TraceCollector
from agentbench.trace.events import EventType
from agentbench.trace.summary import TraceSummary
from agentbench.scoring.models import (
    TaskScore, CorrectnessResult, SecondaryResult,
    QualityResult, EfficiencyResult, ProcessResult,
)

_TEST_KEYWORDS = ("pytest", "jest", "unittest", "npm test", "go test")


class Scorer:
    """Evaluates a completed agent run across multiple dimensions."""

    async def score(
        self,
        task: TaskSpec,
        sandbox: Sandbox,
        sandbox_manager: SandboxManager,
        trace: TraceCollector,
        run_id: str,
        agent_name: str,
    ) -> TaskScore:
        """
        Run the full scoring pipeline.

        Steps:
        1. Score correctness by running eval commands in the sandbox
        2. Score quality from secondary eval results and file diff
        3. Score efficiency from trace summary
        4. Score process quality from trace event analysis
        5. Assemble and return TaskScore
        """
        diff = await sandbox_manager.snapshot_diff(sandbox)
        correctness = await self._score_correctness(task, sandbox, sandbox_manager, diff)
        quality = self._score_quality(task, sandbox_manager, diff, correctness)
        summary = trace.summary()
        efficiency = self._score_efficiency(summary, trace)
        process = self._score_process(trace, task)

        return TaskScore(
            task_id=task.id,
            agent_name=agent_name,
            run_id=run_id,
            correctness=correctness,
            quality=quality,
            efficiency=efficiency,
            process=process,
            overall_pass=correctness.primary_pass,
        )

    async def _score_correctness(
        self, task: TaskSpec, sandbox: Sandbox, sandbox_manager: SandboxManager, diff: FileDiff,
    ) -> CorrectnessResult:
        """
        Run the primary and secondary evaluation criteria.

        Primary:
        - Execute task.evaluation.primary.command in the sandbox
        - Check pass_condition (currently only "exit_code == 0" supported)
        - Parse test output for partial credit: look for patterns like
          "X passed, Y failed" or pytest's summary line

        Secondary:
        - Execute each task.evaluation.secondary criterion
        - For diff_size type: compute diff and check max_lines_changed
        - For other types: run the command and check exit code
        """
        # Primary evaluation
        primary_result = await sandbox_manager.exec(
            sandbox, task.evaluation.primary.command,
            timeout=task.evaluation.primary.timeout_seconds,
        )
        primary_pass = primary_result.exit_code == 0
        partial = self._parse_partial_score(primary_result.stdout + primary_result.stderr)

        # Secondary evaluations
        secondary_results = []
        for criterion in task.evaluation.secondary:
            if criterion.type == EvalType.DIFF_SIZE:
                total_changed = diff.total_lines_added + diff.total_lines_deleted
                passed = total_changed <= (criterion.max_lines_changed or 999999)
                secondary_results.append(SecondaryResult(
                    label=criterion.label,
                    passed=passed,
                    output=f"Lines changed: {total_changed}, max: {criterion.max_lines_changed}",
                ))
            elif criterion.command:
                sec_result = await sandbox_manager.exec(
                    sandbox, criterion.command, timeout=criterion.timeout_seconds,
                )
                secondary_results.append(SecondaryResult(
                    label=criterion.label,
                    passed=sec_result.exit_code == 0,
                    output=sec_result.stdout[:2000],
                    exit_code=sec_result.exit_code,
                ))

        return CorrectnessResult(
            primary_pass=primary_pass,
            primary_output=primary_result.stdout[:5000],
            primary_exit_code=primary_result.exit_code,
            partial_score=partial if not primary_pass else 1.0,
            secondary_results=secondary_results,
        )

    def _parse_partial_score(self, output: str) -> float:
        """
        Parse test output for partial credit.

        Patterns to look for (checked in order of specificity):
        - pytest: "X passed, Y failed" or "Y failed, X passed" → X / (X + Y)
        - jest: "Tests: X passed, Y failed, Z total" → X / Z
        - pytest: "X passed" with no failures present → 1.0

        Returns 0.0 if no pattern matches.
        """
        # pytest: both orderings of passed/failed
        m = re.search(r"(\d+)\s+passed[^,]*,\s*(\d+)\s+failed", output)
        if not m:
            m = re.search(r"(\d+)\s+failed[^,]*,\s*(\d+)\s+passed", output)
            if m:
                # swap so group(1)=passed, group(2)=failed
                passed, failed = int(m.group(2)), int(m.group(1))
                return passed / (passed + failed) if (passed + failed) > 0 else 0.0
        if m:
            passed = int(m.group(1))
            failed = int(m.group(2))
            return passed / (passed + failed) if (passed + failed) > 0 else 0.0

        # jest pattern
        m = re.search(r"Tests:\s+(\d+)\s+passed.*?(\d+)\s+total", output)
        if m:
            passed = int(m.group(1))
            total = int(m.group(2))
            return passed / total if total > 0 else 0.0

        # pytest: "X passed" only if no failures are mentioned
        if "failed" not in output:
            m = re.search(r"(\d+)\s+passed", output)
            if m:
                return 1.0

        return 0.0

    def _score_quality(
        self, task: TaskSpec, sandbox_manager: SandboxManager,
        diff: FileDiff, correctness: CorrectnessResult,
    ) -> QualityResult:
        """
        Score code quality from diff and secondary results.

        - lint_clean: True if any secondary with label containing "lint" passed
        - type_check_clean: True if any secondary with label containing "type" passed
        - diff metrics from the FileDiff
        - diff_within_budget: True if diff_size secondary (if any) passed
        """
        lint_clean = True
        type_check_clean = True
        diff_within_budget = True

        for sr in correctness.secondary_results:
            if "lint" in sr.label.lower():
                lint_clean &= sr.passed
            if "type" in sr.label.lower():
                type_check_clean &= sr.passed
            if "diff" in sr.label.lower():
                diff_within_budget &= sr.passed

        return QualityResult(
            lint_clean=lint_clean,
            type_check_clean=type_check_clean,
            diff_lines_changed=diff.total_lines_added + diff.total_lines_deleted,
            diff_lines_added=diff.total_lines_added,
            diff_lines_deleted=diff.total_lines_deleted,
            diff_within_budget=diff_within_budget,
        )

    def _score_efficiency(self, summary: TraceSummary, trace: TraceCollector) -> EfficiencyResult:
        """Score efficiency from trace summary."""
        files_read = summary.files_read
        return EfficiencyResult(
            total_tokens=summary.total_tokens,
            input_tokens=summary.input_tokens,
            output_tokens=summary.output_tokens,
            thinking_tokens=summary.thinking_tokens,
            total_turns=summary.total_turns,
            total_tool_calls=summary.total_tool_calls,
            wall_clock_seconds=summary.wall_clock_seconds,
            files_read_count=len(files_read),
            files_written_count=len(summary.files_written),
            commands_executed=summary.commands_executed,
            tokens_per_turn=summary.total_tokens / max(summary.total_turns, 1),
        )

    def _score_process(self, trace: TraceCollector, task: TaskSpec) -> ProcessResult:
        """
        Score process quality by analyzing the trace event sequence.

        Heuristics:
        - read_before_edit: Did any FILE_READ event occur before the first FILE_WRITE?
        - ran_tests_before_done: Is there a TEST_RUN (or COMMAND_EXEC containing "pytest"/"jest")
          event before AGENT_DONE?
        - iterated_on_failure: If any COMMAND_OUTPUT has exit_code != 0 after a test command,
          is there a subsequent FILE_WRITE followed by another test command?
        - explored_codebase: Did the agent read files beyond those in files_to_highlight?
        - test_run_count: count of TEST_RUN events + COMMAND_EXEC events whose command
          contains test-related keywords
        """
        events = trace.events
        highlight_set = set(task.setup.files_to_highlight)

        read_before_edit = False
        first_write_seen = False
        ran_tests_before_done = False
        iterated_on_failure = False
        files_read_set: set[str] = set()
        test_run_count = 0

        # State machine for iterated_on_failure
        last_test_failed = False
        wrote_after_failure = False
        prev_was_test_cmd = False

        for event in events:
            etype = event.event_type

            if etype == EventType.FILE_READ:
                path = event.data.get("path", "")
                files_read_set.add(path)
                if not first_write_seen:
                    read_before_edit = True

            elif etype == EventType.FILE_WRITE:
                if not first_write_seen:
                    first_write_seen = True
                if last_test_failed:
                    wrote_after_failure = True
                prev_was_test_cmd = False

            elif etype in (EventType.COMMAND_EXEC, EventType.TEST_RUN):
                cmd = event.data.get("command", "")
                is_test = (
                    etype == EventType.TEST_RUN
                    or any(kw in cmd for kw in _TEST_KEYWORDS)
                )
                if is_test:
                    test_run_count += 1
                    ran_tests_before_done = True
                    if wrote_after_failure:
                        iterated_on_failure = True
                    prev_was_test_cmd = True
                else:
                    prev_was_test_cmd = False

            elif etype == EventType.COMMAND_OUTPUT:
                if prev_was_test_cmd:
                    exit_code = event.data.get("exit_code", 0)
                    if exit_code != 0:
                        last_test_failed = True
                        wrote_after_failure = False
                    else:
                        last_test_failed = False
                        wrote_after_failure = False
                prev_was_test_cmd = False

            elif etype == EventType.AGENT_DONE:
                break

        explored_codebase = bool(files_read_set - highlight_set)

        return ProcessResult(
            read_before_edit=read_before_edit,
            ran_tests_before_done=ran_tests_before_done,
            iterated_on_failure=iterated_on_failure,
            explored_codebase=explored_codebase,
            test_run_count=test_run_count,
        )
