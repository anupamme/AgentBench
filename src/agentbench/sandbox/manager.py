"""
Sandbox Manager — Docker-based isolated execution environments.

Responsibilities:
- Create fresh Docker containers per task run
- Execute commands inside sandboxes
- Capture filesystem diffs before/after agent runs
- Enforce resource limits (CPU, memory, timeout)
- Clean up containers after runs
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import docker
import docker.errors

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from agentbench.core.models import TaskSpec


class SandboxStatus(StrEnum):
    CREATING = "creating"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TORN_DOWN = "torn_down"


@dataclass
class ResourceLimits:
    cpu_count: int = 2
    memory_mb: int = 2048
    timeout_seconds: int = 600
    network_enabled: bool = False


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False


@dataclass
class FileDiff:
    """Filesystem diff between workspace snapshots."""

    files_added: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    raw_diff: str = ""  # unified diff output


@dataclass
class Sandbox:
    container_id: str
    task_id: str
    workspace_path: str  # path inside container, e.g. /workspace
    host_workspace_path: Path  # path on host for result extraction
    status: SandboxStatus = SandboxStatus.CREATING
    created_at: datetime = field(default_factory=datetime.utcnow)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    snapshot_commit: str = ""  # git commit hash capturing post-setup state


class SandboxError(Exception):
    """Raised on sandbox creation, execution, or teardown failures."""

    pass


# Git identity used when creating snapshot commits in workspaces
_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "AgentBench",
    "GIT_AUTHOR_EMAIL": "agentbench@localhost",
    "GIT_COMMITTER_NAME": "AgentBench",
    "GIT_COMMITTER_EMAIL": "agentbench@localhost",
}


class SandboxManager:
    """Manages Docker sandbox lifecycle for task evaluation."""

    DEFAULT_IMAGE = "python:3.12-slim"
    WORKSPACE_CONTAINER_PATH = "/workspace"

    def __init__(self, docker_client: Any = None) -> None:
        """
        Args:
            docker_client: Optional pre-configured Docker client.
                           If None, connects to the local Docker daemon.
        """
        self._client: Any = docker_client or docker.from_env()  # type: ignore[attr-defined]
        self._active_sandboxes: dict[str, Sandbox] = {}

    async def create(
        self, task: TaskSpec, resource_limits: ResourceLimits | None = None
    ) -> Sandbox:
        """Create and start a sandbox for the given task."""
        limits = resource_limits or ResourceLimits()

        host_workspace = Path(tempfile.mkdtemp(prefix="agentbench_"))

        try:
            # Clone or copy repo into host workspace
            if task.setup.repo.startswith("http"):
                await self._clone_repo(task.setup.repo, task.setup.commit, host_workspace)
            else:
                await asyncio.to_thread(
                    shutil.copytree, task.setup.repo, str(host_workspace), dirs_exist_ok=True
                )

            # Build container config and start container
            config = self._build_container_config(task, host_workspace, limits)
            try:
                container = await asyncio.to_thread(self._client.containers.run, **config)
            except docker.errors.DockerException as e:
                raise SandboxError(f"Failed to start container: {e}") from e

            sandbox = Sandbox(
                container_id=container.id,
                task_id=task.id,
                workspace_path=self.WORKSPACE_CONTAINER_PATH,
                host_workspace_path=host_workspace,
                status=SandboxStatus.CREATING,
                resource_limits=limits,
            )
            self._active_sandboxes[container.id] = sandbox

            # Run setup commands
            for cmd in task.setup.setup_commands:
                result = await self.exec(sandbox, cmd, timeout=limits.timeout_seconds)
                if result.exit_code != 0:
                    raise SandboxError(
                        f"Setup command failed (exit {result.exit_code}): {cmd}\n"
                        f"stderr: {result.stderr}"
                    )

            # Commit the post-setup workspace state as the diff baseline.
            # This ensures snapshot_diff reflects changes made *after* setup,
            # not changes introduced by setup commands themselves.
            sandbox.snapshot_commit = await self._commit_post_setup_snapshot(host_workspace)

            sandbox.status = SandboxStatus.READY
            return sandbox

        except Exception:
            # Clean up temp dir on failure
            shutil.rmtree(host_workspace, ignore_errors=True)
            raise

    async def exec(self, sandbox: Sandbox, command: str, timeout: int = 60) -> ExecResult:
        """Execute a command inside the sandbox."""
        try:
            container = await asyncio.to_thread(self._client.containers.get, sandbox.container_id)
        except docker.errors.NotFound as e:
            raise SandboxError(f"Container not found: {sandbox.container_id}") from e

        # Wrap with timeout enforced inside the container
        wrapped = f"timeout {timeout} sh -c {shlex.quote(command)}"

        start = time.monotonic()
        try:
            exit_code, output = await asyncio.to_thread(
                container.exec_run,
                wrapped,
                stdout=True,
                stderr=True,
                demux=True,
            )
        except docker.errors.DockerException as e:
            raise SandboxError(f"exec_run failed: {e}") from e

        duration_ms = int((time.monotonic() - start) * 1000)

        stdout_bytes, stderr_bytes = output if output else (b"", b"")
        stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
        stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")

        timed_out = exit_code == 124

        return ExecResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            timed_out=timed_out,
        )

    async def snapshot_diff(self, sandbox: Sandbox) -> FileDiff:
        """Compute the filesystem diff between the post-setup state and current state."""
        if not sandbox.snapshot_commit:
            raise SandboxError("No snapshot commit found; was create() called?")

        workspace = sandbox.host_workspace_path

        def _do_diff() -> tuple[str, str]:
            w = str(workspace)
            commit = sandbox.snapshot_commit

            # Stage all current changes (including new/deleted/modified files)
            subprocess.run(["git", "-C", w, "add", "-A"], check=True, capture_output=True)

            # Get unified diff against the post-setup commit
            raw = subprocess.run(
                ["git", "-C", w, "diff", "--cached", commit],
                check=True,
                capture_output=True,
                text=True,
                env=_GIT_ENV,
            ).stdout

            # Get per-file status: A=added, M=modified, D=deleted
            name_status = subprocess.run(
                ["git", "-C", w, "diff", "--cached", "--name-status", commit],
                check=True,
                capture_output=True,
                text=True,
                env=_GIT_ENV,
            ).stdout

            # Unstage — restore index to the snapshot commit
            subprocess.run(
                ["git", "-C", w, "reset", commit],
                check=True,
                capture_output=True,
                env=_GIT_ENV,
            )

            return raw, name_status

        raw_diff, name_status = await asyncio.to_thread(_do_diff)

        files_added: list[str] = []
        files_modified: list[str] = []
        files_deleted: list[str] = []

        for line in name_status.splitlines():
            if not line.strip():
                continue
            status, _, path = line.partition("\t")
            status = status.strip()
            path = path.strip()
            if status == "A":
                files_added.append(path)
            elif status == "M":
                files_modified.append(path)
            elif status.startswith("D"):
                files_deleted.append(path)

        total_added = sum(
            1
            for line in raw_diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        total_deleted = sum(
            1
            for line in raw_diff.splitlines()
            if line.startswith("-") and not line.startswith("---")
        )

        return FileDiff(
            files_added=files_added,
            files_modified=files_modified,
            files_deleted=files_deleted,
            total_lines_added=total_added,
            total_lines_deleted=total_deleted,
            raw_diff=raw_diff,
        )

    async def teardown(self, sandbox: Sandbox) -> None:
        """Stop and remove the sandbox container. Clean up host workspace."""
        try:
            container = await asyncio.to_thread(self._client.containers.get, sandbox.container_id)
            await asyncio.to_thread(container.stop, timeout=10)
            await asyncio.to_thread(container.remove, force=True)
        except docker.errors.NotFound:
            pass  # already gone
        except docker.errors.DockerException as e:
            raise SandboxError(f"Failed to tear down container: {e}") from e
        finally:
            shutil.rmtree(sandbox.host_workspace_path, ignore_errors=True)
            self._active_sandboxes.pop(sandbox.container_id, None)
            sandbox.status = SandboxStatus.TORN_DOWN

    async def teardown_all(self) -> None:
        """Tear down all active sandboxes. Used for cleanup on shutdown."""
        for sandbox in list(self._active_sandboxes.values()):
            with contextlib.suppress(Exception):
                await self.teardown(sandbox)

    @asynccontextmanager
    async def session(
        self, task: TaskSpec, resource_limits: ResourceLimits | None = None
    ) -> AsyncIterator[Sandbox]:
        """Context manager that creates a sandbox and ensures teardown."""
        sandbox = await self.create(task, resource_limits)
        try:
            yield sandbox
        finally:
            await self.teardown(sandbox)

    def _build_container_config(
        self, task: TaskSpec, host_workspace: Path, limits: ResourceLimits
    ) -> dict[str, object]:
        """Build the Docker container configuration dict."""
        image = task.setup.dockerfile or self.DEFAULT_IMAGE
        return {
            "image": image,
            "volumes": {str(host_workspace): {"bind": self.WORKSPACE_CONTAINER_PATH, "mode": "rw"}},
            "working_dir": self.WORKSPACE_CONTAINER_PATH,
            # Network is always enabled at the container level so that setup_commands
            # (e.g. pip install) can reach the internet. The task.constraints.network
            # flag is enforced by agent adapters, not at the Docker layer, since
            # Docker container networking cannot be changed after creation.
            "mem_limit": f"{limits.memory_mb}m",
            "nano_cpus": limits.cpu_count * 1_000_000_000,
            "detach": True,
            "stdin_open": True,
            "command": "sleep infinity",
        }

    async def _clone_repo(self, repo_url: str, commit: str, dest: Path) -> None:
        """Clone a git repo and checkout a specific commit."""

        def _do_clone() -> None:
            try:
                subprocess.run(
                    ["git", "clone", repo_url, str(dest)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                subprocess.run(
                    ["git", "-C", str(dest), "checkout", commit],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                raise SandboxError(f"Git operation failed: {e.cmd}\nstderr: {e.stderr}") from e

        await asyncio.to_thread(_do_clone)

    async def _commit_post_setup_snapshot(self, workspace: Path) -> str:
        """
        Commit the current workspace state as the diff baseline.

        Called after setup commands complete so that snapshot_diff measures
        only changes made by the agent, not changes from setup commands.

        If the workspace has no git repo (e.g. from a local copy), one is
        initialized first. Returns the commit hash.
        """

        def _do_commit() -> str:
            w = str(workspace)

            if not (workspace / ".git").exists():
                subprocess.run(["git", "-C", w, "init"], check=True, capture_output=True)

            try:
                subprocess.run(
                    ["git", "-C", w, "add", "-A"],
                    check=True,
                    capture_output=True,
                    env=_GIT_ENV,
                )
                subprocess.run(
                    ["git", "-C", w, "commit", "-m", "post-setup snapshot", "--allow-empty"],
                    check=True,
                    capture_output=True,
                    env=_GIT_ENV,
                )
            except subprocess.CalledProcessError as e:
                raise SandboxError(
                    f"Failed to create post-setup snapshot commit: {e.stderr}"
                ) from e

            result = subprocess.run(
                ["git", "-C", w, "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()

        return await asyncio.to_thread(_do_commit)


__all__ = [
    "ExecResult",
    "FileDiff",
    "ResourceLimits",
    "Sandbox",
    "SandboxError",
    "SandboxManager",
    "SandboxStatus",
]
