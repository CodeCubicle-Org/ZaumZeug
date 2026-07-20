# Story: E3-S00
"""E3-S00 — Runtime factory builds a single Haystack Agent from harness config."""

from __future__ import annotations

from pathlib import Path

import yaml
from haystack.components.agents import Agent
from haystack.tools import ComponentTool

from zaumzeug.config.models import AgentModelsConfig
from zaumzeug.config.resolver import ARTIFACT_MANIFEST
from zaumzeug.integrations.mock import MockChatGenerator
from zaumzeug.runtime.factory import build_agent
from zaumzeug.runtime.model_router import ModelRouter


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _mock_router(tmp_path: Path) -> ModelRouter:
    return ModelRouter(
        AgentModelsConfig.model_validate(
            {
                "default_model_id": "mock",
                "models": {
                    "mock": {"provider": "mock", "model": "harness-fixture"},
                },
            }
        ),
        project_root=tmp_path,
    )


def _harness_layout(
    tmp_path: Path,
    *,
    tools_builtin: list[str] | None = None,
    prompt_text: str = "You are a researcher.",
    use_artifact: bool = False,
) -> Path:
    harness_dir = tmp_path / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"

    agent_section: dict = {"system_prompt": "prompts/system.md"}
    if use_artifact:
        artifact_dir = agent_dir / "artifacts" / "current"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / ARTIFACT_MANIFEST).write_text("{}", encoding="utf-8")
        prompt_path = artifact_dir / "prompts" / "system.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt_text, encoding="utf-8")
        agent_section = {"artifact": "artifacts/current"}

    agent_yaml: dict = {
        "name": "researcher",
        "default_model_id": "mock",
        "agent": agent_section,
    }
    if tools_builtin is not None:
        agent_yaml["tools"] = {"builtin": tools_builtin}

    _write_yaml(agent_dir / "agent.yaml", agent_yaml)

    if not use_artifact:
        prompt_path = agent_dir / "prompts" / "system.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt_text, encoding="utf-8")

    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    return harness_dir


def _tool_names(agent: Agent) -> list[str | None]:
    if agent.tools is None:
        return []
    return [
        tool.name if isinstance(tool, ComponentTool) else getattr(tool, "name", None)
        for tool in agent.tools
    ]


def test_e3_s00_ac1_builds_agent_from_config(tmp_path: Path) -> None:
    """AC-1: factory builds a Haystack Agent from harness config."""
    harness_dir = _harness_layout(tmp_path, tools_builtin=["web_fetch"])
    agent = build_agent(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert isinstance(agent, Agent)


def test_e3_s00_ac2_injects_model_router(tmp_path: Path) -> None:
    """AC-2: ModelRouter supplies the Agent chat generator backend."""
    harness_dir = _harness_layout(tmp_path)
    router = _mock_router(tmp_path)
    expected = router.build_generator("mock")

    agent = build_agent(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=router,
    )

    assert agent.chat_generator is expected
    assert isinstance(agent.chat_generator, MockChatGenerator)


def test_e3_s00_ac3_registers_builtin_tools(tmp_path: Path) -> None:
    """AC-3: tools.builtin from agent.yaml are registered on the Agent."""
    harness_dir = _harness_layout(tmp_path, tools_builtin=["web_fetch"])
    agent = build_agent(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert _tool_names(agent) == ["web_fetch"]


def test_e3_s00_ac4_loads_system_prompt_from_path(tmp_path: Path) -> None:
    """AC-4: system_prompt is loaded from the resolved file path (E2-S03)."""
    prompt = "You are the resolved system prompt."
    harness_dir = _harness_layout(tmp_path, prompt_text=prompt)
    agent = build_agent(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert agent.system_prompt == prompt


def test_e3_s00_ac6_single_agent_no_nested_loops(tmp_path: Path) -> None:
    """AC-6: factory returns exactly one Haystack Agent with no nested Agent tools."""
    harness_dir = _harness_layout(tmp_path, tools_builtin=["web_fetch"])
    agent = build_agent(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )

    assert isinstance(agent, Agent)
    assert not isinstance(agent.chat_generator, Agent)
    for tool in agent.tools or []:
        component = getattr(tool, "component", None)
        assert not isinstance(component, Agent)
        assert not isinstance(tool, Agent)


def test_e3_s03_ac4_yaml_builtin_reference(tmp_path: Path) -> None:
    """AC-4 (E3-S03): ``tools.builtin: [web_fetch]`` wires the catalog tool into the agent."""
    harness_dir = _harness_layout(tmp_path, tools_builtin=["web_fetch"])
    agent = build_agent(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert _tool_names(agent) == ["web_fetch"]
