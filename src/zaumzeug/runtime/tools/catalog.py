"""Phase-aware builtin tool catalog (Architecture §6.5)."""

from __future__ import annotations

from typing import Any, Callable

from zaumzeug.config.builtins import (
    BUILTIN_TOOL_PHASES,
    BuiltinToolValidationError,
    available_builtin_tool_ids,
    validate_builtin_tool_ids,
)
from zaumzeug.runtime.tools.web_fetch import build_web_fetch_tool

BuiltinToolFactory = Callable[..., Any]

BUILTIN_TOOL_FACTORIES: dict[str, BuiltinToolFactory] = {
    "web_fetch": build_web_fetch_tool,
}

# Re-export config-layer validation under the runtime catalog name.
BuiltinToolCatalogError = BuiltinToolValidationError

__all__ = [
    "BUILTIN_TOOL_PHASES",
    "BuiltinToolCatalogError",
    "available_builtin_tool_ids",
    "build_builtin_tools",
    "create_builtin_tool",
    "validate_builtin_tool_ids",
]


def create_builtin_tool(tool_id: str, **kwargs: Any) -> Any:
    """Instantiate a Haystack tool for a catalog *tool_id*."""
    validate_builtin_tool_ids([tool_id])
    factory = BUILTIN_TOOL_FACTORIES.get(tool_id)
    if factory is None:
        from zaumzeug.config.constants import CURRENT_SDK_PHASE

        available = available_builtin_tool_ids()
        raise BuiltinToolCatalogError(
            f"builtin tool {tool_id!r} is not implemented; "
            f"available for Phase {CURRENT_SDK_PHASE}: {available}"
        )
    return factory(**kwargs)


def build_builtin_tools(
    tool_ids: list[str],
    *,
    phase: int | None = None,
    **kwargs: Any,
) -> list[Any]:
    """Build Haystack tools for validated builtin ids from agent config."""
    from zaumzeug.config.constants import CURRENT_SDK_PHASE

    resolved_phase = CURRENT_SDK_PHASE if phase is None else phase
    validate_builtin_tool_ids(tool_ids, phase=resolved_phase)
    return [create_builtin_tool(tool_id, **kwargs) for tool_id in tool_ids]
