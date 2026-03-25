"""
Schema Export — generates JSON Schema from Pydantic models.

Used for external validation and documentation.
"""
from __future__ import annotations

import json

from agentbench.core.models import TaskSpec


def export_task_schema() -> dict:  # type: ignore[type-arg]
    """Return the JSON Schema for TaskSpec."""
    return TaskSpec.model_json_schema()


def export_task_schema_json(indent: int = 2) -> str:
    """Return the JSON Schema as a formatted JSON string."""
    return json.dumps(export_task_schema(), indent=indent)
