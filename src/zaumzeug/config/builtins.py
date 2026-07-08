"""Builtin tool catalog metadata and validation (Architecture §6.5)."""

from __future__ import annotations

from zaumzeug.config.constants import CURRENT_SDK_PHASE

# Tool id → minimum SDK phase that ships the builtin.
BUILTIN_TOOL_PHASES: dict[str, int] = {
    "web_fetch": 1,
    "calculator": 3,
    "read_file": 3,
    "search_docs": 4,
}


class BuiltinToolValidationError(ValueError):
    """Raised when agent config references an unknown builtin tool id."""


def available_builtin_tool_ids(*, phase: int = CURRENT_SDK_PHASE) -> list[str]:
    """Return builtin tool ids available in *phase*, sorted for stable error messages."""
    return sorted(
        tool_id
        for tool_id, min_phase in BUILTIN_TOOL_PHASES.items()
        if min_phase <= phase
    )


def validate_builtin_tool_ids(
    tool_ids: list[str],
    *,
    phase: int = CURRENT_SDK_PHASE,
) -> None:
    """Raise :class:`BuiltinToolValidationError` when any id is unknown for *phase*."""
    if not tool_ids:
        return

    available = available_builtin_tool_ids(phase=phase)
    unknown = [tool_id for tool_id in tool_ids if tool_id not in available]
    if not unknown:
        return

    raise BuiltinToolValidationError(
        f"unknown builtin tool id(s) {unknown!r}; "
        f"available for Phase {phase}: {available}"
    )
