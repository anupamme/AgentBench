"""Tests for SandboxManager — requires Docker daemon to be running."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from agentbench.core.models import TaskSpec
from agentbench.sandbox.manager import (
    ResourceLimits,
    SandboxManager,
    SandboxStatus,
)

if TYPE_CHECKING:
    from pathlib import Path

# Mark all tests in this module as requiring Docker
pytestmark = pytest.mark.docker


@pytest.fixture
def sandbox_manager() -> SandboxManager:
    return SandboxManager()


@pytest.fixture
def simple_task_spec() -> TaskSpec:
    """A task spec that uses a local test repo (no git clone needed)."""
    raw = {
        "id": "test-sandbox-task",
        "version": 1,
        "metadata": {
            "difficulty": "easy",
            "task_type": "bug_fix",
            "languages": ["python"],
            "estimated_human_time_minutes": 5,
            "source": "test",
        },
        "setup": {
            "repo": "/tmp/test-repo",  # will be overridden in test
            "commit": "HEAD",
            "setup_commands": ["echo setup_complete > /workspace/.setup_done"],
        },
        "prompt": "Fix the bug.",
        "evaluation": {
            "primary": {
                "type": "test_suite",
                "command": "python -m pytest tests/ -x",
                "pass_condition": "exit_code == 0",
            }
        },
        "constraints": {
            "max_turns": 10,
            "max_tokens": 50000,
            "timeout_seconds": 60,
            "network": False,
        },
    }
    return TaskSpec.model_validate(raw)


class TestSandboxLifecycle:
    async def test_create_and_teardown(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        """Create a sandbox, verify it's running, tear it down."""
        (tmp_path / "main.py").write_text("print('hello')")
        simple_task_spec.setup.repo = str(tmp_path)

        sandbox = await sandbox_manager.create(simple_task_spec)
        assert sandbox.status == SandboxStatus.READY
        assert sandbox.container_id is not None

        await sandbox_manager.teardown(sandbox)
        assert sandbox.status == SandboxStatus.TORN_DOWN

    async def test_exec_simple_command(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "main.py").write_text("print('hello')")
        simple_task_spec.setup.repo = str(tmp_path)

        async with sandbox_manager.session(simple_task_spec) as sandbox:
            result = await sandbox_manager.exec(sandbox, "echo hello")
            assert result.exit_code == 0
            assert "hello" in result.stdout

    async def test_exec_captures_stderr(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "main.py").write_text("")
        simple_task_spec.setup.repo = str(tmp_path)

        async with sandbox_manager.session(simple_task_spec) as sandbox:
            result = await sandbox_manager.exec(sandbox, "echo error >&2")
            assert "error" in result.stderr

    async def test_exec_timeout(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "main.py").write_text("")
        simple_task_spec.setup.repo = str(tmp_path)

        async with sandbox_manager.session(simple_task_spec) as sandbox:
            result = await sandbox_manager.exec(sandbox, "sleep 30", timeout=2)
            assert result.timed_out is True

    async def test_exec_nonzero_exit_code(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "main.py").write_text("")
        simple_task_spec.setup.repo = str(tmp_path)

        async with sandbox_manager.session(simple_task_spec) as sandbox:
            result = await sandbox_manager.exec(sandbox, "exit 42")
            assert result.exit_code == 42

    async def test_setup_commands_run(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "main.py").write_text("")
        simple_task_spec.setup.repo = str(tmp_path)

        async with sandbox_manager.session(simple_task_spec) as sandbox:
            result = await sandbox_manager.exec(sandbox, "cat /workspace/.setup_done")
            assert "setup_complete" in result.stdout


class TestFilesystemDiff:
    async def test_snapshot_diff_detects_new_file(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "main.py").write_text("original")
        simple_task_spec.setup.repo = str(tmp_path)

        async with sandbox_manager.session(simple_task_spec) as sandbox:
            await sandbox_manager.exec(sandbox, "echo new_content > /workspace/new_file.py")
            diff = await sandbox_manager.snapshot_diff(sandbox)
            assert "new_file.py" in diff.files_added

    async def test_snapshot_diff_detects_modified_file(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "main.py").write_text("original")
        simple_task_spec.setup.repo = str(tmp_path)

        async with sandbox_manager.session(simple_task_spec) as sandbox:
            await sandbox_manager.exec(sandbox, "echo modified > /workspace/main.py")
            diff = await sandbox_manager.snapshot_diff(sandbox)
            assert "main.py" in diff.files_modified

    async def test_snapshot_diff_detects_deleted_file(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "main.py").write_text("original")
        simple_task_spec.setup.repo = str(tmp_path)

        async with sandbox_manager.session(simple_task_spec) as sandbox:
            await sandbox_manager.exec(sandbox, "rm /workspace/main.py")
            diff = await sandbox_manager.snapshot_diff(sandbox)
            assert "main.py" in diff.files_deleted


class TestNetworkIsolation:
    async def test_network_disabled_by_default(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "main.py").write_text("")
        simple_task_spec.setup.repo = str(tmp_path)
        simple_task_spec.constraints.network = False

        async with sandbox_manager.session(simple_task_spec) as sandbox:
            result = await sandbox_manager.exec(sandbox, "curl -s https://example.com", timeout=5)
            # Should fail — network is disabled
            assert result.exit_code != 0 or result.timed_out


class TestResourceLimits:
    async def test_memory_limit_applied(
        self,
        sandbox_manager: SandboxManager,
        simple_task_spec: TaskSpec,
        tmp_path: Path,
    ) -> None:
        """Container should have memory limit set."""
        (tmp_path / "main.py").write_text("")
        simple_task_spec.setup.repo = str(tmp_path)

        limits = ResourceLimits(memory_mb=512)
        async with sandbox_manager.session(simple_task_spec, resource_limits=limits) as sandbox:
            # Verify container has memory limit by inspecting it
            import docker

            client = docker.from_env()
            container = client.containers.get(sandbox.container_id)
            mem_limit = container.attrs["HostConfig"]["Memory"]
            assert mem_limit == 512 * 1024 * 1024  # 512MB in bytes
