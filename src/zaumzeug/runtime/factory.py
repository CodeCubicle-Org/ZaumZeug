"""Runtime factory — build Haystack agents from resolved harness config (E3-S00).

Optional Pattern A ``input_rewrite`` preprocess is loaded here (E4-S03b) and applied
by serve/run callers before ``Agent.run`` — no DSPy on this path.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from zaumzeug.runtime.preprocess import PreprocessError, load_input_rewrite_template
from zaumzeug.runtime.tools.catalog import build_builtin_tools
from zaumzeug.runtime.tools.custom import CustomToolError, build_custom_tools
from zaumzeug.runtime.tools.mcp import McpBoundaryError, build_mcp_toolsets

_ARTIFACT_SYSTEM_PROMPT = Path("prompts") / "system.md"


class RuntimeFactoryError(RuntimeError):
    """Raised when the runtime factory cannot build an agent."""


@dataclass(frozen=True, slots=True)
class BuiltAgent:
    """Factory output: Haystack agent plus optional input-rewrite template."""

    agent: Agent
    resolution: ServeResolution
    input_rewrite_template: str | None = None


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


def load_input_rewrite(resolution: ServeResolution) -> str | None:
    """Load optional ``input_rewrite`` template when serving from an artifact (E4-S03b).

    Returns ``None`` when the source is not an artifact or the manifest omits rewrite.
    Raises :class:`RuntimeFactoryError` when the manifest lists rewrite but the file
    is missing.
    """
    if resolution.source is not RuntimeSource.ARTIFACT:
        return None
    try:
        return load_input_rewrite_template(resolution.path)
    except PreprocessError as exc:
        raise RuntimeFactoryError(str(exc)) from exc


def _mcp_entries(agent_data: dict[str, Any]) -> list[Any]:
    tools_section = agent_data.get("tools")
    if not isinstance(tools_section, dict):
        return []
    mcp = tools_section.get("mcp")
    if not isinstance(mcp, list):
        return []
    return list(mcp)


def _custom_entries(agent_data: dict[str, Any]) -> list[Any]:
    tools_section = agent_data.get("tools")
    if not isinstance(tools_section, dict):
        return []
    custom = tools_section.get("custom")
    if not isinstance(custom, list):
        return []
    return list(custom)


def build_agent_tools(
    agent_data: dict[str, Any],
    *,
    agent_dir: Path | str | None = None,
) -> list[Any]:
    """Build Haystack tools from ``tools.builtin``, ``tools.mcp``, and ``tools.custom``."""
    tools: list[Any] = []
    tools.extend(build_builtin_tools(_builtin_tool_ids(agent_data)))
    try:
        tools.extend(build_mcp_toolsets(_mcp_entries(agent_data)))
    except McpBoundaryError as exc:
        raise RuntimeFactoryError(str(exc)) from exc
    custom_entries = _custom_entries(agent_data)
    if custom_entries:
        if agent_dir is None:
            raise RuntimeFactoryError(
                "tools.custom requires the agent directory to import modules"
            )
        try:
            tools.extend(build_custom_tools(custom_entries, agent_dir=agent_dir))
        except CustomToolError as exc:
            raise RuntimeFactoryError(str(exc)) from exc
    return tools


def build_agent_bundle(
    harness_dir: Path | str,
    *,
    harness_name: str,
    agent_name: str,
    router: ModelRouter,
) -> BuiltAgent:
    """Build a Haystack ``Agent`` and load optional input-rewrite template (E4-S03b)."""
    harness_dir = Path(harness_dir)
    resolution = resolve_agent_serve(
        harness_dir,
        harness_name=harness_name,
        agent_name=agent_name,
    )
    agent_config = load_agent_config(resolution.agent_yaml_path)
    tools = build_agent_tools(
        agent_config.model_dump(exclude_none=True),
        agent_dir=resolution.agent_yaml_path.parent,
    )
    system_prompt = load_system_prompt(resolution)
    input_rewrite_template = load_input_rewrite(resolution)
    chat_generator = router.build_generator(agent_config.default_model_id)

    agent = Agent(
        chat_generator=chat_generator,
        tools=tools or None,
        system_prompt=system_prompt,
    )
    return BuiltAgent(
        agent=agent,
        resolution=resolution,
        input_rewrite_template=input_rewrite_template,
    )


def build_agent(
    harness_dir: Path | str,
    *,
    harness_name: str,
    agent_name: str,
    router: ModelRouter,
) -> Agent:
    """Build a single Haystack ``Agent`` from harness config and a stage-scoped router.

    Shared by serve, MCP, and ACP (E3-S02+) — one factory, no nested agent loops.
    Uses ``resolve_agent_serve()`` (E2-S03), the builtin tool catalog (E3-S03),
    MCP toolsets (E7-S01), and custom tools from ``agents/<name>/tools/`` (E7-S02).
    Prefer :func:`build_agent_bundle` when the caller needs ``input_rewrite``.
    """
    return build_agent_bundle(
        harness_dir,
        harness_name=harness_name,
        agent_name=agent_name,
        router=router,
    ).agent
