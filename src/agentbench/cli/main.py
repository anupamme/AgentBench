from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from agentbench import __version__

app = typer.Typer(
    name="agentbench",
    help="Eval framework for agentic coding tools",
    no_args_is_help=True,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"agentbench {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(  # noqa: UP007
        None, "--version", "-V", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


@app.command()
def run(
    task: str | None = typer.Option(None, help="Single task ID or path to task YAML"),
    suite: str | None = typer.Option(None, help="Suite name or path to suite YAML"),
    agent: str = typer.Option(..., help="Agent adapter name"),
    model: str = typer.Option("claude-sonnet-4-20250514", help="Model to use"),
    parallelism: int = typer.Option(1, help="Number of parallel runs"),
    output: str = typer.Option("results/", help="Output directory"),
    bedrock: bool = typer.Option(False, "--bedrock/--no-bedrock", help="Use AWS Bedrock"),
    aws_region: str | None = typer.Option(None, "--aws-region", help="AWS region for Bedrock"),
) -> None:
    """Run evaluation tasks against an agent."""
    import asyncio
    from pathlib import Path as P

    from agentbench.adapters.base import AgentConfig
    from agentbench.adapters.registry import get_adapter
    from agentbench.core.orchestrator import Orchestrator
    from agentbench.core.task_loader import TaskLoader, TaskLoadError

    loader = TaskLoader()

    # Load tasks
    if task:
        task_path = P(task)
        if task_path.suffix in (".yaml", ".yml"):
            try:
                tasks = [loader.load_task(task_path)]
            except TaskLoadError as e:
                console.print(f"[red]Failed to load task {task_path}:[/red]")
                for err in e.errors:
                    console.print(f"  [red]• {err}[/red]")
                raise typer.Exit(code=1) from None
        else:
            task_path = P("tasks") / task / "task.yaml"
            try:
                tasks = [loader.load_task(task_path)]
            except TaskLoadError as e:
                console.print(f"[red]Failed to load task '{task}':[/red]")
                for err in e.errors:
                    console.print(f"  [red]• {err}[/red]")
                raise typer.Exit(code=1) from None
    elif suite:
        suite_path = P(suite)
        if not suite_path.exists():
            suite_path = P("tasks/suites") / f"{suite}.yaml"
        if not suite_path.exists():
            suite_path = P("tasks/.suites") / f"{suite}.yaml"
        try:
            tasks = loader.load_suite(suite_path)
        except TaskLoadError as e:
            console.print(f"[red]Failed to load suite '{suite}':[/red]")
            for err in e.errors:
                console.print(f"  [red]• {err}[/red]")
            raise typer.Exit(code=1) from None
    else:
        console.print("[red]Must specify either --task or --suite[/red]")
        raise typer.Exit(code=1)

    # Create adapter
    extra: dict = {}
    if bedrock:
        extra["use_bedrock"] = True
    if aws_region:
        extra["aws_region"] = aws_region
    config = AgentConfig(model=model, extra=extra)
    try:
        adapter_instance = get_adapter(agent, config)
    except Exception as e:
        console.print(f"[red]Failed to load adapter '{agent}': {e}[/red]")
        raise typer.Exit(code=1) from None

    # Run
    orchestrator = Orchestrator(output_dir=P(output))
    results = asyncio.run(orchestrator.run_suite(tasks, adapter_instance, parallelism))

    # Print summary
    passed = sum(1 for r in results if r.score and r.score.overall_pass)
    total = len(results)
    console.print(f"\n[bold]Results: {passed}/{total} passed[/bold]")
    for r in results:
        status = "[green]✓[/green]" if (r.score and r.score.overall_pass) else "[red]✗[/red]"
        failure_info = ""
        if r.failure_classification:
            failure_info = f" [{r.failure_classification.primary_category.value}]"
        elif r.error:
            failure_info = f" [error: {r.error[:60]}]"
        console.print(f"  {status} {r.task_id}{failure_info}")


@app.command()
def experiment(
    config: str = typer.Option(..., help="Path to experiment YAML config"),
    output: str = typer.Option("results/", help="Output directory"),
) -> None:
    """Run a multi-agent comparison experiment."""
    import asyncio
    from pathlib import Path as P

    from agentbench.adapters.base import AgentConfig
    from agentbench.adapters.registry import get_adapter
    from agentbench.core.experiment import ExperimentConfig
    from agentbench.core.orchestrator import Orchestrator
    from agentbench.core.task_loader import TaskLoader, TaskLoadError

    config_path = P(config)
    if not config_path.exists():
        console.print(f"[red]Config file not found: {config_path}[/red]")
        raise typer.Exit(code=1)

    try:
        exp = ExperimentConfig.load(config_path)
    except Exception as e:
        console.print(f"[red]Failed to load experiment config: {e}[/red]")
        raise typer.Exit(code=1) from None

    loader = TaskLoader()
    suite_path = P(exp.suite)
    if not suite_path.exists():
        suite_path = P("tasks/suites") / f"{exp.suite}.yaml"
    if not suite_path.exists():
        suite_path = P("tasks/.suites") / f"{exp.suite}.yaml"
    try:
        tasks = loader.load_suite(suite_path)
    except TaskLoadError as e:
        console.print(f"[red]Failed to load suite '{exp.suite}':[/red]")
        for err in e.errors:
            console.print(f"  [red]• {err}[/red]")
        raise typer.Exit(code=1) from None

    console.print(f"[bold]Experiment: {exp.name}[/bold]")
    console.print(f"  Suite: {exp.suite} ({len(tasks)} tasks)")
    console.print(f"  Agents: {len(exp.agents)}, runs_per_task: {exp.runs_per_task}")

    all_results: dict[str, list] = {}

    for agent_cfg in exp.agents:
        agent_results = []
        agent_config = AgentConfig(
            model=agent_cfg.model,
            temperature=agent_cfg.temperature,
            max_tokens_per_response=agent_cfg.max_tokens_per_response,
            extra=agent_cfg.extra,
        )
        try:
            adapter_instance = get_adapter(agent_cfg.adapter, agent_config)
        except Exception as e:
            console.print(f"[red]Failed to load adapter '{agent_cfg.adapter}': {e}[/red]")
            continue

        orchestrator = Orchestrator(output_dir=P(output) / exp.name)

        for run_idx in range(exp.runs_per_task):
            if exp.runs_per_task > 1:
                console.print(
                    f"\n[cyan]Agent: {agent_cfg.name} — run {run_idx + 1}/{exp.runs_per_task}[/cyan]"
                )
            else:
                console.print(f"\n[cyan]Agent: {agent_cfg.name}[/cyan]")

            run_results = asyncio.run(
                orchestrator.run_suite(tasks, adapter_instance, exp.parallelism)
            )
            agent_results.extend(run_results)

        all_results[agent_cfg.name] = agent_results

    # Print aggregate summary
    console.print("\n[bold]Experiment Summary[/bold]")
    for agent_name, results in all_results.items():
        passed = sum(1 for r in results if r.score and r.score.overall_pass)
        total = len(results)
        console.print(f"  {agent_name}: {passed}/{total} passed")


@app.command()
def report(
    results_dir: str = typer.Argument(..., help="Path to results directory"),
    format: str = typer.Option("table", help="Output format: table, detail, markdown, failure"),
) -> None:
    """Generate a report from results."""
    from pathlib import Path as P

    from agentbench.reporting.data import ExperimentData
    from agentbench.reporting.reporter import Reporter

    data = ExperimentData.load(P(results_dir))
    if not data.runs:
        console.print(f"[yellow]No runs found in {results_dir}[/yellow]")
        raise typer.Exit(code=1)

    reporter = Reporter(console)

    if format == "table":
        reporter.summary_table(data)
    elif format == "detail":
        reporter.detail_table(data)
    elif format == "markdown":
        console.print(reporter.markdown_report(data))
    elif format == "failure":
        reporter.failure_report(data)
    else:
        console.print(f"[red]Unknown format '{format}'. Use: table, detail, markdown, failure[/red]")
        raise typer.Exit(code=1)


@app.command()
def compare(
    baseline: str = typer.Argument(..., help="Baseline results directory"),
    candidate: str = typer.Argument(..., help="Candidate results directory"),
) -> None:
    """Compare two result sets with statistical significance testing."""
    from pathlib import Path as P

    from agentbench.reporting.comparison import ComparisonEngine
    from agentbench.reporting.data import ExperimentData

    baseline_data = ExperimentData.load(P(baseline))
    candidate_data = ExperimentData.load(P(candidate))
    engine = ComparisonEngine()
    result = engine.compare(baseline_data, candidate_data)
    engine.print_comparison(result, console)


@app.command()
def trace(
    run_dir: str = typer.Argument(..., help="Path to a specific run directory"),
    events: str | None = typer.Option(None, help="Filter by event type (comma-separated)"),
    timeline: bool = typer.Option(False, help="Show chronological timeline"),
) -> None:
    """Inspect the trace of a specific run."""
    from pathlib import Path as P

    from agentbench.trace.collector import TraceCollector

    trace_path = P(run_dir) / "trace.json"
    if not trace_path.exists():
        console.print(f"[red]No trace.json found in {run_dir}[/red]")
        raise typer.Exit(code=1)

    loaded_trace = TraceCollector.load(trace_path)

    if timeline:
        console.print(loaded_trace.to_timeline())
    else:
        summary = loaded_trace.summary()
        console.print(f"[bold]Trace: {loaded_trace.run_id}[/bold]")
        console.print(f"  Task: {loaded_trace.task_id}")
        console.print(f"  Agent: {loaded_trace.agent_name}")
        console.print(f"  Events: {summary.total_events}")
        console.print(f"  Tokens: {summary.total_tokens}")
        console.print(f"  Duration: {summary.wall_clock_seconds:.1f}s")

        if events:
            from agentbench.trace.events import EventType
            filter_types = {EventType(e.strip()) for e in events.split(",")}
            filtered = [ev for ev in loaded_trace.events if ev.event_type in filter_types]
            for ev in filtered:
                console.print(f"  [{ev.sequence_number}] {ev.event_type.value}: {ev.data}")


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
