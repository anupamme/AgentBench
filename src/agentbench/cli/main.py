from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    name="agentbench",
    help="Eval framework for agentic coding tools",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    task: str | None = typer.Option(None, help="Single task ID to run"),
    suite: str | None = typer.Option(None, help="Task suite to run"),
    agent: str = typer.Option(..., help="Agent adapter to use"),
    model: str = typer.Option("claude-sonnet-4-20250514", help="Model to use"),
    parallelism: int = typer.Option(1, help="Number of parallel runs"),
    output: str = typer.Option("results/", help="Output directory"),
) -> None:
    """Run evaluation tasks against an agent."""
    console.print("[yellow]run command not yet implemented[/yellow]")


@app.command()
def experiment(
    config: str = typer.Option(..., help="Path to experiment YAML config"),
) -> None:
    """Run a multi-agent comparison experiment."""
    console.print("[yellow]experiment command not yet implemented[/yellow]")


@app.command()
def report(
    results_dir: str = typer.Argument(..., help="Path to results directory"),
    format: str = typer.Option("table", help="Output format: table, markdown, json"),
) -> None:
    """Generate a report from results."""
    console.print("[yellow]report command not yet implemented[/yellow]")


@app.command()
def compare(
    baseline: str = typer.Argument(..., help="Baseline results directory"),
    candidate: str = typer.Argument(..., help="Candidate results directory"),
) -> None:
    """Compare two result sets with statistical significance testing."""
    console.print("[yellow]compare command not yet implemented[/yellow]")


@app.command()
def trace(
    run_dir: str = typer.Argument(..., help="Path to a specific run directory"),
    events: str | None = typer.Option(None, help="Filter by event type"),
    timeline: bool = typer.Option(False, help="Show chronological timeline"),
) -> None:
    """Inspect the trace of a specific run."""
    console.print("[yellow]trace command not yet implemented[/yellow]")


@app.command()
def validate(
    task_path: str = typer.Argument(..., help="Path to task YAML to validate"),
) -> None:
    """Validate a task definition file."""
    console.print("[yellow]validate command not yet implemented[/yellow]")
