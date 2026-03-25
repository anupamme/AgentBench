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


class SandboxManager:
    async def create(self, task: object) -> Sandbox:
        raise NotImplementedError

    async def exec(self, sandbox: Sandbox, command: str, timeout: int = 60) -> ExecResult:
        raise NotImplementedError

    async def snapshot_diff(self, sandbox: Sandbox) -> FileDiff:
        raise NotImplementedError

    async def teardown(self, sandbox: Sandbox) -> None:
        raise NotImplementedError


class Sandbox:
    """Represents a running sandbox environment."""

    pass


class ExecResult:
    """Result of executing a command inside a sandbox."""

    pass


class FileDiff:
    """Filesystem diff between two workspace snapshots."""

    pass
