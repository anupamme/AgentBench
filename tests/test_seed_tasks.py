"""Tests that verify all seed tasks are valid and well-formed."""
from __future__ import annotations

import pytest
from pathlib import Path
from agentbench.core.task_loader import TaskLoader

TASKS_DIR = Path(__file__).parent.parent / "tasks"


def get_task_dirs():
    if not TASKS_DIR.exists():
        return []
    return [d for d in sorted(TASKS_DIR.iterdir()) if d.is_dir() and not d.name.startswith(".")]


@pytest.mark.parametrize("task_dir", get_task_dirs(), ids=lambda d: d.name)
def test_task_yaml_is_valid(task_dir: Path):
    loader = TaskLoader()
    task_yaml = task_dir / "task.yaml"
    assert task_yaml.exists(), f"Missing task.yaml in {task_dir}"
    task = loader.load_task(task_yaml)
    assert task.id == task_dir.name, f"Task ID '{task.id}' must match directory name '{task_dir.name}'"


@pytest.mark.parametrize("task_dir", get_task_dirs(), ids=lambda d: d.name)
def test_task_has_repo(task_dir: Path):
    repo_dir = task_dir / "repo"
    assert repo_dir.exists(), f"Missing repo/ directory in {task_dir}"
    assert any(repo_dir.iterdir()), f"repo/ directory is empty in {task_dir}"


@pytest.mark.parametrize("task_dir", get_task_dirs(), ids=lambda d: d.name)
def test_task_has_solution(task_dir: Path):
    solution_dir = task_dir / "solution"
    assert solution_dir.exists(), f"Missing solution/ directory in {task_dir}"
    assert any(solution_dir.iterdir()), f"solution/ directory is empty in {task_dir}"


def test_minimum_task_count():
    """We need at least 5 seed tasks."""
    assert len(get_task_dirs()) >= 5
