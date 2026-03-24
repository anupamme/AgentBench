"""
Scoring Pipeline — evaluates agent outputs across multiple dimensions.

Dimensions: functional correctness, code quality, efficiency, process quality.
"""
from __future__ import annotations


class Scorer:
    """Multi-dimensional scoring for completed task runs."""

    async def score(self, sandbox: object, eval_spec: object, trace: object) -> dict:
        raise NotImplementedError
