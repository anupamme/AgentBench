"""
Failure Classifier — assigns failure categories to failed task runs.

Uses heuristic rules applied in priority order. Each rule checks specific
conditions on the trace and score, and returns a classification if matched.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from agentbench.classification.taxonomy import FailureCategory, FailureClassification
from agentbench.trace.events import EventType, TraceEvent

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agentbench.core.models import TaskSpec
    from agentbench.scoring.models import TaskScore
    from agentbench.trace.collector import TraceCollector


class FailureClassifier:
    """Classifies failure modes from task scores and traces."""

    def classify(
        self,
        score: TaskScore,
        trace: TraceCollector,
        task: TaskSpec,
    ) -> FailureClassification | None:
        """
        Classify why an agent failed a task.

        Returns None if the task passed (score.overall_pass is True).

        Rules are applied in priority order. The first matching rule determines
        the primary category. Additional matching rules populate secondary_categories.

        Implemented rules in priority order (highest to lowest):
        1. TIMEOUT_OR_LOOP — trace ends with CONSTRAINT_HIT
        2. NO_VERIFICATION — no test run detected in trace
        3. IGNORED_TEST_FAILURE — ran tests, saw failure, declared done without iterating
        4. CONTEXT_MISS — none of files_to_highlight were read
        5. INCOMPLETE_FIX — partial_score > 0 but primary didn't pass
        6. REGRESSION — partial_score == 1.0 but a secondary full-suite check failed
        7. OVER_ENGINEERING — diff_size secondary failed
        8. UNKNOWN — fallback

        Not yet implemented (require solution diffing unavailable at runtime):
        - HALLUCINATED_API
        - WRONG_DIAGNOSIS
        - CORRECT_PLAN_BAD_EXECUTION
        """
        if score.overall_pass:
            return None

        events = trace.events
        evidence: list[str] = []
        matched: list[FailureCategory] = []

        # Rule 1: TIMEOUT_OR_LOOP
        if self._check_timeout_or_loop(events):
            matched.append(FailureCategory.TIMEOUT_OR_LOOP)
            evidence.append("Trace ends with a CONSTRAINT_HIT event")

        # Rule 2: NO_VERIFICATION
        if self._check_no_verification(events):
            matched.append(FailureCategory.NO_VERIFICATION)
            evidence.append("No test run detected in trace")

        # Rule 3: IGNORED_TEST_FAILURE
        if self._check_ignored_test_failure(events):
            matched.append(FailureCategory.IGNORED_TEST_FAILURE)
            evidence.append("Agent ran tests, saw failures, but didn't iterate")

        # Rule 4: CONTEXT_MISS
        if self._check_context_miss(events, task):
            matched.append(FailureCategory.CONTEXT_MISS)
            highlighted = task.setup.files_to_highlight
            read_files = self._get_files_read(events)
            missed = set(highlighted) - set(read_files)
            evidence.append(f"Agent didn't read highlighted files: {missed}")

        # Rule 5: INCOMPLETE_FIX (was rule 6 in original spec — HALLUCINATED_API not implemented)
        if self._check_incomplete_fix(score):
            matched.append(FailureCategory.INCOMPLETE_FIX)
            evidence.append(f"Partial score: {score.correctness.partial_score:.2f}")

        # Rule 6: REGRESSION (WRONG_DIAGNOSIS and CORRECT_PLAN_BAD_EXECUTION not implemented)
        if self._check_regression(score):
            matched.append(FailureCategory.REGRESSION)
            evidence.append(
                "All targeted tests pass (partial_score=1.0) but secondary full_suite fails"
            )

        # Rule 7: OVER_ENGINEERING (was rule 10 in original spec)
        if self._check_over_engineering(score):
            matched.append(FailureCategory.OVER_ENGINEERING)
            evidence.append(
                f"Diff size exceeds budget: {score.quality.diff_lines_changed} lines changed"
            )

        # Determine primary and secondary
        if not matched:
            return FailureClassification(
                primary_category=FailureCategory.UNKNOWN,
                confidence=0.3,
                evidence=["No heuristic rules matched"],
                secondary_categories=[],
            )

        primary = matched[0]
        secondary = matched[1:]
        confidence = min(0.9, 0.5 + 0.1 * len(evidence))

        return FailureClassification(
            primary_category=primary,
            confidence=confidence,
            evidence=evidence,
            secondary_categories=secondary,
        )

    # --- Heuristic rule implementations ---

    def _check_timeout_or_loop(self, events: Sequence[TraceEvent]) -> bool:
        """True if the last substantive event is CONSTRAINT_HIT."""
        for event in reversed(events):
            if event.event_type == EventType.CONSTRAINT_HIT:
                return True
            if event.event_type in (EventType.AGENT_DONE, EventType.ERROR):
                break
        return False

    def _check_no_verification(self, events: Sequence[TraceEvent]) -> bool:
        """True if no TEST_RUN events and no COMMAND_EXEC with test keywords."""
        test_keywords = ["pytest", "jest", "npm test", "npm run test", "go test", "cargo test"]
        for event in events:
            if event.event_type == EventType.TEST_RUN:
                return False
            if event.event_type == EventType.COMMAND_EXEC:
                cmd = event.data.get("command", "").lower()
                if any(kw in cmd for kw in test_keywords):
                    return False
        return True

    def _check_ignored_test_failure(self, events: Sequence[TraceEvent]) -> bool:
        """
        True if agent ran tests, got a failure, but declared done without
        editing any files after the failure.

        Look for the pattern:
        COMMAND_EXEC (test) → COMMAND_OUTPUT (exit_code != 0) → ... → AGENT_DONE
        with no FILE_WRITE events between the failed test and AGENT_DONE.
        """
        last_test_failed = False
        file_write_after_failure = False

        for event in events:
            if event.event_type == EventType.COMMAND_OUTPUT:
                exit_code = event.data.get("exit_code", 0)
                cmd_output = event.data.get("stdout", "") + event.data.get("stderr", "")
                # Check if this was a test command output
                test_keywords_out = ["passed", "failed", "error"]
                if exit_code != 0 and any(kw in cmd_output.lower() for kw in test_keywords_out):
                    last_test_failed = True
                    file_write_after_failure = False
            elif event.event_type == EventType.FILE_WRITE and last_test_failed:
                file_write_after_failure = True
                last_test_failed = False  # reset — they iterated

        return last_test_failed and not file_write_after_failure

    def _check_context_miss(self, events: Sequence[TraceEvent], task: TaskSpec) -> bool:
        """
        True if the agent didn't read any of the files_to_highlight.
        Only applies if files_to_highlight is non-empty.
        """
        highlighted = set(task.setup.files_to_highlight)
        if not highlighted:
            return False

        read_files = set(self._get_files_read(events))
        # Context miss if none of the highlighted files were read
        return len(highlighted & read_files) == 0

    def _check_incomplete_fix(self, score: TaskScore) -> bool:
        """True if partial_score > 0 but primary didn't pass."""
        return not score.correctness.primary_pass and score.correctness.partial_score > 0

    def _check_regression(self, score: TaskScore) -> bool:
        """True if all targeted tests pass (partial_score == 1.0) but a secondary suite fails.

        classify() is only called for failed tasks (primary_pass=False), so we cannot
        check primary_pass directly. partial_score == 1.0 serves as the proxy: it means
        every targeted test passed, yet the overall run still failed — most likely because
        a secondary full-suite check caught a regression introduced by the fix.
        """
        if score.correctness.partial_score < 1.0:
            return False
        for sr in score.correctness.secondary_results:
            if ("suite" in sr.label.lower() or "regression" in sr.label.lower()) and not sr.passed:
                return True
        return False

    def _check_over_engineering(self, score: TaskScore) -> bool:
        """True if diff_size secondary failed."""
        return not score.quality.diff_within_budget

    def _get_files_read(self, events: Sequence[TraceEvent]) -> list[str]:
        """Extract unique file paths from FILE_READ events."""
        paths = []
        for event in events:
            if event.event_type == EventType.FILE_READ:
                path = event.data.get("path", "")
                if path and path not in paths:
                    paths.append(path)
        return paths
