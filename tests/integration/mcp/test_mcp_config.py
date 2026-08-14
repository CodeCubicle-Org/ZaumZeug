# Story: E7-S01 / E7.1
"""E7-S01 — ``tools.mcp`` YAML wires Haystack ``MCPToolset``."""

from __future__ import annotations

from pathlib import Path

import yaml
from haystack_integrations.tools.mcp import MCPToolset, StdioServerInfo

from zaumzeug.config.models import AgentModelsConfig
from zaumzeug.runtime.factory import build_agent
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.runtime.tools.mcp import MCP_DEFAULT_TIMEOUT_S


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _mcp_harness(tmp_path: Path) -> Path:
    harness_dir = tmp_path / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416, "mcp_port": 1417}}},
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
            "tools": {
                "builtin": ["web_fetch"],
                "mcp": [
                    {
                        "name": "filesystem",
                        "command": "uv",
                        "args": ["run", "mcp-server-filesystem", "/workspace"],
                    }
                ],
            },
        },
    )
    prompt = agent_dir / "prompts" / "system.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("You are a researcher.", encoding="utf-8")
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


def test_e7_s01_ac1_yaml_wires_mcp_toolset(tmp_path: Path) -> None:
    """AC-1: ``tools.mcp`` in yaml wires Haystack ``MCPToolset`` (deferred connect)."""
    harness_dir = _mcp_harness(tmp_path)
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

    mcp_toolsets = [tool for tool in agent.tools if isinstance(tool, MCPToolset)]
    assert len(mcp_toolsets) == 1
    toolset = mcp_toolsets[0]
    assert isinstance(toolset.server_info, StdioServerInfo)
    assert toolset.server_info.command == "uv"
    assert toolset.server_info.args == [
        "run",
        "mcp-server-filesystem",
        "/workspace",
    ]
    assert toolset.eager_connect is False
    assert toolset.connection_timeout == MCP_DEFAULT_TIMEOUT_S
    assert toolset.invocation_timeout == MCP_DEFAULT_TIMEOUT_S
