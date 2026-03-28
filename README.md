# AgentBench

[![CI](https://github.com/anupamme/AgentBench/actions/workflows/ci.yml/badge.svg)](https://github.com/anupamme/AgentBench/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/agentbench.svg)](https://badge.fury.io/py/agentbench)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## What is AgentBench?

AgentBench is an evaluation framework for agentic coding tools. Unlike benchmarks that test single-function completion, AgentBench measures how well agents handle realistic, multi-step coding workflows: navigating codebases, using tools iteratively, and fixing bugs by running tests and adapting to feedback.

Beyond pass/fail scores, AgentBench captures rich execution traces showing every tool call, file edit, and test run an agent makes. These traces power a failure taxonomy that identifies *why* an agent failed — context miss, wrong diagnosis, hallucinated API, ignored test failures, and more — giving you actionable data to improve your agent rather than just a number.

## Key Features

- **Rich execution traces** — every tool call, file read/write, test run, and token count recorded
- **Multi-dimensional scoring** — primary pass/fail plus secondary quality checks (lint, type check, diff size)
- **Failure taxonomy** — 10 failure categories with heuristic classification and confidence scores
- **Pluggable adapters** — built-in support for Anthropic API (including Bedrock) and Claude Code CLI; easy to add new ones
- **Reproducible sandboxes** — Docker-based isolated environments with configurable setup commands
- **Statistical comparison** — compare two agents across tasks with significance testing
- **50+ benchmark tasks** — spanning Python, JavaScript, Go, TypeScript across all difficulty levels

## Quick Start

```bash
pip install agentbench

# Run a single task
agentbench run --task calc-fix-division-by-zero --agent anthropic-api

# Run a full suite
agentbench run --suite quick-v1 --agent anthropic-api --model claude-sonnet-4-20250514

# Generate a report
agentbench report results/ --format table
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLI (Typer)                       │
│  run │ experiment │ report │ compare │ scaffold      │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────▼──────────────┐
         │        Orchestrator         │
         │  (parallel task dispatch)   │
         └──┬──────────────────────┬──┘
            │                      │
   ┌────────▼──────┐    ┌──────────▼────────┐
   │  Task Registry │    │   Agent Adapters   │
   │  (YAML tasks)  │    │ anthropic-api      │
   │  task_loader   │    │ claude-code        │
   └────────────────┘    │ mock (testing)     │
                         └──────────┬────────┘
                                    │
              ┌─────────────────────▼──────────────────┐
              │              Sandbox (Docker)            │
              │  isolated container per run              │
              └─────────────────────┬──────────────────┘
                                    │
         ┌──────────────────────────▼───────────────────┐
         │               Trace Collector                  │
         │  AGENT_START│TOOL_CALL│FILE_READ│TEST_RUN│...  │
         └──────────┬────────────────────────────────────┘
                    │
      ┌─────────────▼──────────────┐
      │       Scoring Pipeline      │
      │  primary + secondary evals  │
      └─────────────┬──────────────┘
                    │
      ┌─────────────▼──────────────┐
      │     Failure Classifier      │
      │  context_miss│halluc_api│…  │
      └─────────────┬──────────────┘
                    │
      ┌─────────────▼──────────────┐
      │      Reporting Engine       │
      │  table│markdown│comparison  │
      └────────────────────────────┘
```

## Task Format

Each task is a directory containing a `task.yaml` file:

```yaml
id: "calc-fix-division-by-zero"   # unique kebab-case ID
version: 1                         # schema version

metadata:
  difficulty: easy                 # easy | medium | hard | expert
  task_type: bug_fix               # see Task Types below
  languages: [python]
  estimated_human_time_minutes: 3
  tags: [python, beginner, error-handling]
  source: "synthetic"              # issue URL or "synthetic"

setup:
  repo: "tasks/calc-fix-division-by-zero/repo"  # local path or git URL
  commit: "HEAD"
  setup_commands:
    - "pip install pytest"
  files_to_highlight:              # hint files (not enforced)
    - "calc.py"
    - "tests/test_calc.py"

prompt: |
  The `divide()` function in `calc.py` crashes with a `ZeroDivisionError` when
  the divisor is zero. Fix it so that it raises a `ValueError` with the message
  "Cannot divide by zero" instead.

evaluation:
  primary:                         # must pass for overall_pass = True
    type: test_suite
    command: "python -m pytest tests/test_calc.py -v"
    pass_condition: "exit_code == 0"
  secondary:                       # quality signals (don't affect pass/fail)
    - type: lint
      command: "python -m py_compile calc.py"
      label: "syntax_valid"
    - type: diff_size
      max_lines_changed: 5
      label: "minimal_diff"

constraints:
  max_turns: 10
  max_tokens: 20000
  timeout_seconds: 60
  network: false
```

**Task Types:** `bug_fix`, `feature_add`, `refactor`, `test_generation`, `dependency_upgrade`, `debug_from_logs`, `multi_file_edit`, `code_review`, `documentation`, `performance`

## Running Evaluations

```bash
# Single task, default model
agentbench run --task calc-fix-division-by-zero --agent anthropic-api

# Full suite with specific model, 4 parallel workers
agentbench run --suite quick-v1 --agent anthropic-api \
  --model claude-sonnet-4-20250514 --parallelism 4

# Using AWS Bedrock
agentbench run --suite quick-v1 --agent anthropic-api \
  --model anthropic.claude-sonnet-4-20250514-v1:0 \
  --bedrock --aws-region us-east-1

# Multi-agent experiment from config
agentbench experiment --config experiments/example-comparison.yaml

# Report formats
agentbench report results/ --format table      # summary table
agentbench report results/ --format detail     # per-task details
agentbench report results/ --format markdown   # markdown report
agentbench report results/ --format failure    # failure analysis

# Compare with statistical testing
agentbench compare results/baseline/ results/candidate/

# Inspect a run trace
agentbench trace results/run-abc123/ --timeline
agentbench trace results/run-abc123/ --events TOOL_CALL,TEST_RUN
```

## Writing Your Own Tasks

Use the scaffold command to create a new task template:

```bash
agentbench scaffold --id my-new-task --type bug_fix \
  --difficulty medium --language python
```

This creates `tasks/my-new-task/` with a starter `task.yaml` and `repo/` directory. Edit the task YAML, add your broken code and tests in `repo/`, then validate:

```bash
agentbench validate tasks/my-new-task/task.yaml
agentbench deep-validate tasks/my-new-task/  # runs in Docker, checks tests pass
```

See [docs/task-authoring.md](docs/task-authoring.md) for the complete guide.

## Adding an Agent Adapter

Implement the `AgentAdapter` abstract base class:

```python
from agentbench.adapters.base import AgentAdapter, AgentConfig, AgentResult
from agentbench.core.models import TaskSpec
from agentbench.sandbox.manager import Sandbox, SandboxManager
from agentbench.trace.collector import TraceCollector
from agentbench.trace.events import EventType

class MyAgentAdapter(AgentAdapter):
    def name(self) -> str:
        return "my-agent"

    async def solve(
        self,
        task: TaskSpec,
        sandbox: Sandbox,
        sandbox_manager: SandboxManager,
        trace: TraceCollector,
    ) -> AgentResult:
        trace.record(EventType.AGENT_START, {"prompt": task.prompt})

        # Interact with your agent here...
        # Execute commands via sandbox_manager.exec(sandbox, command)
        # Record tool calls, file reads/writes to trace

        trace.record(EventType.AGENT_DONE, {"reason": "completed"})
        return AgentResult(
            completed=True,
            reason="completed",
            total_turns=5,
            total_tokens_used=1234,
            wall_clock_seconds=12.3,
        )
```

Register it in `src/agentbench/adapters/registry.py` and use `--agent my-agent` on the CLI.

See [docs/adapters.md](docs/adapters.md) for the complete guide.

## Failure Taxonomy

| Category | Description |
|---|---|
| `context_miss` | Agent didn't read the relevant files before editing |
| `wrong_diagnosis` | Agent misidentified the root cause; edited wrong files |
| `correct_plan_bad_execution` | Right files targeted but implementation is buggy |
| `hallucinated_api` | Agent used functions/methods that don't exist in the codebase |
| `incomplete_fix` | Partial fix — some tests pass but not all |
| `no_verification` | Agent didn't run tests before declaring done |
| `ignored_test_failure` | Agent saw test failures but declared done without iterating |
| `timeout_or_loop` | Agent got stuck in a loop or exceeded budget |
| `regression` | Fixed target tests but broke other previously-passing tests |
| `over_engineering` | Correct but unnecessarily complex; rewrote unrelated code |
| `unknown` | Doesn't match any known pattern |

See [docs/failure-taxonomy.md](docs/failure-taxonomy.md) for details and examples.

## Results & Reporting

Results are stored as JSON in the output directory. Each run produces:

```
results/
  run-<id>/
    result.json     # TaskRunResult with score, failure classification
    trace.json      # Full execution trace
```

**Table report** (`--format table`):
```
Task                          Agent          Pass  Score  Failure
calc-fix-division-by-zero     sonnet-4       ✓     1.00   —
flask-add-health-endpoint     sonnet-4       ✗     0.40   incomplete_fix
go-fix-goroutine-leak         sonnet-4       ✗     0.00   context_miss
```

**Comparison report** (`agentbench compare`):
```
Comparison: baseline vs candidate (12 tasks, 3 runs each)
Pass rate: 58.3% → 75.0% (+16.7pp, p=0.041 *)
```

## API Reference

All public classes and functions have docstrings. Key modules:

- `agentbench.core.models` — Pydantic models (`TaskSpec`, `TaskMetadata`, etc.)
- `agentbench.adapters.base` — `AgentAdapter`, `AgentConfig`, `AgentResult`
- `agentbench.trace.collector` — `TraceCollector`
- `agentbench.trace.events` — `EventType` enum
- `agentbench.classification.taxonomy` — `FailureCategory`, `FailureClassification`
- `agentbench.reporting.reporter` — `Reporter`

## Contributing

Contributions welcome! The highest-impact areas:

**Adding tasks** — create a task in `tasks/`, validate it with `agentbench deep-validate`, and open a PR. See [docs/task-authoring.md](docs/task-authoring.md).

**Adding adapters** — implement `AgentAdapter` for your tool. See [docs/adapters.md](docs/adapters.md).

**Improving scoring** — the scoring pipeline is in `src/agentbench/scoring/scorer.py`.

**Improving failure classification** — heuristic rules are in `src/agentbench/classification/classifier.py`.

Development setup:

```bash
git clone https://github.com/anupamme/AgentBench
cd AgentBench
pip install -e ".[dev]"
pytest tests/ -m "not docker"
```

## Citation

If you use AgentBench in your research, please cite:

```bibtex
@software{agentbench2026,
  title  = {AgentBench: An Evaluation Framework for Agentic Coding Tools},
  author = {Mediratta, Anupam},
  year   = {2026},
  url    = {https://github.com/anupamme/AgentBench},
}
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
