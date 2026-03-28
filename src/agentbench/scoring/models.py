"""Score dataclasses for the multi-dimensional scoring pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CorrectnessResult:
    """Functional correctness evaluation."""
    primary_pass: bool                           # Did the primary eval criterion pass?
    primary_output: str = ""                     # stdout from the primary eval command
    primary_exit_code: int = -1
    partial_score: float = 0.0                   # 0.0–1.0, fraction of tests passing
    secondary_results: list[SecondaryResult] = field(default_factory=list)


@dataclass
class SecondaryResult:
    label: str
    passed: bool
    output: str = ""
    exit_code: int = -1


@dataclass
class QualityResult:
    """Code quality evaluation."""
    lint_clean: bool = True
    lint_errors: int = 0
    lint_output: str = ""
    type_check_clean: bool = True
    type_check_errors: int = 0
    diff_lines_changed: int = 0
    diff_lines_added: int = 0
    diff_lines_deleted: int = 0
    diff_within_budget: bool = True              # True if diff_size secondary eval passed


@dataclass
class EfficiencyResult:
    """Resource efficiency evaluation."""
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    total_turns: int = 0
    total_tool_calls: int = 0
    wall_clock_seconds: float = 0.0
    files_read_count: int = 0
    files_written_count: int = 0
    commands_executed: int = 0
    # Derived ratios
    tokens_per_turn: float = 0.0
    # files_read that were in files_to_highlight / total files_read
    relevant_file_read_ratio: float = 0.0


@dataclass
class ProcessResult:
    """Process quality — did the agent follow good engineering practices?"""
    read_before_edit: bool = False        # Did the agent read relevant files before editing them?
    ran_tests_before_done: bool = False   # Did the agent run tests at least once before finishing?
    iterated_on_failure: bool = False     # If tests failed, did the agent try again?
    explored_codebase: bool = False       # Did the agent read more than just the highlighted files?
    test_run_count: int = 0               # How many times did the agent run tests?


@dataclass
class TaskScore:
    """Complete multi-dimensional score for a single task run."""
    task_id: str
    agent_name: str
    run_id: str
    correctness: CorrectnessResult
    quality: QualityResult
    efficiency: EfficiencyResult
    process: ProcessResult
    overall_pass: bool = False                   # shorthand: correctness.primary_pass

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict using dataclasses.asdict."""
        from dataclasses import asdict
        return asdict(self)
