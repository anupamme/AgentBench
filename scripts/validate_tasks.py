#!/usr/bin/env python3
"""Validate all task definitions in the tasks/ directory."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentbench.core.task_loader import TaskLoader, TaskLoadError


def main():
    tasks_dir = Path(__file__).parent.parent / "tasks"
    loader = TaskLoader()
    errors = []
    valid = 0

    for task_dir in sorted(tasks_dir.iterdir()):
        if not task_dir.is_dir() or task_dir.name.startswith("."):
            continue
        task_yaml = task_dir / "task.yaml"
        if not task_yaml.exists():
            errors.append(f"  {task_dir.name}: missing task.yaml")
            continue
        try:
            task = loader.load_task(task_yaml)
            print(f"  \u2713 {task.id} ({task.metadata.difficulty.value}, {task.metadata.task_type.value})")
            valid += 1
        except TaskLoadError as e:
            errors.append(f"  \u2717 {task_dir.name}: {e.errors}")

    print(f"\n{valid} valid, {len(errors)} errors")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
