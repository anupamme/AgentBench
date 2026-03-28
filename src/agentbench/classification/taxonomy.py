"""Failure taxonomy — categories of agent failure modes."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class FailureCategory(StrEnum):
    """Primary failure categories."""

    CONTEXT_MISS = "context_miss"
    # Agent didn't read the right files. Relevant files (from task spec's
    # files_to_highlight or known fix locations) not in trace's FILE_READ events.

    WRONG_DIAGNOSIS = "wrong_diagnosis"
    # Agent misidentified the root cause. Edited files unrelated to the known
    # fix location (if solution/ exists and can be diffed).

    CORRECT_PLAN_BAD_EXECUTION = "correct_plan_bad_execution"
    # Right files targeted but implementation is buggy. Agent edited the correct
    # files but tests still fail on those specific tests.

    HALLUCINATED_API = "hallucinated_api"
    # Agent used functions/methods/imports that don't exist in the codebase.
    # Detected by checking if new imports or function calls in the agent's edits
    # reference symbols not present in the original codebase.

    INCOMPLETE_FIX = "incomplete_fix"
    # Partial fix — some tests pass but not all. Partial score > 0 but < 1.0.

    NO_VERIFICATION = "no_verification"
    # Agent didn't run tests before declaring done. No TEST_RUN or test-like
    # COMMAND_EXEC events in the trace.

    IGNORED_TEST_FAILURE = "ignored_test_failure"
    # Agent ran tests, saw failures, but still declared done without iterating.
    # TEST_RUN with failures followed by AGENT_DONE without intervening FILE_WRITE.

    TIMEOUT_OR_LOOP = "timeout_or_loop"
    # Agent got stuck in a loop or ran out of budget. CONSTRAINT_HIT event
    # at the end of the trace.

    REGRESSION = "regression"
    # Fixed the target tests but broke other tests. Primary passes but
    # secondary full_suite fails.

    OVER_ENGINEERING = "over_engineering"
    # Correct but unnecessarily complex. Diff size >> expected (if diff_size
    # secondary exists and failed) or rewrote unrelated code.

    UNKNOWN = "unknown"
    # Doesn't match any known pattern.


@dataclass
class FailureClassification:
    """Result of failure classification for a single run."""

    primary_category: FailureCategory
    confidence: float  # 0.0–1.0, how confident we are in this classification
    evidence: list[str]  # Human-readable list of evidence supporting this classification
    # Additional applicable categories (may overlap)
    secondary_categories: list[FailureCategory] = field(default_factory=list)
