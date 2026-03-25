"""
Task Loader — loads and validates task definitions from YAML files.

Supports loading individual tasks, directories of tasks, and named suites.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

from agentbench.core.models import TaskSpec


class TaskLoadError(Exception):
    """Raised when a task YAML is invalid or cannot be loaded."""

    def __init__(self, path: Path, errors: list[str]) -> None:
        self.path = path
        self.errors = errors
        super().__init__(f"Failed to load task {path}: {'; '.join(errors)}")


class TaskLoader:
    """Loads and validates task specs from YAML files."""

    def load_task(self, path: Path) -> TaskSpec:
        """
        Load a single task YAML file and return a validated TaskSpec.

        Raises TaskLoadError if the YAML is malformed or fails validation.
        """
        if not path.exists():
            raise TaskLoadError(path, [f"File not found: {path}"])
        if path.suffix not in (".yaml", ".yml"):
            raise TaskLoadError(path, [f"Expected .yaml or .yml file, got: {path.suffix}"])

        try:
            with open(path) as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise TaskLoadError(path, [f"YAML parse error: {e}"]) from e

        if not isinstance(raw, dict):
            raise TaskLoadError(path, ["YAML root must be a mapping"])

        try:
            return TaskSpec.model_validate(raw)
        except Exception as e:
            raise TaskLoadError(path, [str(e)]) from e

    def load_directory(self, directory: Path) -> list[TaskSpec]:
        """
        Load all .yaml/.yml files in a directory (non-recursive).

        Returns list of valid TaskSpecs. Raises TaskLoadError on first invalid file.
        """
        if not directory.is_dir():
            raise TaskLoadError(directory, ["Not a directory"])

        tasks = []
        for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
            tasks.append(self.load_task(path))
        return tasks

    def load_suite(self, suite_path: Path) -> list[TaskSpec]:
        """
        Load a suite definition file (a YAML file listing task IDs or paths).

        Suite format:
        ```yaml
        name: standard-v1
        description: Standard benchmark suite
        tasks:
          - path: tasks/django-fix-queryset/task.yaml
          - path: tasks/flask-add-middleware/task.yaml
        ```
        """
        try:
            with open(suite_path) as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise TaskLoadError(suite_path, [f"YAML parse error: {e}"]) from e

        base_dir = suite_path.parent
        tasks = []
        for entry in raw.get("tasks", []):
            task_path = base_dir / entry["path"]
            tasks.append(self.load_task(task_path))
        return tasks

    def validate_only(self, path: Path) -> list[str]:
        """
        Validate a task YAML without fully loading it.
        Returns a list of error strings (empty if valid).
        """
        try:
            self.load_task(path)
            return []
        except TaskLoadError as e:
            return e.errors
