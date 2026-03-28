"""Tests for core Pydantic models and task loading."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import yaml
from pydantic import ValidationError

from agentbench.core.models import (
    Constraints,
    Difficulty,
    EvalCriterion,
    EvalType,
    TaskEvaluation,
    TaskMetadata,
    TaskSetup,
    TaskSpec,
    TaskType,
)
from agentbench.core.task_loader import TaskLoader, TaskLoadError

if TYPE_CHECKING:
    from pathlib import Path


# --- Model validation tests ---


class TestTaskSpec:
    def test_valid_minimal_task(self, sample_task_yaml: str) -> None:
        """A minimal valid task YAML should parse successfully."""
        raw = yaml.safe_load(sample_task_yaml)
        task = TaskSpec.model_validate(raw)
        assert task.id == "test-task-001"
        assert task.metadata.difficulty == Difficulty.EASY
        assert task.metadata.task_type == TaskType.BUG_FIX

    def test_invalid_id_format(self) -> None:
        """Task IDs must be kebab-case, starting with alphanumeric."""
        with pytest.raises(ValidationError):
            TaskSpec(
                id="Invalid ID!",
                version=1,
                metadata=TaskMetadata(
                    difficulty=Difficulty.EASY,
                    task_type=TaskType.BUG_FIX,
                    languages=["python"],
                    estimated_human_time_minutes=5,
                    source="test",
                ),
                setup=TaskSetup(repo="https://example.com", commit="abc"),
                prompt="Fix the bug in main.py.",
                evaluation=TaskEvaluation(
                    primary=EvalCriterion(
                        type=EvalType.TEST_SUITE,
                        command="pytest",
                        pass_condition="exit_code == 0",
                    )
                ),
            )

    def test_empty_languages_rejected(self) -> None:
        """At least one language must be specified."""
        with pytest.raises(ValidationError):
            TaskMetadata(
                difficulty=Difficulty.EASY,
                task_type=TaskType.BUG_FIX,
                languages=[],
                estimated_human_time_minutes=5,
                source="test",
            )

    def test_negative_time_rejected(self) -> None:
        """Estimated time must be positive."""
        with pytest.raises(ValidationError):
            TaskMetadata(
                difficulty=Difficulty.EASY,
                task_type=TaskType.BUG_FIX,
                languages=["python"],
                estimated_human_time_minutes=-1,
                source="test",
            )

    def test_default_constraints(self) -> None:
        """Default constraints should be applied when not specified."""
        c = Constraints()
        assert c.max_turns == 50
        assert c.max_tokens == 200000
        assert c.timeout_seconds == 600
        assert c.network is False

    def test_all_task_types_valid(self) -> None:
        """Every TaskType enum value should be a valid option."""
        for tt in TaskType:
            meta = TaskMetadata(
                difficulty=Difficulty.EASY,
                task_type=tt,
                languages=["python"],
                estimated_human_time_minutes=5,
                source="test",
            )
            assert meta.task_type == tt

    def test_all_difficulty_levels_valid(self) -> None:
        """Every Difficulty enum value should be a valid option."""
        for d in Difficulty:
            meta = TaskMetadata(
                difficulty=d,
                task_type=TaskType.BUG_FIX,
                languages=["python"],
                estimated_human_time_minutes=5,
                source="test",
            )
            assert meta.difficulty == d


class TestEvalCriterion:
    def test_test_suite_requires_command(self) -> None:
        """test_suite type must have a command."""
        with pytest.raises(ValidationError):
            EvalCriterion(type=EvalType.TEST_SUITE, pass_condition="exit_code == 0")

    def test_diff_size_requires_max_lines(self) -> None:
        """diff_size type must have max_lines_changed."""
        with pytest.raises(ValidationError):
            EvalCriterion(type=EvalType.DIFF_SIZE)

    def test_valid_test_suite(self) -> None:
        ec = EvalCriterion(
            type=EvalType.TEST_SUITE, command="pytest", pass_condition="exit_code == 0"
        )
        assert ec.type == EvalType.TEST_SUITE
        assert ec.command == "pytest"

    def test_valid_diff_size(self) -> None:
        ec = EvalCriterion(type=EvalType.DIFF_SIZE, max_lines_changed=30, label="small_diff")
        assert ec.max_lines_changed == 30


# --- TaskLoader tests ---


class TestTaskLoader:
    def test_load_valid_yaml(self, sample_task_yaml: str, tmp_path: Path) -> None:
        """Loading a valid YAML file should return a TaskSpec."""
        task_file = tmp_path / "task.yaml"
        task_file.write_text(sample_task_yaml)
        loader = TaskLoader()
        task = loader.load_task(task_file)
        assert task.id == "test-task-001"

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Loading a nonexistent file should raise TaskLoadError."""
        loader = TaskLoader()
        with pytest.raises(TaskLoadError):
            loader.load_task(tmp_path / "nonexistent.yaml")

    def test_load_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Malformed YAML should raise TaskLoadError."""
        task_file = tmp_path / "bad.yaml"
        task_file.write_text("{ invalid yaml: [")
        loader = TaskLoader()
        with pytest.raises(TaskLoadError):
            loader.load_task(task_file)

    def test_load_invalid_schema(self, tmp_path: Path) -> None:
        """Valid YAML but invalid schema should raise TaskLoadError."""
        task_file = tmp_path / "bad_schema.yaml"
        task_file.write_text("id: bad\nversion: 1\n")
        loader = TaskLoader()
        with pytest.raises(TaskLoadError):
            loader.load_task(task_file)

    def test_load_wrong_extension(self, tmp_path: Path) -> None:
        """Non-YAML extensions should be rejected."""
        task_file = tmp_path / "task.json"
        task_file.write_text("{}")
        loader = TaskLoader()
        with pytest.raises(TaskLoadError):
            loader.load_task(task_file)

    def test_load_directory(self, sample_task_yaml: str, tmp_path: Path) -> None:
        """Loading a directory should return all valid tasks."""
        for i in range(3):
            modified = sample_task_yaml.replace("test-task-001", f"test-task-{i:03d}")
            (tmp_path / f"task-{i}.yaml").write_text(modified)
        loader = TaskLoader()
        tasks = loader.load_directory(tmp_path)
        assert len(tasks) == 3

    def test_validate_only_returns_empty_for_valid(
        self, sample_task_yaml: str, tmp_path: Path
    ) -> None:
        task_file = tmp_path / "task.yaml"
        task_file.write_text(sample_task_yaml)
        loader = TaskLoader()
        errors = loader.validate_only(task_file)
        assert errors == []

    def test_validate_only_returns_errors_for_invalid(self, tmp_path: Path) -> None:
        task_file = tmp_path / "bad.yaml"
        task_file.write_text("id: x\n")
        loader = TaskLoader()
        errors = loader.validate_only(task_file)
        assert len(errors) > 0


# --- JSON Schema export tests ---


class TestSchemaExport:
    def test_export_produces_valid_json_schema(self) -> None:
        from agentbench.core.schema import export_task_schema

        schema = export_task_schema()
        assert "properties" in schema
        assert "id" in schema["properties"]
        assert schema["type"] == "object"

    def test_export_json_string(self) -> None:
        from agentbench.core.schema import export_task_schema_json

        json_str = export_task_schema_json()
        parsed = json.loads(json_str)
        assert "properties" in parsed
