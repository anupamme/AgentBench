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
    from pathlib import Path

    from agentbench.core.task_loader import TaskLoader, TaskLoadError

    loader = TaskLoader()
    path = Path(task_path)

    try:
        task = loader.load_task(path)
        console.print(
            f"[green]✓ Valid task:[/green] {task.id} "
            f"({task.metadata.difficulty.value}, {task.metadata.task_type.value})"
        )
    except TaskLoadError as e:
        console.print(f"[red]✗ Validation failed for {path}:[/red]")
        for error in e.errors:
            console.print(f"  [red]• {error}[/red]")
        raise typer.Exit(code=1) from None


@app.command()
def scaffold(
    id: str = typer.Option(..., help="Task ID (kebab-case, e.g. fix-null-pointer-bug)"),
    task_type: str = typer.Option(..., "--type", help="Task type: bug_fix, feature_add, refactor, etc."),
    difficulty: str = typer.Option("medium", help="Difficulty: easy, medium, hard, expert"),
    language: str = typer.Option("python", help="Primary language: python or javascript"),
) -> None:
    """Create a new task from a template."""
    from agentbench.tools.scaffold_task import scaffold_task

    try:
        scaffold_task(id=id, task_type=task_type, difficulty=difficulty, language=language)
    except (ValueError, FileExistsError) as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=1) from None


@app.command(name="deep-validate")
def deep_validate(
    task_dir: str = typer.Argument(..., help="Path to task directory"),
) -> None:
    """Run deep validation on a task (requires Docker)."""
    import asyncio
    from pathlib import Path

    from rich.table import Table

    from agentbench.tools.validate_task import TaskValidator

    path = Path(task_dir)
    if not path.is_dir():
        console.print(f"[red]✗ Not a directory: {path}[/red]")
        raise typer.Exit(code=1)

    result = asyncio.run(TaskValidator().validate(path))

    table = Table(title=f"Validation: {result.task_id}", show_lines=True)
    table.add_column("Check", style="bold")
    table.add_column("Result", justify="center")
    table.add_column("Message")
    table.add_column("Duration", justify="right")

    for check in result.checks:
        status = "[green]✓ pass[/green]" if check.passed else "[red]✗ fail[/red]"
        duration = f"{check.duration_seconds:.2f}s" if check.duration_seconds else ""
        table.add_row(check.name, status, check.message, duration)

    console.print(table)

    if result.passed:
        console.print(f"\n[green]✓ All checks passed for {result.task_id}[/green]\n")
    else:
        console.print(f"\n[red]✗ Validation failed for {result.task_id}[/red]\n")
        raise typer.Exit(code=1)
