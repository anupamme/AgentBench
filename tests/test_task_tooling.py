"""Tests for task scaffolding and deep validation tooling."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentbench.core.task_loader import TaskLoader
from agentbench.tools.scaffold_task import scaffold_task
from agentbench.tools.validate_task import TaskValidator

# ─────────────────────────────────────────────────────────────────────────────
# Scaffolding tests (no Docker required)
# ─────────────────────────────────────────────────────────────────────────────


def test_scaffold_creates_directory_structure(tmp_path: Path) -> None:
    task_dir = scaffold_task(
        id="test-scaffold-task",
        task_type="bug_fix",
        difficulty="easy",
        language="python",
        tasks_root=tmp_path,
    )

    assert task_dir.is_dir()
    assert (task_dir / "task.yaml").is_file()
    assert (task_dir / "repo").is_dir()
    assert (task_dir / "solution").is_dir()
    assert (task_dir / "solution" / ".gitkeep").is_file()


def test_scaffold_yaml_is_valid(tmp_path: Path) -> None:
    scaffold_task(
        id="test-valid-yaml",
        task_type="feature_add",
        difficulty="medium",
        language="python",
        tasks_root=tmp_path,
    )
    loader = TaskLoader()
    errors = loader.validate_only(tmp_path / "test-valid-yaml" / "task.yaml")
    assert errors == [], f"Unexpected validation errors: {errors}"


def test_scaffold_python_files(tmp_path: Path) -> None:
    task_dir = scaffold_task(
        id="python-task",
        task_type="bug_fix",
        difficulty="easy",
        language="python",
        tasks_root=tmp_path,
    )
    repo = task_dir / "repo"
    assert (repo / "main.py").is_file()
    assert (repo / "tests" / "test_main.py").is_file()
    assert (repo / "requirements.txt").is_file()


def test_scaffold_javascript_files(tmp_path: Path) -> None:
    task_dir = scaffold_task(
        id="js-task",
        task_type="feature_add",
        difficulty="medium",
        language="javascript",
        tasks_root=tmp_path,
    )
    repo = task_dir / "repo"
    assert (repo / "src" / "index.js").is_file()
    assert (repo / "tests" / "index.test.js").is_file()
    assert (repo / "package.json").is_file()


def test_scaffold_raises_if_exists(tmp_path: Path) -> None:
    scaffold_task(
        id="duplicate-task",
        task_type="bug_fix",
        difficulty="easy",
        language="python",
        tasks_root=tmp_path,
    )
    with pytest.raises(FileExistsError):
        scaffold_task(
            id="duplicate-task",
            task_type="bug_fix",
            difficulty="easy",
            language="python",
            tasks_root=tmp_path,
        )


def test_scaffold_invalid_difficulty(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="difficulty"):
        scaffold_task(
            id="bad-difficulty",
            task_type="bug_fix",
            difficulty="impossible",
            language="python",
            tasks_root=tmp_path,
        )


def test_scaffold_invalid_task_type(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="task_type"):
        scaffold_task(
            id="bad-type",
            task_type="unknown_type",
            difficulty="easy",
            language="python",
            tasks_root=tmp_path,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Validator unit tests (mocked sandbox)
# ─────────────────────────────────────────────────────────────────────────────


def _make_task_dir(tmp_path: Path, *, with_repo: bool = True, with_solution: bool = True) -> Path:
    """Helper: create a minimal valid task directory structure."""
    scaffold_task(
        id="mock-task",
        task_type="bug_fix",
        difficulty="easy",
        language="python",
        tasks_root=tmp_path,
    )
    task_dir = tmp_path / "mock-task"

    if not with_repo:
        import shutil
        shutil.rmtree(task_dir / "repo")

    if not with_solution:
        import shutil
        shutil.rmtree(task_dir / "solution")

    return task_dir


@pytest.mark.asyncio
async def test_validator_missing_schema(tmp_path: Path) -> None:
    # Point to a directory with no task.yaml
    task_dir = tmp_path / "no-yaml-task"
    task_dir.mkdir()

    validator = TaskValidator(sandbox_manager=MagicMock())
    result = await validator.validate(task_dir)

    assert not result.passed
    schema_check = next(c for c in result.checks if c.name == "schema_valid")
    assert not schema_check.passed


@pytest.mark.asyncio
async def test_validator_missing_repo(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path, with_repo=False)

    validator = TaskValidator(sandbox_manager=MagicMock())
    result = await validator.validate(task_dir)

    assert not result.passed
    repo_check = next(c for c in result.checks if c.name == "repo_exists")
    assert not repo_check.passed
    # Should short-circuit — no sandbox checks attempted
    assert not any(c.name == "setup_succeeds" for c in result.checks)


@pytest.mark.asyncio
async def test_validator_missing_solution(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path, with_solution=False)

    # Mock sandbox so we don't need Docker
    mock_manager = MagicMock()
    mock_sandbox = MagicMock()
    mock_exec_fail = MagicMock(exit_code=1, stdout="", stderr="test failed")
    mock_exec_pass = MagicMock(exit_code=0, stdout="", stderr="")

    # session() is an async context manager
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session(task, resource_limits=None):
        yield mock_sandbox

    mock_manager.session = mock_session
    mock_manager.exec = AsyncMock(side_effect=[mock_exec_fail, mock_exec_pass])

    validator = TaskValidator(sandbox_manager=mock_manager)
    result = await validator.validate(task_dir)

    solution_check = next(c for c in result.checks if c.name == "solution_exists")
    assert not solution_check.passed
    assert not result.passed


@pytest.mark.asyncio
async def test_validator_full_pass(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path, with_repo=True, with_solution=True)

    # Add a real solution file so solution_exists passes
    solution_file = task_dir / "solution" / "main.py"
    solution_file.write_text("def fixed(): pass\n")

    mock_manager = MagicMock()
    mock_sandbox = MagicMock()
    # First exec: tests fail on unmodified repo (exit_code != 0)
    # Second exec: tests pass after solution applied (exit_code == 0)
    mock_exec_fail = MagicMock(exit_code=1, stdout="FAILED 1 error", stderr="")
    mock_exec_pass = MagicMock(exit_code=0, stdout="passed", stderr="")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session(task, resource_limits=None):
        yield mock_sandbox

    mock_manager.session = mock_session
    # exec calls in order:
    #   1. run eval on unmodified repo → fail (tests_fail_initially)
    #   2. copy solution file via base64 → success (one file: main.py)
    #   3. run eval with solution → pass (tests_pass_with_solution)
    mock_copy_ok = MagicMock(exit_code=0, stdout="", stderr="")
    mock_manager.exec = AsyncMock(side_effect=[mock_exec_fail, mock_copy_ok, mock_exec_pass])

    validator = TaskValidator(sandbox_manager=mock_manager)
    result = await validator.validate(task_dir)

    check_names = [c.name for c in result.checks]
    assert "schema_valid" in check_names
    assert "repo_exists" in check_names
    assert "solution_exists" in check_names
    assert "setup_succeeds" in check_names
    assert "tests_fail_initially" in check_names
    assert "tests_pass_with_solution" in check_names

    assert all(c.passed for c in result.checks), [
        f"{c.name}: {c.message}" for c in result.checks if not c.passed
    ]
    assert result.passed


@pytest.mark.asyncio
async def test_validator_detects_no_bug(tmp_path: Path) -> None:
    """If tests pass on the unmodified repo, tests_fail_initially should fail."""
    task_dir = _make_task_dir(tmp_path)
    (task_dir / "solution" / "fix.py").write_text("pass\n")

    mock_manager = MagicMock()
    mock_sandbox = MagicMock()
    # Tests pass even on the unmodified repo — no bug present
    mock_exec_pass = MagicMock(exit_code=0, stdout="passed", stderr="")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session(task, resource_limits=None):
        yield mock_sandbox

    mock_manager.session = mock_session
    # exec calls in order:
    #   1. run eval on unmodified repo → pass (bug absent — tests_fail_initially should fail)
    #   2. copy solution file via base64 → success (one file: fix.py)
    #   3. run eval with solution → pass
    mock_manager.exec = AsyncMock(side_effect=[mock_exec_pass, mock_exec_pass, mock_exec_pass])

    validator = TaskValidator(sandbox_manager=mock_manager)
    result = await validator.validate(task_dir)

    fail_check = next(c for c in result.checks if c.name == "tests_fail_initially")
    assert not fail_check.passed
    assert not result.passed


# ─────────────────────────────────────────────────────────────────────────────
# Docker integration tests
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent


@pytest.mark.docker
@pytest.mark.asyncio
async def test_validator_with_real_task() -> None:
    task_dir = REPO_ROOT / "tasks" / "calc-fix-division-by-zero"
    assert task_dir.is_dir(), f"Seed task not found: {task_dir}"

    validator = TaskValidator()
    result = await validator.validate(task_dir)

    failed = [c for c in result.checks if not c.passed]
    assert result.passed, f"Validation failed. Failed checks: {failed}"
