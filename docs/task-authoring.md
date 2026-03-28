# Task Authoring Guide

This guide explains how to create high-quality benchmark tasks for AgentBench.

## Quick Start

```bash
agentbench scaffold --id my-task --type bug_fix --difficulty medium --language python
agentbench validate tasks/my-task/task.yaml
agentbench deep-validate tasks/my-task/
```

## Task YAML Schema Reference

Every task is a directory with a `task.yaml` file. The schema is defined by `TaskSpec` in `src/agentbench/core/models.py`.

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique kebab-case identifier matching `^[a-z0-9][a-z0-9\-]{2,80}$` |
| `version` | int (≥1) | yes | Schema version for forward compatibility |
| `metadata` | object | yes | Task metadata (see below) |
| `setup` | object | yes | Sandbox setup (see below) |
| `prompt` | string | yes | The task description given to the agent (≥10 chars) |
| `evaluation` | object | yes | Evaluation criteria (see below) |
| `constraints` | object | no | Runtime constraints (defaults apply) |

### `metadata`

| Field | Type | Required | Description |
|---|---|---|---|
| `difficulty` | enum | yes | `easy`, `medium`, `hard`, `expert` |
| `task_type` | enum | yes | See Task Types below |
| `languages` | list[str] | yes | Programming languages involved (at least one) |
| `estimated_human_time_minutes` | int | yes | How long a senior engineer would take |
| `tags` | list[str] | no | Free-form tags for filtering |
| `source` | string | yes | `"synthetic"` or an issue/PR URL |

**Task Types:**
- `bug_fix` — fix a broken function or behavior
- `feature_add` — implement a new feature
- `refactor` — restructure code without changing behavior
- `test_generation` — write tests for existing code
- `dependency_upgrade` — update a dependency and fix breaking changes
- `debug_from_logs` — diagnose and fix an issue from log output
- `multi_file_edit` — change that spans multiple files
- `code_review` — identify and fix issues in a code review scenario
- `documentation` — write or update docs/docstrings
- `performance` — optimize for speed or memory

### `setup`

| Field | Type | Required | Description |
|---|---|---|---|
| `repo` | string | yes | Git repo URL or local path to repo snapshot |
| `commit` | string | yes | Git commit hash to checkout (`"HEAD"` for local repos) |
| `dockerfile` | string | no | Path to custom Dockerfile relative to task directory |
| `setup_commands` | list[str] | no | Shell commands run before the agent starts |
| `files_to_highlight` | list[str] | no | Hint files for context (not enforced, informational only) |

### `evaluation`

| Field | Type | Required | Description |
|---|---|---|---|
| `primary` | EvalCriterion | yes | The main pass/fail check |
| `secondary` | list[EvalCriterion] | no | Additional quality checks |

**EvalCriterion fields:**

| Field | Type | Description |
|---|---|---|
| `type` | enum | `test_suite`, `lint`, `type_check`, `diff_size`, `custom_script` |
| `command` | string | Shell command to run (required for all types except `diff_size`) |
| `pass_condition` | string | `"exit_code == 0"` (currently only supported condition) |
| `max_lines_changed` | int | For `diff_size` only: maximum lines changed |
| `label` | string | Human-readable label for reports |
| `timeout_seconds` | int | Timeout for this criterion (default: 300) |

### `constraints`

| Field | Type | Default | Description |
|---|---|---|---|
| `max_turns` | int | 50 | Maximum agent interaction turns |
| `max_tokens` | int | 200000 | Total token budget (input + output combined) |
| `timeout_seconds` | int | 600 | Wall clock time limit |
| `network` | bool | false | Whether the agent has internet access |

## Best Practices for Writing Prompts

**Be specific about the failure mode.** Instead of "fix the bug in calc.py", write "The `divide()` function raises `ZeroDivisionError` when the divisor is zero. Fix it to raise `ValueError('Cannot divide by zero')` instead."

**Name the test that should pass.** "The test `test_divide_by_zero` in `tests/test_calc.py` should pass after your fix." This gives the agent a concrete verification target.

**Avoid giving away the solution.** Don't say "add an `if b == 0` check". Describe the observable behavior you want, not the implementation.

**Include relevant context clues.** If the fix requires understanding a related module, mention it exists: "The `utils.py` module has helper functions you may find useful."

**Keep it realistic.** Prompts should read like a real issue description or code review comment, not a homework assignment.

## How to Calibrate Difficulty

| Level | `estimated_human_time_minutes` | Characteristics |
|---|---|---|
| `easy` | 2–10 | Single-file, obvious fix, clear test failure message |
| `medium` | 10–30 | 1–3 files, requires reading related code, moderate reasoning |
| `hard` | 30–90 | Multi-file, non-obvious root cause, requires understanding architecture |
| `expert` | 90+ | Deep domain knowledge, subtle bugs, or large refactors |

**Signs a task is too easy for its label:** An agent solves it in 1–2 turns without reading any context files.

**Signs a task is too hard for its label:** No agent solves it across many runs; the fix requires knowledge not available in the codebase.

## Common Pitfalls

**Flaky tests** — If your test sometimes passes and sometimes fails non-deterministically, it will produce unreliable evaluation results. Use deterministic test data and avoid timing-dependent tests.

**Too much in `files_to_highlight`** — If you list every relevant file, you've made a hard task easy. List only the files the agent needs to understand the symptom, not the solution.

**Ambiguous primary criterion** — The primary eval command should have a clear pass/fail signal. Prefer `pytest tests/test_foo.py::test_specific_case` over `pytest tests/` (which might pass even if your target test wasn't fixed).

**Setup commands that don't work in Docker** — Test your setup commands in a clean container. Commands that rely on your local environment (e.g., a globally installed tool) will fail in CI.

**Missing `pass_condition`** — Always set `pass_condition: "exit_code == 0"` for `test_suite`, `lint`, and `type_check` criteria.

## Verifying Your Task

```bash
# Check YAML is valid and parses correctly
agentbench validate tasks/my-task/task.yaml

# Full Docker-based validation: builds sandbox, runs setup, runs primary eval
agentbench deep-validate tasks/my-task/
```

The deep-validate command checks:
1. Task YAML parses and validates against the schema
2. The sandbox builds and setup commands succeed
3. The **primary eval fails** on the unmodified code (so there's actually something to fix)
4. A reference solution (if provided in `solution/`) makes the primary eval pass
