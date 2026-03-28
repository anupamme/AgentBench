# Tasks

This directory contains all benchmark tasks for AgentBench. For a comprehensive authoring guide, see [`docs/task-authoring.md`](../docs/task-authoring.md).

## Quick Start

```bash
# Scaffold a new task
agentbench scaffold --id my-task --type bug_fix --difficulty medium --language python

# Validate the task YAML schema
agentbench validate tasks/my-task/task.yaml

# Full validation: build sandbox, run setup, confirm primary eval fails on unmodified code
agentbench deep-validate tasks/my-task/
```

## Directory Layout

Each task is a self-contained directory:

```
tasks/<task-id>/
  task.yaml        # required — full task specification
  repo/            # required — the broken/incomplete codebase
  solution/        # optional — reference solution for deep-validate
```

Suite definitions live in:

```
tasks/.suites/
  quick-v1.yaml    # ~10 fast tasks for smoke testing
  standard-v1.yaml # full benchmark suite
```

## YAML Schema Reference

The schema is enforced by `TaskSpec` in `src/agentbench/core/models.py`.

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique kebab-case identifier matching `^[a-z0-9][a-z0-9\-]{2,80}$` |
| `version` | int (≥1) | yes | Schema version for forward compatibility |
| `metadata` | object | yes | Task metadata (see below) |
| `setup` | object | yes | Sandbox setup (see below) |
| `prompt` | string | yes | The task description given to the agent (≥10 chars) |
| `evaluation` | object | yes | Evaluation criteria (see below) |
| `constraints` | object | no | Runtime constraints with defaults (see below) |

### `metadata`

| Field | Type | Required | Description |
|---|---|---|---|
| `difficulty` | enum | yes | `easy`, `medium`, `hard`, `expert` |
| `task_type` | enum | yes | See Task Types below |
| `languages` | list[str] | yes | Programming languages involved (at least one) |
| `estimated_human_time_minutes` | int | yes | How long a senior engineer would take |
| `tags` | list[str] | no | Free-form tags for filtering |
| `source` | string | yes | `"synthetic"` or an issue/PR URL |

**Task Types:** `bug_fix`, `feature_add`, `refactor`, `test_generation`, `dependency_upgrade`, `debug_from_logs`, `multi_file_edit`, `code_review`, `documentation`, `performance`

**Difficulty calibration:**

| Level | `estimated_human_time_minutes` | Characteristics |
|---|---|---|
| `easy` | 2–10 | Single-file, obvious fix, clear test failure message |
| `medium` | 10–30 | 1–3 files, requires reading related code, moderate reasoning |
| `hard` | 30–90 | Multi-file, non-obvious root cause, requires understanding architecture |
| `expert` | 90+ | Deep domain knowledge, subtle bugs, or large refactors |

### `setup`

| Field | Type | Required | Description |
|---|---|---|---|
| `repo` | string | yes | Git repo URL or local path to repo snapshot |
| `commit` | string | yes | Git commit hash to checkout (`"HEAD"` for local repos) |
| `dockerfile` | string | no | Path to custom Dockerfile relative to task directory |
| `setup_commands` | list[str] | no | Shell commands run before the agent starts |
| `files_to_highlight` | list[str] | no | Hint files for context (informational only, not enforced) |

### `evaluation`

| Field | Type | Required | Description |
|---|---|---|---|
| `primary` | EvalCriterion | yes | The main pass/fail check |
| `secondary` | list[EvalCriterion] | no | Additional quality checks (e.g., lint, diff size) |

**EvalCriterion fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `type` | enum | — | `test_suite`, `lint`, `type_check`, `diff_size`, `custom_script` |
| `command` | string | — | Shell command to run (required for all types except `diff_size`) |
| `pass_condition` | string | — | `"exit_code == 0"` (only supported condition) |
| `max_lines_changed` | int | — | For `diff_size` only: maximum lines changed |
| `label` | string | `""` | Human-readable label for reports |
| `timeout_seconds` | int | 300 | Per-criterion timeout |

### `constraints`

| Field | Type | Default | Description |
|---|---|---|---|
| `max_turns` | int | 50 | Maximum agent interaction turns |
| `max_tokens` | int | 200000 | Total token budget (input + output combined) |
| `timeout_seconds` | int | 600 | Wall clock time limit |
| `network` | bool | false | Whether the agent has internet access |

### Complete annotated example

```yaml
id: "calc-fix-division-by-zero"
version: 1

metadata:
  difficulty: easy
  task_type: bug_fix
  languages: ["python"]
  estimated_human_time_minutes: 5
  tags: ["arithmetic", "exception-handling"]
  source: "synthetic"

setup:
  repo: "./repo"
  commit: "HEAD"
  setup_commands:
    - "pip install -e ."
  files_to_highlight:
    - "src/calc.py"      # where the symptom appears
    # NOT "src/calc.py" line 42 — don't reveal the fix location

prompt: |
  The `divide()` function in `src/calc.py` raises `ZeroDivisionError` when the
  divisor is zero. The test `test_divide_by_zero` in `tests/test_calc.py` is
  currently failing. Fix the function to raise `ValueError('Cannot divide by zero')`
  instead.

evaluation:
  primary:
    type: test_suite
    # Target the specific test, not the whole suite
    command: "pytest tests/test_calc.py::test_divide_by_zero -v"
    pass_condition: "exit_code == 0"
    label: "ZeroDivisionError test"
    timeout_seconds: 60
  secondary:
    - type: lint
      command: "ruff check src/"
      pass_condition: "exit_code == 0"
      label: "Ruff lint"
    - type: diff_size
      max_lines_changed: 10
      label: "Small diff (≤10 lines)"

constraints:
  max_turns: 10       # easy task — should be done quickly
  max_tokens: 50000
  timeout_seconds: 120
  network: false
```

## Step-by-Step: Creating a New Task

1. **Scaffold the directory structure:**
   ```bash
   agentbench scaffold --id my-task --type bug_fix --difficulty medium --language python
   ```

2. **Add broken code to `repo/`:**
   - Copy or create the codebase with the bug/incomplete feature already present
   - Include a failing test that captures the expected behavior
   - Ensure tests run with a standard command (e.g., `pytest tests/`)

3. **Write the prompt** — be specific about the observable failure, name the failing test, don't reveal the solution.

4. **Configure `evaluation.primary`** with the specific test command that targets your failing test.

5. **Set constraints** appropriate to the difficulty level (see calibration table above).

6. **Validate:**
   ```bash
   agentbench validate tasks/my-task/task.yaml   # schema check
   agentbench deep-validate tasks/my-task/       # full Docker validation
   ```

7. **Optionally add a `solution/` directory** with the reference fix — `deep-validate` will verify it makes the primary eval pass.

## Quality Checklist

Before opening a PR with a new task:

- [ ] `id` is unique across all tasks and matches `^[a-z0-9][a-z0-9\-]{2,80}$`
- [ ] `agentbench validate` passes without errors
- [ ] `agentbench deep-validate` passes (primary eval **fails** on unmodified repo)
- [ ] `solution/` makes the primary eval pass (if provided)
- [ ] Primary eval command is specific (not `pytest tests/` — use `pytest tests/test_foo.py::test_bar`)
- [ ] All tests are deterministic (no timing-dependent or flaky tests)
- [ ] `files_to_highlight` contains only symptom files, not solution files
- [ ] `setup_commands` work in a clean Docker container (no local env dependencies)
- [ ] `pass_condition: "exit_code == 0"` is set on all `test_suite`, `lint`, and `type_check` criteria
- [ ] Difficulty calibration: `estimated_human_time_minutes` is in the correct range for the level
- [ ] Prompt reads like a real issue description, not a homework assignment

## Representative Examples

**Easy Python bug fix** — `calc-fix-division-by-zero/`: Single file, single test, obvious failure message. Good for verifying the basic pipeline works. The primary eval targets one specific test case so there's no ambiguity.

**Medium multi-file task** — `py-multi-add-model-routes/`: Requires reading multiple modules to understand the data model before adding a new API route. Represents realistic feature-add work that touches both model layer and route layer.

**Go sandbox** — `go-fix-goroutine-leak/`: Demonstrates non-Python task setup. Uses a Go base image, runs `go test ./...` as the primary eval. Shows how `dockerfile` can point to a language-specific image.

---

For the full guide including best practices and common pitfalls, see [`docs/task-authoring.md`](../docs/task-authoring.md).
