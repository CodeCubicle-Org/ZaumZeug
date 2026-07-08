"""Runtime factory — build Haystack agents from resolved harness config (E3-S00)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from haystack.components.agents import Agent

from zaumzeug.config.loader import load_agent_config
from zaumzeug.config.resolver import ServeResolution, resolve_agent_serve
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.runtime.tools.catalog import build_builtin_tools


def _builtin_tool_ids(agent_data: dict[str, Any]) -> list[str]:
    tools_section = agent_data.get("tools")
    if not isinstance(tools_section, dict):
        return []
    builtin = tools_section.get("builtin")
    if not isinstance(builtin, list):
        return []
    return [str(item) for item in builtin]


def load_system_prompt(resolution: ServeResolution) -> str:
    """Read the resolved system prompt file for serve/run."""
    return resolution.path.read_text(encoding="utf-8")


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
    """Build a Haystack ``Agent`` from harness config and a stage-scoped router."""
    harness_dir = Path(harness_dir)
    resolution = resolve_agent_serve(
        harness_dir,
        harness_name=harness_name,
        agent_name=agent_name,
    )
    agent_config = load_agent_config(resolution.agent_yaml_path)
    tools = build_agent_tools(agent_config.model_dump(exclude_none=True))
    system_prompt = load_system_prompt(resolution)

    return Agent(
        chat_generator=router.build_generator(),
        tools=tools or None,
        system_prompt=system_prompt,
    )
