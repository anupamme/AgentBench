"""Markdown report generation for AgentBench results.

Uses Jinja2 templates to produce structured markdown documents
suitable for GitHub READMEs, blog posts, or documentation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


class MarkdownReporter:
    """Generates markdown reports from stored results."""

    def __init__(self) -> None:
        """Initialize with Jinja2 template environment.

        Templates are loaded from src/agentbench/reporting/templates/.
        """
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Register custom filters
        self.env.filters["format_pct"] = lambda v: f"{float(v) * 100:.1f}%"
        self.env.filters["format_tokens"] = lambda v: f"{float(v):,.0f}"

    def generate_suite_report(self, experiment_summary: dict[str, Any]) -> str:
        """Generate a full suite/experiment report in markdown.

        Template: templates/suite_report.md.j2

        Sections: Summary, Results by Difficulty, Results by Task Type,
        Failure Analysis, Efficiency Comparison, Per-Task Results.

        Returns: Complete markdown string.
        """
        template = self.env.get_template("suite_report.md.j2")
        return str(template.render(s=experiment_summary))

    def generate_comparison_report(
        self,
        comparison: dict[str, Any],
        exp_a_summary: dict[str, Any],
        exp_b_summary: dict[str, Any],
    ) -> str:
        """Generate a comparison report between two experiments.

        Template: templates/comparison_report.md.j2

        Sections: Overview, Pass Rate Changes, Task Flips,
        Failure Distribution Changes, Unique Solves.

        Returns: Complete markdown string.
        """
        template = self.env.get_template("comparison_report.md.j2")
        return str(template.render(cmp=comparison, a=exp_a_summary, b=exp_b_summary))

    def save(self, content: str, output_path: Path) -> None:
        """Save markdown content to a file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
