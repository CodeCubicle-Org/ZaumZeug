# Story: E3-S03 / E3.3
"""E3-S03 — ``web_fetch`` referenced from agent yaml via runtime factory."""

from __future__ import annotations

from pathlib import Path

import yaml
from haystack.tools import ComponentTool

from zaumzeug.config.models import AgentModelsConfig
from zaumzeug.runtime.factory import build_agent
from zaumzeug.runtime.model_router import ModelRouter


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _harness_layout(tmp_path: Path) -> Path:
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
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": {"builtin": ["web_fetch"]},
        },
    )
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("You are a researcher.", encoding="utf-8")
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


def test_e3_s03_ac4_yaml_builtin_reference(tmp_path: Path) -> None:
    """AC-4: ``tools.builtin: [web_fetch]`` wires the catalog tool into the agent."""
    harness_dir = _harness_layout(tmp_path)
    router = ModelRouter(
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

    agent = build_agent(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=router,
    )

    assert agent.tools is not None
    tool_names = [
        tool.name if isinstance(tool, ComponentTool) else getattr(tool, "name", None)
        for tool in agent.tools
    ]
    assert tool_names == ["web_fetch"]
