"""
Adapter Registry — discovers and instantiates agent adapters by name.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentbench.adapters.base import AgentAdapter, AgentConfig


class AdapterNotFoundError(Exception):
    pass


# Registry of known adapters: name → import path
_ADAPTER_REGISTRY: dict[str, str] = {
    "anthropic-api": "agentbench.adapters.anthropic_api:AnthropicAPIAdapter",
    "claude-code": "agentbench.adapters.claude_code:ClaudeCodeAdapter",
    "mock": "agentbench.adapters.mock:MockAdapter",
}


def get_adapter(name: str, config: AgentConfig | None = None) -> AgentAdapter:
    """
    Get an adapter instance by name.

    Lazily imports the adapter class to avoid heavy dependencies at startup.
    """
    if name not in _ADAPTER_REGISTRY:
        available = ", ".join(sorted(_ADAPTER_REGISTRY.keys()))
        raise AdapterNotFoundError(f"Unknown adapter '{name}'. Available: {available}")

    module_path, class_name = _ADAPTER_REGISTRY[name].rsplit(":", 1)
    module = importlib.import_module(module_path)
    adapter_class = getattr(module, class_name)
    return adapter_class(config=config)  # type: ignore[no-any-return]


def list_adapters() -> list[str]:
    """Return names of all registered adapters."""
    return sorted(_ADAPTER_REGISTRY.keys())


def register_adapter(name: str, import_path: str) -> None:
    """Register a custom adapter. import_path format: 'module.path:ClassName'"""
    _ADAPTER_REGISTRY[name] = import_path
