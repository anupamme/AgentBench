"""Classification package for AgentBench."""

from __future__ import annotations

from agentbench.classification.classifier import FailureClassifier
from agentbench.classification.taxonomy import FailureCategory, FailureClassification

__all__ = ["FailureCategory", "FailureClassification", "FailureClassifier"]
