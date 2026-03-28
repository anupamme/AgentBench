"""
Task scaffolding tool — creates a new task directory with boilerplate.

Usage:
    agentbench scaffold --id my-task-name --type bug_fix --difficulty medium --language python
"""
from __future__ import annotations

from pathlib import Path

from rich.console import Console

from agentbench.core.models import Difficulty, TaskType

console = Console()

_TASK_YAML_TEMPLATE = """\
id: {id}
version: 1
metadata:
  difficulty: {difficulty}
  task_type: {task_type}
  languages: [{language}]
  estimated_human_time_minutes: 15
  tags: []
  source: contributed
setup:
  repo: tasks/{id}/repo
  commit: HEAD
  setup_commands: []
  files_to_highlight: []
prompt: "TODO: Describe the task here."
evaluation:
  primary:
    type: test_suite
    command: "TODO: add test command"
    pass_condition: "exit_code == 0"
    label: primary_tests
    timeout_seconds: 60
  secondary: []
constraints:
  max_turns: 20
  max_tokens: 50000
  timeout_seconds: 300
  network: false
"""

_PYTHON_MAIN = """\
def main():
    # TODO: implement the code under test
    pass


if __name__ == "__main__":
    main()
"""

_PYTHON_TEST = """\
import pytest
from main import main


def test_placeholder():
    # TODO: write a failing test that the agent must fix
    assert False, "Replace this with a real test"
"""

_REQUIREMENTS_TXT = """\
pytest
"""

_JS_INDEX = """\
// TODO: implement the code under test
function main() {}

module.exports = { main };
"""

_JS_TEST = """\
const { main } = require('../src/index');

test('placeholder', () => {
  // TODO: write a failing test that the agent must fix
  expect(false).toBe(true);
});
"""

_PACKAGE_JSON = """\
{{
  "name": "{id}",
  "version": "1.0.0",
  "scripts": {{
    "test": "jest"
  }},
  "devDependencies": {{
    "jest": "^29.0.0"
  }}
}}
"""


def scaffold_task(
    id: str,
    task_type: str,
    difficulty: str = "medium",
    language: str = "python",
    tasks_root: Path | None = None,
) -> Path:
    """
    Create a new task directory with boilerplate files.

    Args:
        id: Task ID in kebab-case (e.g. "fix-null-pointer-bug")
        task_type: One of the TaskType enum values (e.g. "bug_fix")
        difficulty: One of "easy", "medium", "hard", "expert"
        language: Primary language: "python" or "javascript"
        tasks_root: Override the default tasks/ directory (used in tests)

    Returns:
        Path to the created task directory.

    Raises:
        ValueError: If task_type or difficulty are not valid enum values.
        FileExistsError: If the task directory already exists.
    """
    # Validate enums early for clear error messages
    try:
        Difficulty(difficulty)
    except ValueError:
        valid = [d.value for d in Difficulty]
        raise ValueError(f"Invalid difficulty {difficulty!r}. Must be one of: {valid}") from None

    try:
        TaskType(task_type)
    except ValueError:
        valid = [t.value for t in TaskType]
        raise ValueError(f"Invalid task_type {task_type!r}. Must be one of: {valid}") from None

    if tasks_root is None:
        tasks_root = Path.cwd() / "tasks"

    task_dir = tasks_root / id

    if task_dir.exists():
        raise FileExistsError(f"Task directory already exists: {task_dir}")

    # Create directory structure
    repo_dir = task_dir / "repo"
    solution_dir = task_dir / "solution"
    task_dir.mkdir(parents=True)
    repo_dir.mkdir()
    solution_dir.mkdir()

    # Write task.yaml
    (task_dir / "task.yaml").write_text(
        _TASK_YAML_TEMPLATE.format(
            id=id, difficulty=difficulty, task_type=task_type, language=language
        )
    )

    # Write language-specific placeholder files
    if language == "javascript":
        (repo_dir / "src").mkdir()
        (repo_dir / "tests").mkdir()
        (repo_dir / "src" / "index.js").write_text(_JS_INDEX)
        (repo_dir / "tests" / "index.test.js").write_text(_JS_TEST)
        (repo_dir / "package.json").write_text(_PACKAGE_JSON.format(id=id))
    else:
        # Default to Python for any unrecognised language
        (repo_dir / "tests").mkdir()
        (repo_dir / "main.py").write_text(_PYTHON_MAIN)
        (repo_dir / "tests" / "test_main.py").write_text(_PYTHON_TEST)
        (repo_dir / "requirements.txt").write_text(_REQUIREMENTS_TXT)

    # Keep solution/ tracked in git
    (solution_dir / ".gitkeep").write_text("")

    console.print(f"\n[green]✓ Task scaffold created:[/green] {task_dir}\n")
    console.print("[bold]Next steps:[/bold]")
    console.print(
        f"  1. Edit [cyan]{task_dir / 'task.yaml'}[/cyan] — fill in the prompt and eval command"
    )
    console.print(
        f"  2. Edit [cyan]{task_dir / 'repo'}[/cyan] — add the broken code that needs fixing"
    )
    console.print(f"  3. Add the solution files to [cyan]{task_dir / 'solution'}[/cyan]")
    console.print(f"  4. Run [cyan]agentbench deep-validate {task_dir}[/cyan] to verify the task\n")

    return task_dir
