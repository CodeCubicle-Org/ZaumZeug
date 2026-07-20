"""Runtime factory — build Haystack agents from resolved harness config (E3-S00)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from haystack.components.agents import Agent

from zaumzeug.config.loader import load_agent_config
from zaumzeug.config.resolver import (
    ARTIFACT_MANIFEST,
    RuntimeSource,
    ServeResolution,
    resolve_agent_serve,
)
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.runtime.tools.catalog import build_builtin_tools

_ARTIFACT_SYSTEM_PROMPT = Path("prompts") / "system.md"


class RuntimeFactoryError(RuntimeError):
    """Raised when the runtime factory cannot build an agent."""


def _builtin_tool_ids(agent_data: dict[str, Any]) -> list[str]:
    tools_section = agent_data.get("tools")
    if not isinstance(tools_section, dict):
        return []
    builtin = tools_section.get("builtin")
    if not isinstance(builtin, list):
        return []
    return [str(item) for item in builtin]


def load_system_prompt(resolution: ServeResolution) -> str:
    """Load the system prompt text for the resolved serve/run source.

    * ``system_prompt`` — ``resolution.path`` is the prompt file (E2-S03).
    * ``artifact`` — ``resolution.path`` is the artifact directory; read
      ``prompts/system.md`` per Architecture §5.3.
    """
    if resolution.source is RuntimeSource.SYSTEM_PROMPT:
        if not resolution.path.is_file():
            raise RuntimeFactoryError(
                f"system_prompt file not found: {resolution.path}"
            )
        return resolution.path.read_text(encoding="utf-8")

    if resolution.source is RuntimeSource.ARTIFACT:
        prompt_path = resolution.path / _ARTIFACT_SYSTEM_PROMPT
        if not prompt_path.is_file():
            raise RuntimeFactoryError(
                f"artifact at {resolution.path} is missing {_ARTIFACT_SYSTEM_PROMPT} "
                f"(expected beside {ARTIFACT_MANIFEST})"
            )
        return prompt_path.read_text(encoding="utf-8")

    raise RuntimeFactoryError(f"unsupported runtime source: {resolution.source!r}")


def build_agent_tools(agent_data: dict[str, Any]) -> list[Any]:
    """Build Haystack tools from ``tools.builtin`` in agent config."""
    return build_builtin_tools(_builtin_tool_ids(agent_data))


def build_agent(
    harness_dir: Path | str,
    *,
    harness_name: str,
    agent_name: str,
    router: ModelRouter,
) -> Agent:
    """Build a single Haystack ``Agent`` from harness config and a stage-scoped router.

    Shared by serve, MCP, and ACP (E3-S02+) — one factory, no nested agent loops.
    Uses ``resolve_agent_serve()`` (E2-S03) and the builtin tool catalog (E3-S03).
    """
    harness_dir = Path(harness_dir)
    resolution = resolve_agent_serve(
        harness_dir,
        harness_name=harness_name,
        agent_name=agent_name,
    )
    agent_config = load_agent_config(resolution.agent_yaml_path)
    tools = build_agent_tools(agent_config.model_dump(exclude_none=True))
    system_prompt = load_system_prompt(resolution)
    chat_generator = router.build_generator(agent_config.default_model_id)

    return Agent(
        chat_generator=chat_generator,
        tools=tools or None,
        system_prompt=system_prompt,
    )
