# AgentBench Design and Architecture

## Overview

AgentBench evaluates agentic coding tools on realistic software engineering tasks. It orchestrates a pipeline that: provisions an isolated Docker sandbox, runs an agent adapter against a task, captures a full execution trace, scores the result, classifies any failures, and stores everything to disk for offline analysis and reporting.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (Typer)                          │
│  run  experiment  report  compare  trace  validate  scaffold │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ Orchestrator │  asyncio.Semaphore for parallelism
                    └──────┬───────┘
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼──────────┐
   │  Task Loader │  │   Sandbox   │  │  Agent Adapter  │
   │  (task.yaml) │  │   Manager   │  │  (anthropic-api │
   │  → TaskSpec  │  │  (Docker)   │  │   claude-code   │
   └─────────────┘  └──────┬───────┘  │   mock)        │
                           │          └────────┬────────┘
                    ┌──────▼──────┐           │
                    │   Sandbox   │◄──commands─┘
                    │  Container  │
                    └──────┬───────┘
                           │ events
                    ┌──────▼──────┐
                    │   Trace     │
                    │  Collector  │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼──────────┐
   │   Scorer    │  │  Failure    │  │  Run Storage   │
   │  (eval cmds │  │ Classifier  │  │  (results/)    │
   │  in sandbox)│  │ (heuristics)│  └────────────────┘
   └─────────────┘  └─────────────┘
          │
   ┌──────▼──────┐
   │  Reporting  │
   │  Engine     │
   └─────────────┘
```

## Component Descriptions

### CLI (`src/agentbench/cli/main.py`)

Typer-based command-line interface. Commands:

| Command | Description |
|---|---|
| `run` | Run one task with one agent |
| `experiment` | Run a full experiment from a YAML config |
| `report` | Generate reports from results directory |
| `compare` | Statistical comparison between two agents |
| `trace` | Inspect execution traces interactively |
| `validate` | Check task YAML schema |
| `deep-validate` | Full Docker-based task validation |
| `scaffold` | Generate a new task directory skeleton |

### Orchestrator (`src/agentbench/core/orchestrator.py`)

Coordinates the 10-step evaluation pipeline for a single run (see Data Flow below). `run_suite()` wraps `run_single()` with `asyncio.Semaphore`-based parallelism and a `rich.progress` bar.

### Task Loader (`src/agentbench/core/task_loader.py`)

Discovers `task.yaml` files in the `tasks/` directory tree, parses them with PyYAML, and validates against the `TaskSpec` Pydantic model. Resolves suite references (e.g., `quick-v1`) by reading `tasks/.suites/<name>.yaml` to get the list of task IDs.

### Task Models (`src/agentbench/core/models.py`)

Pydantic v2 models that are the schema source of truth: `TaskSpec`, `TaskMetadata`, `TaskSetup`, `TaskEvaluation`, `EvalCriterion`, `Constraints`. Field-level validation (regex patterns, range checks, cross-field validators) is enforced here.

### Agent Adapters (`src/agentbench/adapters/`)

Pluggable backends for different agentic tools. The `AgentAdapter` ABC (`base.py`) defines two abstract methods:

- `name() -> str` — returns the adapter's identifier (e.g., `"anthropic-api"`)
- `async solve(task, sandbox, sandbox_manager, trace) -> AgentResult` — runs the agent's interaction loop

Built-in adapters:

| Adapter | File | Description |
|---|---|---|
| `anthropic-api` | `anthropic_api.py` | Calls the Anthropic Messages API directly; supports Bedrock |
| `claude-code` | `claude_code.py` | Spawns the `claude` CLI as a subprocess |
| `mock` | `mock.py` | Deterministic fake for unit testing |

`registry.py` maps adapter name strings to classes, used by the CLI and experiment runner.

### Sandbox Manager (`src/agentbench/sandbox/manager.py`)

Wraps the Docker Python SDK. `session(task)` is an async context manager that creates an isolated container for the task's repo, runs `setup_commands`, and tears down automatically on exit. `execute(sandbox, command)` runs a shell command inside the container and returns stdout, stderr, and exit code. `snapshot_diff(sandbox)` returns a unified diff of all changes made to the workspace.

### Trace Collector (`src/agentbench/trace/collector.py`)

In-memory event log for a single run. `record(event_type, data, ...)` appends a `TraceEvent` with automatic UTC timestamps and auto-incrementing sequence numbers. `new_turn()` advances the turn counter (used to group events per agent interaction). `save(path)` serializes to JSON. See Trace Format below.

### Scorer (`src/agentbench/scoring/scorer.py`)

After the agent finishes, runs the task's `evaluation.primary` and `evaluation.secondary` commands inside the (still-live) sandbox. Returns a `TaskScore` with `overall_pass` (bool) and per-criterion `ScoreResult` objects. Timeouts are enforced per criterion.

### Failure Classifier (`src/agentbench/classification/classifier.py`)

Heuristic rule engine. Takes `(TaskScore, TraceCollector, TaskSpec)` and returns a `FailureClassification` with a `FailureCategory`, evidence strings, and a confidence score. The 10 categories are defined in `src/agentbench/classification/taxonomy.py`. See [`docs/failure-taxonomy.md`](failure-taxonomy.md) for the full reference.

### Run Storage (`src/agentbench/core/results.py`)

Manages the on-disk layout for a single run:

```
results/<experiment-name>/<task-id>/<agent-name>/<run-id>/
  trace.json      # full execution trace
  result.json     # AgentResult (completion status, turns, tokens, timing)
  diff.patch      # unified diff of workspace changes
  metadata.json   # task spec + agent config snapshot
  score.json      # TaskScore + FailureClassification
```

### Reporting Engine (`src/agentbench/reporting/`)

Reads result directories and produces formatted output:

| Module | Description |
|---|---|
| `reporter.py` | Main orchestrator; dispatches to formatters |
| `data.py` | Aggregates raw results into `ReportData` |
| `terminal.py` | Rich-based tables and progress displays |
| `markdown.py` | Markdown report formatter |
| `comparison.py` | Statistical comparison with Fisher's exact test |
| `trace_viewer.py` | Interactive trace timeline viewer |

## Data Flow: Single Run

The following describes what happens when `agentbench run --task calc-fix-division-by-zero --agent anthropic-api` is executed:

1. **CLI parses arguments** → looks up `"anthropic-api"` in `AdapterRegistry`, instantiates `AnthropicAPIAdapter` with default `AgentConfig`.

2. **TaskLoader.load("calc-fix-division-by-zero")** → reads `tasks/calc-fix-division-by-zero/task.yaml`, validates against `TaskSpec` schema, returns a `TaskSpec` object.

3. **Orchestrator.run_single(task, adapter)** is called.

4. **run_id generated** → `"run-<12 hex chars>"` via `uuid4().hex[:12]`.

5. **SandboxManager.session(task)** → Docker creates a container from the task's Dockerfile (or `python:3.12-slim` default), mounts `tasks/calc-fix-division-by-zero/repo/` as `/workspace`, runs `setup_commands` (e.g., `pip install -e .`).

6. **TraceCollector initialized** with `run_id`, `task_id`, `agent_name`.

7. **adapter.solve(task, sandbox, sandbox_manager, trace)** called:
   - Records `AGENT_START` event to trace
   - Sends task prompt to the Anthropic Messages API
   - In a loop: receives model response → executes tool calls (bash commands, file edits) in the sandbox → records `TOOL_CALL`, `TOOL_RESULT`, `FILE_READ`, `FILE_WRITE`, `COMMAND_EXEC`, etc. events → feeds results back to the model → checks constraints (turns, tokens, timeout)
   - Records `AGENT_DONE` or `CONSTRAINT_HIT` event
   - Returns `AgentResult`

8. **Scorer.score(task, sandbox, ...)** → runs `pytest tests/test_calc.py::test_divide_by_zero -v` inside the sandbox, captures exit code, returns `TaskScore(overall_pass=True/False, ...)`.

9. **FailureClassifier.classify(score, trace, task)** → if failed, analyzes trace events and returns a `FailureClassification` (e.g., category `WRONG_APPROACH`, confidence 0.8).

10. **SandboxManager.snapshot_diff(sandbox)** → returns unified diff of all changes to `/workspace`.

11. **RunStorage writes outputs** → `trace.json`, `result.json`, `diff.patch`, `metadata.json`, `score.json` to `results/<run-id>/`.

12. **Sandbox torn down** → container removed.

13. **CLI displays result** via `terminal.py` formatter.

## Trace Format Specification

Each run produces a `trace.json` file with the following structure:

```json
{
  "run_id": "run-a1b2c3d4e5f6",
  "task_id": "calc-fix-division-by-zero",
  "agent_name": "anthropic-api",
  "event_count": 12,
  "summary": {
    "total_tokens": 8420,
    "total_tool_calls": 4,
    "wall_clock_seconds": 18.3
  },
  "events": [
    {
      "timestamp": "2026-03-28T14:23:01.123456+00:00",
      "event_type": "agent_start",
      "data": { "task_id": "calc-fix-division-by-zero" },
      "duration_ms": 0,
      "sequence_number": 0,
      "turn_number": 0
    },
    {
      "timestamp": "2026-03-28T14:23:03.456789+00:00",
      "event_type": "tool_call",
      "data": { "tool": "bash", "command": "cat src/calc.py" },
      "duration_ms": 120,
      "sequence_number": 1,
      "turn_number": 1,
      "token_usage": {
        "input_tokens": 800,
        "output_tokens": 45,
        "thinking_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "total_tokens": 845
      }
    }
  ]
}
```

### Event Types

All valid `event_type` values (from `EventType` StrEnum in `src/agentbench/trace/events.py`):

| Value | Category | Description |
|---|---|---|
| `agent_thinking` | Reasoning | Model reasoning/planning output (extended thinking) |
| `agent_message` | Reasoning | Agent's conversational message |
| `tool_call` | Tool usage | Agent invoked a tool |
| `tool_result` | Tool usage | Tool returned a result |
| `file_read` | File ops | Agent read a file |
| `file_write` | File ops | Agent created or modified a file |
| `file_create` | File ops | Agent created a new file |
| `file_delete` | File ops | Agent deleted a file |
| `command_exec` | Shell ops | Agent executed a shell command |
| `command_output` | Shell ops | Output from a shell command |
| `search` | Navigation | Agent searched for content |
| `directory_list` | Navigation | Agent listed directory contents |
| `test_run` | Tests | Agent ran a test suite |
| `test_result` | Tests | Test suite results |
| `agent_start` | Lifecycle | Agent began working on the task |
| `agent_done` | Lifecycle | Agent signaled completion |
| `error` | Lifecycle | An error occurred |
| `constraint_hit` | Lifecycle | A constraint was hit (timeout, token limit, turn limit) |

`token_usage` is optional and only present on events where the adapter provided API usage data (typically `tool_call` events with full API responses).

## Failure Taxonomy Reference

When a task fails, the classifier assigns one of 10 failure categories:

| Category | Description |
|---|---|
| `wrong_approach` | Agent pursued a fundamentally incorrect strategy |
| `incomplete_fix` | Partial fix — some tests pass but not all |
| `introduced_regression` | Fix broke previously passing tests |
| `gave_up` | Agent explicitly stopped without a solution |
| `constraint_exceeded` | Ran out of turns, tokens, or time |
| `tool_failure` | Repeated tool errors blocked progress |
| `misread_task` | Agent misunderstood the task requirements |
| `environment_error` | Sandbox setup or dependency failures |
| `flaky_test` | Test is non-deterministic (task quality issue) |
| `unknown` | Could not determine a specific failure reason |

See [`docs/failure-taxonomy.md`](failure-taxonomy.md) for the full reference with examples and heuristics.
