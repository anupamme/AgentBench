"""Shared test fixtures for AgentBench."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_task_yaml() -> str:
    return '''
id: "test-task-001"
version: 1
metadata:
  difficulty: easy
  task_type: bug_fix
  languages: [python]
  estimated_human_time_minutes: 5
  tags: [test]
  source: "synthetic"
setup:
  repo: "https://github.com/test/repo"
  commit: "abc123"
  setup_commands:
    - "pip install -e ."
prompt: |
  Fix the bug in main.py so that the test passes.
evaluation:
  primary:
    type: test_suite
    command: "python -m pytest tests/ -x"
    pass_condition: "exit_code == 0"
constraints:
  max_turns: 10
  max_tokens: 50000
  timeout_seconds: 120
  network: false
'''
