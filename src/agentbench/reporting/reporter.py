"""
Reporting Engine — generates human-readable reports from eval results.

Supports terminal tables, markdown reports, and JSON export.
Includes comparison mode with statistical significance testing.
"""
from __future__ import annotations


class Reporter:
    """Generates reports from evaluation results."""

    def generate(self, results_dir: str, format: str = "table") -> str:
        raise NotImplementedError

    def compare(self, baseline_dir: str, candidate_dir: str) -> str:
        raise NotImplementedError
