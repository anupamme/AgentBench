"""
End-to-end integration test: task → sandbox → agent → trace → results.

Requires Docker to be running. Uses the calc-fix-division-by-zero seed task
and a mock adapter that applies the known-good fix.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentbench.adapters.mock import MockAdapter
from agentbench.core.task_loader import TaskLoader
from agentbench.sandbox.manager import SandboxManager
from agentbench.trace.collector import TraceCollector
from agentbench.trace.events import EventType

pytestmark = pytest.mark.docker

TASKS_DIR = Path(__file__).parent.parent / "tasks"


# The known-good fix for calc-fix-division-by-zero
CALC_FIX_CONTENT = '''"""Simple calculator module."""


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''


@pytest.fixture
def calc_task():
    loader = TaskLoader()
    return loader.load_task(TASKS_DIR / "calc-fix-division-by-zero" / "task.yaml")


@pytest.fixture
def sandbox_manager():
    return SandboxManager()


@pytest.fixture
def correct_fix_script():
    """A mock script that applies the correct fix."""
    return [
        {"type": "bash", "command": "cat calc.py"},
        {"type": "bash", "command": "python -m pytest tests/test_calc.py -v"},
        {"type": "file_write", "path": "calc.py", "content": CALC_FIX_CONTENT},
        {"type": "bash", "command": "python -m pytest tests/test_calc.py -v"},
        {"type": "done"},
    ]


@pytest.fixture
def wrong_fix_script():
    """A mock script that applies an incorrect fix."""
    return [
        {"type": "file_write", "path": "calc.py", "content": "def divide(a, b): return 0"},
        {"type": "done"},
    ]


class TestEndToEndPipeline:
    async def test_full_pipeline_with_correct_fix(
        self, calc_task, sandbox_manager, correct_fix_script
    ):
        """
        Full pipeline test:
        1. Load task
        2. Create sandbox
        3. Run mock agent with correct fix
        4. Verify trace has expected events
        5. Run evaluation command and verify tests pass
        6. Save trace to disk and reload it
        """
        trace = TraceCollector(
            run_id="e2e-test-001",
            task_id=calc_task.id,
            agent_name="mock",
        )
        adapter = MockAdapter(correct_fix_script)

        async with sandbox_manager.session(calc_task) as sandbox:
            # Run the agent
            result = await adapter.solve(calc_task, sandbox, sandbox_manager, trace)

            # Verify agent result
            assert result.completed is True
            assert result.reason == "completed"

            # Verify trace has expected events
            event_types = [e.event_type for e in trace.events]
            assert EventType.AGENT_START in event_types
            assert EventType.AGENT_DONE in event_types
            assert EventType.COMMAND_EXEC in event_types
            assert EventType.FILE_WRITE in event_types

            # Run the evaluation command
            eval_result = await sandbox_manager.exec(
                sandbox,
                calc_task.evaluation.primary.command,
                timeout=60,
            )
            assert (
                eval_result.exit_code == 0
            ), f"Tests failed:\n{eval_result.stdout}\n{eval_result.stderr}"

        # Verify trace serialization round-trips
        summary = trace.summary()
        assert summary.total_events > 0
        assert summary.commands_executed > 0

        json_str = trace.to_json()
        parsed = json.loads(json_str)
        assert parsed["run_id"] == "e2e-test-001"
        assert len(parsed["events"]) == trace.event_count

    async def test_full_pipeline_with_wrong_fix(self, calc_task, sandbox_manager, wrong_fix_script):
        """Wrong fix should result in failing tests."""
        trace = TraceCollector(run_id="e2e-test-002", task_id=calc_task.id, agent_name="mock")
        adapter = MockAdapter(wrong_fix_script)

        async with sandbox_manager.session(calc_task) as sandbox:
            result = await adapter.solve(calc_task, sandbox, sandbox_manager, trace)
            assert result.completed is True

            # Run eval — should fail
            eval_result = await sandbox_manager.exec(
                sandbox,
                calc_task.evaluation.primary.command,
                timeout=60,
            )
            assert eval_result.exit_code != 0

    async def test_trace_save_and_load(
        self, calc_task, sandbox_manager, correct_fix_script, tmp_path
    ):
        """Trace should save to disk and load back identically."""
        trace = TraceCollector(run_id="e2e-test-003", task_id=calc_task.id, agent_name="mock")
        adapter = MockAdapter(correct_fix_script)

        async with sandbox_manager.session(calc_task) as sandbox:
            await adapter.solve(calc_task, sandbox, sandbox_manager, trace)

        # Save
        trace_path = tmp_path / "trace.json"
        trace.save(trace_path)
        assert trace_path.exists()

        # Load
        loaded = TraceCollector.load(trace_path)
        assert loaded.run_id == trace.run_id
        assert loaded.event_count == trace.event_count
        assert loaded.events[0].event_type == trace.events[0].event_type

    async def test_filesystem_diff_after_fix(self, calc_task, sandbox_manager, correct_fix_script):
        """After applying a fix, snapshot_diff should show calc.py as modified."""
        trace = TraceCollector(run_id="e2e-test-004", task_id=calc_task.id, agent_name="mock")
        adapter = MockAdapter(correct_fix_script)

        async with sandbox_manager.session(calc_task) as sandbox:
            await adapter.solve(calc_task, sandbox, sandbox_manager, trace)
            diff = await sandbox_manager.snapshot_diff(sandbox)
            assert "calc.py" in diff.files_modified
