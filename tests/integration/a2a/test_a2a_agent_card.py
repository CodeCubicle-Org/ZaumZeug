# Story: E8-S04 / E8.4
"""E8-S04 — Optional A2A agent card hosting."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from starlette.testclient import TestClient

from zaumzeug.serve.a2a import A2aDisabledError, prepare_a2a
from zaumzeug.serve.a2a_extra import A2A_INSTALL_HINT, is_a2a_available

REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_A2A = REPO_ROOT / "user-docs" / "guides" / "a2a.md"
TEMPLATE_A2A = REPO_ROOT / "install" / "templates" / "user-docs" / "guides" / "a2a.md"
LIVE_ACP = REPO_ROOT / "user-docs" / "guides" / "acp.md"
LIVE_MCP = REPO_ROOT / "user-docs" / "guides" / "cursor-mcp.md"
PRD = REPO_ROOT / "docs" / "prd.md"


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _a2a_harness(
    project_root: Path,
    *,
    a2a: bool | dict | None = True,
    port: int = 1418,
    harness_name: str = "example",
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    serve: dict = {"hayhooks": {"port": 1416}}
    if a2a is not None:
        if a2a is True:
            serve["a2a"] = {"enabled": True, "port": port}
        elif a2a is False:
            serve["a2a"] = False
        else:
            serve["a2a"] = a2a
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": harness_name,
            "description": "Research harness for A2A discovery",
            "serve": serve,
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


def _prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kwargs):
    project_root = tmp_path / "project"
    _a2a_harness(project_root, **kwargs)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    monkeypatch.chdir(project_root)
    return prepare_a2a("example", project_root=project_root)


@pytest.mark.skipif(not is_a2a_available(), reason=f"needs {A2A_INSTALL_HINT}")
def test_e8_s04_ac1_serve_a2a_hosts_agent_card(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: ``serve.a2a: true`` hosts the agent card endpoint."""
    prepared = _prepare(tmp_path, monkeypatch, a2a=True, port=1418)
    assert prepared.port == 1418
    assert prepared.agent_card_path == "/example/.well-known/agent-card.json"

    with TestClient(prepared.app) as client:
        status = client.get("/status")
        assert status.status_code == 200
        body = status.json()
        assert body["status"] == "ok"
        assert "example" in body["agents"]

        card = client.get(prepared.agent_card_path)
        assert card.status_code == 200
        payload = card.json()
        assert payload.get("name") == "example"
        assert "skills" in payload or "supportedInterfaces" in payload or "url" in str(
            payload
        )


def test_e8_s04_ac1_disabled_without_serve_a2a(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: ``zaumzeug a2a`` without ``serve.a2a`` fails with a clear hint."""
    if not is_a2a_available():
        pytest.skip(f"needs {A2A_INSTALL_HINT}")
    project_root = tmp_path / "project"
    _a2a_harness(project_root, a2a=None)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    monkeypatch.chdir(project_root)
    with pytest.raises(A2aDisabledError, match="serve.a2a"):
        prepare_a2a("example", project_root=project_root)


def test_e8_s04_ac2_documented_separately_from_mcp_and_acp() -> None:
    """AC-2: A2A is documented in its own guide, separate from MCP and ACP."""
    assert LIVE_A2A.is_file()
    assert TEMPLATE_A2A.is_file()
    text = LIVE_A2A.read_text(encoding="utf-8")
    assert "Not MCP, not ACP" in text or "not MCP" in text.lower()
    assert "zaumzeug a2a" in text
    assert "serve.a2a" in text
    assert "agent-card.json" in text
    # Distinct files (not folded into MCP/ACP guides)
    assert LIVE_ACP.is_file()
    assert LIVE_MCP.is_file()
    assert LIVE_A2A.resolve() != LIVE_ACP.resolve()
    assert LIVE_A2A.resolve() != LIVE_MCP.resolve()
    acp = LIVE_ACP.read_text(encoding="utf-8")
    assert "A2A" in acp  # ACP guide still disambiguates naming
    assert "zaumzeug a2a" not in acp  # A2A how-to lives in a2a.md


def test_e8_s04_ac3_does_not_conflict_with_ng1() -> None:
    """AC-3: A2A docs keep one harness per process; NG1 multi-tenant out of scope."""
    text = LIVE_A2A.read_text(encoding="utf-8")
    assert "one harness per process" in text.lower() or "One process = one harness" in text
    assert "NG1" in text
    assert "multi-tenant" in text.lower() or "Multi-tenant" in text
    assert "multi-harness routing" in text.lower() or "Do not document multi-harness" in text
    prd = PRD.read_text(encoding="utf-8")
    assert "NG1" in prd
    assert "Multi-tenant" in prd or "multi-tenant" in prd
