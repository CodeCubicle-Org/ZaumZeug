# Story: E7-S05 / E7.5
"""E7-S05 — ``zaumzeug acp`` stdio JSON-RPC (Agent Client Protocol)."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from haystack_integrations.tools.mcp import MCPToolset, StdioServerInfo

from zaumzeug.serve.acp import (
    ACP_PROTOCOL_VERSION,
    AcpSessionServer,
    prepare_acp,
    serve_stdio,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_ACP_GUIDE = REPO_ROOT / "user-docs" / "guides" / "acp.md"
TEMPLATE_ACP_GUIDE = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "guides" / "acp.md"
)
LIVE_CLI = REPO_ROOT / "user-docs" / "reference" / "cli.md"
TEMPLATE_CLI = REPO_ROOT / "install" / "templates" / "user-docs" / "reference" / "cli.md"


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _acp_harness(
    project_root: Path,
    *,
    mcp: bool = False,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": "example",
            "serve": {
                "hayhooks": {"port": 1416, "mcp_port": 1417},
                "acp": {"enabled": True},
            },
        },
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"
    tools: dict = {"builtin": ["web_fetch"]}
    if mcp:
        tools["mcp"] = [
            {
                "name": "filesystem",
                "command": "uv",
                "args": ["run", "mcp-server-filesystem", "/workspace"],
            }
        ]
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": tools,
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
    fixtures = project_root / "tests" / "fixtures" / "responses"
    fixtures.mkdir(parents=True, exist_ok=True)
    src = REPO_ROOT / "tests" / "fixtures" / "responses" / "harness-fixture.txt"
    if src.is_file():
        (fixtures / "harness-fixture.txt").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return harness_dir


def _prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, mcp: bool = False):
    project_root = tmp_path / "project"
    _acp_harness(project_root, mcp=mcp)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    monkeypatch.chdir(project_root)
    return prepare_acp("example", project_root=project_root)


def _initialize_payload(msg_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "initialize",
        "params": {
            "protocolVersion": ACP_PROTOCOL_VERSION,
            "clientCapabilities": {},
            "clientInfo": {"name": "zaumzeug-test", "version": "0.1.0"},
        },
    }


def test_e7_s05_ac1_starts_stdio_jsonrpc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: ``zaumzeug acp <name>`` starts a stdio JSON-RPC process."""
    prepared = _prepare(tmp_path, monkeypatch)
    server = AcpSessionServer(prepared)
    replies = server.handle_message(_initialize_payload())
    assert len(replies) == 1
    body = replies[0]
    assert body["jsonrpc"] == "2.0"
    assert body["id"] == 1
    result = body["result"]
    assert result["protocolVersion"] == ACP_PROTOCOL_VERSION
    assert result["agentInfo"]["name"] == "zaumzeug-example"
    assert "authMethods" in result

    session = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "session/new",
            "params": {"cwd": str(tmp_path), "mcpServers": []},
        }
    )
    assert session[0]["result"]["sessionId"]

    reader = io.StringIO(json.dumps(_initialize_payload(0)) + "\n")
    writer = io.StringIO()
    serve_stdio(prepared, reader=reader, writer=writer)
    line = writer.getvalue().splitlines()[0]
    framed = json.loads(line)
    assert framed["jsonrpc"] == "2.0"
    assert framed["result"]["protocolVersion"] == ACP_PROTOCOL_VERSION

    project_root = tmp_path / "project"
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    src = str(REPO_ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not existing else os.pathsep.join([src, existing])
    proc = subprocess.Popen(
        [sys.executable, "-m", "zaumzeug.cli", "acp", "example"],
        cwd=str(project_root),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        stdout, stderr = proc.communicate(
            json.dumps(_initialize_payload()) + "\n",
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        pytest.fail(f"acp process timed out; stderr={stderr!r}")

    assert "Agent Client Protocol" in stderr
    lines = [line for line in stdout.splitlines() if line.strip()]
    assert lines, f"expected JSON-RPC on stdout; stderr={stderr!r}"
    cli_body = json.loads(lines[0])
    assert cli_body["jsonrpc"] == "2.0"
    assert cli_body["result"]["protocolVersion"] == ACP_PROTOCOL_VERSION


def test_e7_s05_ac2_docs_include_zed_jetbrains_snippets() -> None:
    """AC-2: docs include Zed and JetBrains ACP registration snippets."""
    for path in (LIVE_ACP_GUIDE, TEMPLATE_ACP_GUIDE, LIVE_CLI, TEMPLATE_CLI):
        text = path.read_text(encoding="utf-8")
        assert "agent_servers" in text, f"{path} must include agent_servers"
        assert "zaumzeug" in text and "acp" in text
        assert '"command"' in text or "`command`" in text
        assert "Zed" in text
        assert "JetBrains" in text
        assert "~/.jetbrains/acp.json" in text or ".jetbrains/acp.json" in text


def test_e7_s05_ac3_docs_disambiguate_acp_vs_a2a() -> None:
    """AC-3: docs disambiguate Agent Client Protocol vs IBM ACP / A2A."""
    for path in (LIVE_ACP_GUIDE, TEMPLATE_ACP_GUIDE):
        text = path.read_text(encoding="utf-8")
        assert "Agent Client Protocol" in text
        assert "A2A" in text
        assert "IBM" in text
        assert "Cursor" in text
        assert "MCP" in text


def test_e7_s05_ac4_internal_mcp_still_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: ACP path still wires ``tools.mcp`` as Haystack ``MCPToolset``."""
    prepared = _prepare(tmp_path, monkeypatch, mcp=True)
    mcp_toolsets = [
        tool for tool in (prepared.agent.tools or []) if isinstance(tool, MCPToolset)
    ]
    assert len(mcp_toolsets) == 1
    toolset = mcp_toolsets[0]
    assert isinstance(toolset.server_info, StdioServerInfo)
    assert toolset.server_info.command == "uv"
    assert toolset.eager_connect is False
