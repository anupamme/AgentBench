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
import hashlib
import json
import shlex
import shutil
import subprocess
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import AsyncIterator

import docker
import docker.errors

from agentbench.core.models import TaskSpec


class SandboxStatus(str, Enum):
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


class SandboxError(Exception):
    """Raised on sandbox creation, execution, or teardown failures."""

    pass


# Files/dirs to exclude from snapshots
_SNAPSHOT_EXCLUDE_DIRS = {"node_modules", "__pycache__", ".git", ".venv"}
_SNAPSHOT_FILE = ".agentbench_snapshot.json"


class SandboxManager:
    """Manages Docker sandbox lifecycle for task evaluation."""

    DEFAULT_IMAGE = "python:3.12-slim"
    WORKSPACE_CONTAINER_PATH = "/workspace"

    def __init__(self, docker_client: docker.DockerClient | None = None) -> None:
        """
        Args:
            docker_client: Optional pre-configured Docker client.
                           If None, connects to the local Docker daemon.
        """
        self._client: docker.DockerClient = docker_client or docker.from_env()
        self._active_sandboxes: dict[str, Sandbox] = {}

    async def create(
        self, task: TaskSpec, resource_limits: ResourceLimits | None = None
    ) -> Sandbox:
        """Create and start a sandbox for the given task."""
        limits = resource_limits or ResourceLimits()
        # Override network from task constraints
        limits.network_enabled = task.constraints.network

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

            # Take initial filesystem snapshot
            await self._take_snapshot(host_workspace)

            sandbox.status = SandboxStatus.READY
            return sandbox

        except Exception:
            # Clean up temp dir on failure
            shutil.rmtree(host_workspace, ignore_errors=True)
            raise

    async def exec(self, sandbox: Sandbox, command: str, timeout: int = 60) -> ExecResult:
        """Execute a command inside the sandbox."""
        try:
            container = await asyncio.to_thread(
                self._client.containers.get, sandbox.container_id
            )
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
        """Compute the filesystem diff between the initial workspace state and current state."""
        snapshot_path = sandbox.host_workspace_path / _SNAPSHOT_FILE
        if not snapshot_path.exists():
            raise SandboxError("No snapshot found; was create() called?")

        with open(snapshot_path) as f:
            snapshot = json.load(f)

        old_files: dict[str, dict[str, str | int]] = snapshot.get("files", {})

        # Build current manifest
        current_files: dict[str, dict[str, str | int]] = {}
        workspace = sandbox.host_workspace_path
        for file_path in workspace.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(workspace)
            parts = rel.parts
            # Skip hidden files, snapshot file, and excluded dirs
            if any(p.startswith(".") for p in parts):
                continue
            if any(p in _SNAPSHOT_EXCLUDE_DIRS for p in parts):
                continue
            checksum = _sha256(file_path)
            current_files[str(rel)] = {"checksum": checksum, "size": file_path.stat().st_size}

        added = [k for k in current_files if k not in old_files]
        deleted = [k for k in old_files if k not in current_files]
        modified = [
            k
            for k in current_files
            if k in old_files and current_files[k]["checksum"] != old_files[k]["checksum"]
        ]

        # Build unified diffs for modified files
        raw_diff_parts: list[str] = []
        total_added = 0
        total_deleted = 0

        for rel_path in modified:
            file_path = workspace / rel_path
            old_checksum_entry = old_files[rel_path]
            # We don't have old content directly; use git diff or reconstruct
            # Since we don't store old content, we note the file changed
            # and produce a placeholder diff header
            try:
                old_content = _get_original_content(workspace, rel_path, snapshot)
                if old_content is not None:
                    new_content = file_path.read_text(errors="replace")
                    diff_output = _unified_diff(old_content, new_content, rel_path)
                    raw_diff_parts.append(diff_output)
                    for line in diff_output.splitlines():
                        if line.startswith("+") and not line.startswith("+++"):
                            total_added += 1
                        elif line.startswith("-") and not line.startswith("---"):
                            total_deleted += 1
            except Exception:
                pass  # best-effort diff

        return FileDiff(
            files_added=added,
            files_modified=modified,
            files_deleted=deleted,
            total_lines_added=total_added,
            total_lines_deleted=total_deleted,
            raw_diff="\n".join(raw_diff_parts),
        )

    async def teardown(self, sandbox: Sandbox) -> None:
        """Stop and remove the sandbox container. Clean up host workspace."""
        try:
            container = await asyncio.to_thread(
                self._client.containers.get, sandbox.container_id
            )
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
            try:
                await self.teardown(sandbox)
            except Exception:
                pass  # best-effort cleanup

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
            "network_disabled": not limits.network_enabled,
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
                    ["git", "clone", "--depth=100", repo_url, str(dest)],
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
                raise SandboxError(
                    f"Git operation failed: {e.cmd}\nstderr: {e.stderr}"
                ) from e

        await asyncio.to_thread(_do_clone)

    async def _take_snapshot(self, workspace: Path) -> None:
        """Walk the workspace directory and save file checksums to .agentbench_snapshot.json."""
        files: dict[str, dict[str, str | int]] = {}
        for file_path in workspace.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(workspace)
            parts = rel.parts
            if any(p.startswith(".") for p in parts):
                continue
            if any(p in _SNAPSHOT_EXCLUDE_DIRS for p in parts):
                continue
            checksum = _sha256(file_path)
            files[str(rel)] = {"checksum": checksum, "size": file_path.stat().st_size}

        snapshot = {
            "files": files,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        snapshot_path = workspace / _SNAPSHOT_FILE
        with open(snapshot_path, "w") as f:
            json.dump(snapshot, f, indent=2)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _get_original_content(
    workspace: Path, rel_path: str, snapshot: dict[str, object]
) -> str | None:
    """
    Retrieve the original file content.
    Since we don't store file content in the snapshot (only checksums),
    we check git for the original. Falls back to None.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace), "show", f"HEAD:{rel_path}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


def _unified_diff(old: str, new: str, filename: str) -> str:
    """Generate a unified diff between two strings."""
    import difflib

    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}"
    )
    return "".join(diff)


__all__ = [
    "ExecResult",
    "FileDiff",
    "ResourceLimits",
    "Sandbox",
    "SandboxError",
    "SandboxManager",
    "SandboxStatus",
]
