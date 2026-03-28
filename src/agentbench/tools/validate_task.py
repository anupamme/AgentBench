"""
Deep task validator — checks that tasks are self-consistent and solvable.

Checks:
1. YAML schema validation (from TaskLoader)
2. Repo directory exists and is non-empty
3. Solution directory exists and is non-empty
4. Docker build succeeds (if custom Dockerfile)
5. Setup commands succeed in a fresh container
6. Tests FAIL with the initial repo state (proving the bug exists)
7. Tests PASS with the solution applied (proving the fix works)
8. Evaluation commands complete within timeout
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from agentbench.core.task_loader import TaskLoader
from agentbench.sandbox.manager import SandboxManager

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str = ""
    duration_seconds: float = 0.0


@dataclass
class ValidationResult:
    task_id: str
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)


class TaskValidator:
    """Deep validation of benchmark tasks."""

    def __init__(self, sandbox_manager: SandboxManager | None = None) -> None:
        self._sandbox_manager = sandbox_manager or SandboxManager()
        self._loader = TaskLoader()

    async def validate(self, task_dir: Path) -> ValidationResult:
        """
        Run all validation checks on a task directory.

        Checks (in order):
        1. schema_valid: task.yaml passes Pydantic validation
        2. repo_exists: repo/ directory exists and is non-empty
        3. solution_exists: solution/ directory exists and is non-empty
        4. setup_succeeds: setup commands run without errors in a container
        5. tests_fail_initially: running eval command on unmodified repo fails
           (proves the bug/missing feature exists)
        6. tests_pass_with_solution: copying solution files into repo makes eval pass
           (proves the solution works)
        """
        results: list[CheckResult] = []
        task_id = task_dir.name

        # ── Check 1: Schema validation ────────────────────────────────────────
        task_yaml = task_dir / "task.yaml"
        t0 = time.monotonic()
        try:
            task = self._loader.load_task(task_yaml)
            results.append(  # noqa: E501
                CheckResult("schema_valid", True, duration_seconds=time.monotonic() - t0)
            )
        except Exception as e:
            results.append(CheckResult("schema_valid", False, str(e), time.monotonic() - t0))
            return ValidationResult(task_id=task_id, passed=False, checks=results)

        # ── Check 2: repo/ exists and non-empty ───────────────────────────────
        repo_dir = task_dir / "repo"
        if repo_dir.is_dir() and any(repo_dir.iterdir()):
            results.append(CheckResult("repo_exists", True))
        else:
            results.append(CheckResult("repo_exists", False, "repo/ missing or empty"))
            return ValidationResult(task_id=task_id, passed=False, checks=results)

        # ── Check 3: solution/ exists and non-empty ───────────────────────────
        solution_dir = task_dir / "solution"
        solution_files = [
            f for f in solution_dir.rglob("*") if f.is_file() and f.name != ".gitkeep"
        ]
        if solution_dir.is_dir() and solution_files:
            results.append(CheckResult("solution_exists", True))
        else:
            results.append(CheckResult("solution_exists", False, "solution/ missing or empty"))
            # Don't short-circuit — sandbox checks are still useful

        # ── Checks 4–6: require Docker ────────────────────────────────────────
        # Point the task's repo at the local repo/ directory so the sandbox
        # copies it instead of trying to clone from a Git URL.
        task.setup.repo = str(repo_dir.resolve())

        try:
            t0 = time.monotonic()
            async with self._sandbox_manager.session(task) as sandbox:
                # Check 4: Setup succeeded (sandbox creation runs setup_commands)
                results.append(
                    CheckResult("setup_succeeds", True, duration_seconds=time.monotonic() - t0)
                )

                # Check 5: Tests fail initially ─────────────────────────────
                assert task.evaluation.primary.command is not None
                t0 = time.monotonic()
                eval_result = await self._sandbox_manager.exec(
                    sandbox,
                    task.evaluation.primary.command,
                    timeout=task.evaluation.primary.timeout_seconds,
                )
                duration = time.monotonic() - t0
                if eval_result.exit_code != 0:
                    results.append(
                        CheckResult(
                            "tests_fail_initially",
                            True,
                            f"Exit code: {eval_result.exit_code}",
                            duration,
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            "tests_fail_initially",
                            False,
                            "Tests pass on unmodified repo — bug doesn't exist or tests"
                            " don't catch it",
                            duration,
                        )
                    )

                # Check 6: Tests pass with solution ──────────────────────────
                # Copy solution files into the workspace via base64-encoded writes
                for sol_file in solution_dir.rglob("*"):
                    if sol_file.is_file() and sol_file.name != ".gitkeep":
                        rel_path = sol_file.relative_to(solution_dir)
                        content = sol_file.read_bytes()
                        encoded = base64.b64encode(content).decode()
                        cmd = (
                            'python3 -c "'
                            "import base64, pathlib; "
                            f"p = pathlib.Path('{rel_path}'); "
                            "p.parent.mkdir(parents=True, exist_ok=True); "
                            f"p.write_bytes(base64.b64decode('{encoded}'))"
                            '"'
                        )
                        await self._sandbox_manager.exec(sandbox, cmd, timeout=30)

                assert task.evaluation.primary.command is not None
                t0 = time.monotonic()
                eval_result = await self._sandbox_manager.exec(
                    sandbox,
                    task.evaluation.primary.command,
                    timeout=task.evaluation.primary.timeout_seconds,
                )
                duration = time.monotonic() - t0
                if eval_result.exit_code == 0:
                    results.append(
                        CheckResult("tests_pass_with_solution", True, duration_seconds=duration)
                    )
                else:
                    output_preview = (eval_result.stdout + eval_result.stderr)[:500]
                    results.append(
                        CheckResult(
                            "tests_pass_with_solution",
                            False,
                            f"Tests fail even with solution applied:\n{output_preview}",
                            duration,
                        )
                    )

        except Exception as e:
            results.append(CheckResult("sandbox_error", False, str(e)))

        all_passed = all(c.passed for c in results)
        return ValidationResult(task_id=task_id, passed=all_passed, checks=results)
