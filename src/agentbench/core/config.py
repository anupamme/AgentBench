"""
Configuration — loads and manages global configuration.

Supports loading from environment variables and YAML config files.
"""

from __future__ import annotations


class Config:
    """Global configuration for AgentBench."""

    @classmethod
    def load(cls, config_path: str | None = None) -> Config:
        raise NotImplementedError
