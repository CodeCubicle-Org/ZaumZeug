# Story: E7-S01 / E7.1
"""E7-S01 — ``zaumzeug mcp`` endpoint and consistent MCP error shape."""

from __future__ import annotations

from pathlib import Path

import yaml
from starlette.testclient import TestClient

from zaumzeug.runtime.tools.mcp import MCP_ERROR_KEY, MCP_ERROR_OK_KEY
from zaumzeug.serve.mcp import JSONRPC_INVALID_REQUEST, JSONRPC_PARSE_ERROR, prepare_mcp

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _mcp_harness(project_root: Path, *, mcp_port: int = 1417) -> Path:
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": "example",
            "serve": {"hayhooks": {"port": 1416, "mcp_port": mcp_port}},
        },
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
    fixtures.mkdir(parents=True)
    src = REPO_ROOT / "tests" / "fixtures" / "responses" / "harness-fixture.txt"
    if src.is_file():
        (fixtures / "harness-fixture.txt").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return harness_dir


def _prepare(tmp_path: Path, monkeypatch, *, mcp_port: int = 1417):
    project_root = tmp_path / "project"
    _mcp_harness(project_root, mcp_port=mcp_port)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    monkeypatch.chdir(project_root)
    return prepare_mcp("example", project_root=project_root, port=mcp_port)


def test_e7_s01_ac2_mcp_endpoint_serves(tmp_path: Path, monkeypatch) -> None:
    """AC-2: ``zaumzeug mcp`` serves MCP at ``{host}:{mcp_port}/mcp``."""
    prepared = _prepare(tmp_path, monkeypatch, mcp_port=1417)
    assert prepared.port == 1417
    assert prepared.host in {"127.0.0.1", "localhost"}

    with TestClient(prepared.app) as client:
        status = client.get("/status")
        assert status.status_code == 200
        assert status.json() == {"status": "ok"}

        init = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "zaumzeug-test", "version": "0.1.0"},
                },
            },
            headers={"accept": "application/json, text/event-stream"},
        )
        assert init.status_code == 200
        body = init.json()
        assert body.get("jsonrpc") == "2.0"
        if "result" in body:
            assert "protocolVersion" in body["result"] or "serverInfo" in body["result"]
        else:
            assert "error" not in body or body.get("id") == 1


def test_e7_s01_ac4_error_shape_consistent(tmp_path: Path, monkeypatch) -> None:
    """AC-4: MCP errors return JSON-RPC + Architecture envelope (``error.data``)."""
    prepared = _prepare(tmp_path, monkeypatch)

    with TestClient(prepared.app) as client:
        parse = client.post(
            "/mcp",
            content=b"not-json{",
            headers={"content-type": "application/json"},
        )
        assert parse.status_code == 200
        _assert_mcp_error_shape(parse.json(), expected_code=JSONRPC_PARSE_ERROR)

        invalid = client.post("/mcp", json={"jsonrpc": "2.0", "id": 7})
        assert invalid.status_code == 200
        invalid_body = invalid.json()
        _assert_mcp_error_shape(invalid_body, expected_code=JSONRPC_INVALID_REQUEST)
        assert invalid_body["id"] == 7


def _assert_mcp_error_shape(body: dict, *, expected_code: int) -> None:
    assert body["jsonrpc"] == "2.0"
    error = body["error"]
    assert isinstance(error["code"], int)
    assert error["code"] == expected_code
    assert isinstance(error["message"], str)
    assert error["message"]
    data = error["data"]
    assert data[MCP_ERROR_OK_KEY] is False
    inner = data[MCP_ERROR_KEY]
    assert inner["type"]
    assert inner["message"]
    assert inner["code"] == expected_code
