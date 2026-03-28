# Contributing to AgentBench

## Development Setup

```bash
git clone https://github.com/anupamme/AgentBench
cd AgentBench
pip install -e ".[dev]"
pre-commit install
```

`pip install -e ".[dev]"` installs the package in editable mode with all development dependencies (pytest, ruff, mypy, pre-commit). Python 3.12+ is required.

`pre-commit install` sets up Git hooks that automatically run ruff and mypy on each `git commit`.

## Running Tests

Tests are split into unit tests (no external dependencies) and Docker integration tests (require a running Docker daemon).

```bash
# Unit tests only — fast, no Docker needed
pytest tests/ -m "not docker"

# Docker integration tests — requires Docker daemon (~300s timeout)
pytest tests/ -m "docker"

# All tests
pytest tests/
```

For most contributions, running the unit tests is sufficient. CI runs both categories automatically.

## Code Quality

```bash
# Lint
ruff check src/ tests/

# Format check (or auto-fix with --fix)
ruff format src/ tests/

# Type check
mypy src/agentbench/ --ignore-missing-imports
```

The project uses `ruff` with `line-length = 100` and rules `E, F, I, N, W, UP, B, SIM, TCH`. Pre-commit hooks run these automatically on commit.

## Adding a New Task

See [`tasks/README.md`](tasks/README.md) for the complete guide. The short version:

1. Run `agentbench scaffold --id my-task --type <type> --difficulty <level> --language <lang>`
2. Add broken code and a failing test under `tasks/my-task/repo/`
3. Edit `tasks/my-task/task.yaml` with your prompt and evaluation criteria
4. Run `agentbench validate tasks/my-task/task.yaml` (schema check)
5. Run `agentbench deep-validate tasks/my-task/` (full Docker validation)
6. Open a PR — CI will re-run the validation

## Adding a New Agent Adapter

See [`docs/adapters.md`](docs/adapters.md) for the complete guide. The short version:

1. Create a new file in `src/agentbench/adapters/` (e.g., `aider.py`)
2. Subclass `AgentAdapter` from `src/agentbench/adapters/base.py` and implement `name()` and `solve()`
3. Register the new class in `src/agentbench/adapters/registry.py`
4. Add unit tests under `tests/test_adapters/`

## Pull Request Process

- All CI checks must pass: lint, type check, unit tests, and task validation
- For bug fixes: include a regression test that reproduces the bug
- For new tasks: `agentbench deep-validate` must pass locally before the PR
- For new adapters: include unit tests that use the mock sandbox
- For user-facing CLI changes: update the relevant section of `README.md`

PRs that only touch documentation do not need the full test suite to pass, but should still pass lint.
