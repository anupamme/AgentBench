"""
Failure Classifier — categorizes why an agent failed a task.

Uses heuristic rules applied to traces and scores to assign failure
categories like context_miss, hallucinated_api, no_verification, etc.
"""
from __future__ import annotations


class FailureClassifier:
    """Classifies failure modes from task scores and traces."""

    def classify(self, score: object, trace: object, task: object) -> str | None:
        raise NotImplementedError
