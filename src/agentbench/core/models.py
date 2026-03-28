"""
Core data models — Pydantic models for task specs, constraints, results, etc.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class TaskType(StrEnum):
    BUG_FIX = "bug_fix"
    FEATURE_ADD = "feature_add"
    REFACTOR = "refactor"
    TEST_GENERATION = "test_generation"
    DEPENDENCY_UPGRADE = "dependency_upgrade"
    DEBUG_FROM_LOGS = "debug_from_logs"
    MULTI_FILE_EDIT = "multi_file_edit"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"


class TaskMetadata(BaseModel):
    difficulty: Difficulty
    task_type: TaskType
    languages: list[str] = Field(min_length=1, description="Programming languages involved")
    estimated_human_time_minutes: int = Field(gt=0)
    tags: list[str] = Field(default_factory=list)
    source: str = Field(description="Origin of the task: issue URL, 'synthetic', etc.")


class TaskSetup(BaseModel):
    repo: str = Field(description="Git repo URL or local path to a repo snapshot tarball")
    commit: str = Field(description="Git commit hash to checkout")
    dockerfile: str | None = Field(
        default=None, description="Path to custom Dockerfile relative to task dir"
    )
    setup_commands: list[str] = Field(
        default_factory=list, description="Shell commands to run before agent starts"
    )
    files_to_highlight: list[str] = Field(
        default_factory=list, description="Hint files for the agent — not enforced"
    )


class EvalType(StrEnum):
    TEST_SUITE = "test_suite"
    LINT = "lint"
    TYPE_CHECK = "type_check"
    DIFF_SIZE = "diff_size"
    CUSTOM_SCRIPT = "custom_script"


class EvalCriterion(BaseModel):
    type: EvalType
    command: str | None = Field(
        default=None, description="Shell command to run for this evaluation"
    )
    pass_condition: str | None = Field(
        default=None, description="Condition to check: 'exit_code == 0', etc."
    )
    max_lines_changed: int | None = Field(
        default=None, description="For diff_size type: max allowed lines changed"
    )
    label: str = Field(default="", description="Human-readable label for reporting")
    timeout_seconds: int = Field(default=300, description="Timeout for this eval criterion")

    @model_validator(mode="after")
    def validate_type_fields(self) -> EvalCriterion:
        """Ensure required fields are present based on eval type."""
        command_required = (
            EvalType.TEST_SUITE,
            EvalType.LINT,
            EvalType.TYPE_CHECK,
            EvalType.CUSTOM_SCRIPT,
        )
        if self.type in command_required and not self.command:
            raise ValueError(f"'command' is required for eval type '{self.type.value}'")
        if self.type == EvalType.DIFF_SIZE and self.max_lines_changed is None:
            raise ValueError("'max_lines_changed' is required for eval type 'diff_size'")
        return self


class TaskEvaluation(BaseModel):
    primary: EvalCriterion = Field(description="Primary pass/fail criterion — usually a test suite")
    secondary: list[EvalCriterion] = Field(
        default_factory=list, description="Additional quality checks"
    )


class Constraints(BaseModel):
    max_turns: int = Field(default=50, gt=0, description="Maximum agent interaction turns")
    max_tokens: int = Field(default=200000, gt=0, description="Total token budget (input + output)")
    timeout_seconds: int = Field(default=600, gt=0, description="Wall clock time limit in seconds")
    network: bool = Field(
        default=False, description="Whether the agent has internet access during solve"
    )


class TaskSpec(BaseModel):
    id: str = Field(
        pattern=r"^[a-z0-9][a-z0-9\-]{2,80}$", description="Unique task identifier, kebab-case"
    )
    version: int = Field(ge=1, description="Schema version for forward compat")
    metadata: TaskMetadata
    setup: TaskSetup
    prompt: str = Field(min_length=10, description="The task description given to the agent")
    evaluation: TaskEvaluation
    constraints: Constraints = Field(default_factory=Constraints)


__all__ = [
    "Constraints",
    "Difficulty",
    "EvalCriterion",
    "EvalType",
    "TaskEvaluation",
    "TaskMetadata",
    "TaskSetup",
    "TaskSpec",
    "TaskType",
]
