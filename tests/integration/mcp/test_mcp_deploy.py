# Story: E7-S06 / E7.6
"""E7-S06 — ``zaumzeug mcp <name> --deploy`` from a production bundle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from starlette.testclient import TestClient

from zaumzeug.config.harness_root import HARNESS_ROOT_ENV, resolve_harness_path
from zaumzeug.serve.mcp import prepare_mcp
from zaumzeug.serve.validate import validate_serve

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _deploy_manifest() -> dict:
    return {
        "build_id": "test-build-id",
        "source_git_sha": "abc123",
        "harness_yaml_hash": "sha256-deadbeef",
        "artifact_run_id": "20260821T120000Z",
        "created_at": "2026-08-21T12:00:00Z",
    }


def _copy_mock_fixture(project_root: Path) -> None:
    fixtures = project_root / "tests" / "fixtures" / "responses"
    fixtures.mkdir(parents=True, exist_ok=True)
    src = REPO_ROOT / "tests" / "fixtures" / "responses" / "harness-fixture.txt"
    if src.is_file():
        (fixtures / "harness-fixture.txt").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8"
        )


def _write_harness_tree(
    harness_dir: Path,
    *,
    harness_name: str = "example",
    mcp_port: int = 1417,
    prompt_text: str = "You are a researcher.\n",
    with_manifest: bool = False,
) -> Path:
    """Write a minimal MCP-capable harness tree (dev or deploy layout)."""
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": harness_name,
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
    prompt.write_text(prompt_text, encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    if with_manifest:
        (harness_dir / "manifest.json").write_text(
            json.dumps(_deploy_manifest()) + "\n",
            encoding="utf-8",
        )
    return harness_dir


def _seed_dev_and_deploy(
    project_root: Path,
    *,
    harness_name: str = "example",
    mcp_port: int = 1417,
) -> tuple[Path, Path]:
    """Dev tree + production bundle with divergent prompts."""
    _copy_mock_fixture(project_root)
    dev = _write_harness_tree(
        project_root / "usr-harnesses" / harness_name,
        harness_name=harness_name,
        mcp_port=mcp_port,
        prompt_text="DEV ONLY — must not be used.\n",
    )
    deploy = _write_harness_tree(
        project_root / "deploy" / harness_name,
        harness_name=harness_name,
        mcp_port=mcp_port,
        prompt_text="Deploy-only prompt.\n",
        with_manifest=True,
    )
    return dev, deploy


def _patch_project(monkeypatch: pytest.MonkeyPatch, project_root: Path) -> None:
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    monkeypatch.chdir(project_root)


def _initialize_payload() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "zaumzeug-test", "version": "0.1.0"},
        },
    }


def _assert_mcp_surface(client: TestClient) -> dict:
    status = client.get("/status")
    assert status.status_code == 200
    assert status.json() == {"status": "ok"}

    init = client.post(
        "/mcp",
        json=_initialize_payload(),
        headers={"accept": "application/json, text/event-stream"},
    )
    assert init.status_code == 200
    body = init.json()
    assert body.get("jsonrpc") == "2.0"
    if "result" in body:
        assert "protocolVersion" in body["result"] or "serverInfo" in body["result"]
    else:
        assert "error" not in body or body.get("id") == 1
    return body


def test_e7_s06_ac1_loads_deploy_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: ``zaumzeug mcp <name> --deploy`` loads from ``deploy/<name>/``."""
    monkeypatch.delenv(HARNESS_ROOT_ENV, raising=False)
    _seed_dev_and_deploy(tmp_path)
    _patch_project(monkeypatch, tmp_path)

    # Divergent / broken content under usr-harnesses must be ignored.
    broken = tmp_path / "usr-harnesses" / "example" / "harness.yaml"
    broken.write_text("name: example\nthis: is: broken\n", encoding="utf-8")

    prepared = prepare_mcp("example", project_root=tmp_path, deploy=True)

    expected = resolve_harness_path(tmp_path, "example", deploy_flag=True)
    serve_validation = validate_serve("example", project_root=tmp_path, deploy=True)
    assert prepared.harness_dir == expected
    assert prepared.harness_dir == serve_validation.harness_dir
    assert prepared.harness_dir.parts[-2:] == ("deploy", "example")
    assert "usr-harnesses" not in prepared.harness_dir.parts
    assert prepared.validation.ok
    assert prepared.host in {"127.0.0.1", "localhost"}
    assert prepared.port == 1417

    # Without --deploy, the same project still resolves the (broken) dev tree.
    dev_result = validate_serve("example", project_root=tmp_path, deploy=False)
    assert not dev_result.ok
    assert "usr-harnesses" in str(dev_result.harness_dir)


def test_e7_s06_ac2_same_surface_as_dev(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: deploy MCP exposes the same Streamable HTTP surface as dev MCP."""
    monkeypatch.delenv(HARNESS_ROOT_ENV, raising=False)
    _seed_dev_and_deploy(tmp_path, mcp_port=1417)
    _patch_project(monkeypatch, tmp_path)

    dev = prepare_mcp("example", project_root=tmp_path, deploy=False)
    deploy = prepare_mcp("example", project_root=tmp_path, deploy=True)

    assert "usr-harnesses" in dev.harness_dir.parts
    assert deploy.harness_dir.parts[-2:] == ("deploy", "example")
    assert dev.port == deploy.port == 1417
    assert dev.host == deploy.host
    assert dev.host in {"127.0.0.1", "localhost"}

    with TestClient(dev.app) as dev_client:
        dev_body = _assert_mcp_surface(dev_client)
    with TestClient(deploy.app) as deploy_client:
        deploy_body = _assert_mcp_surface(deploy_client)

    assert set(dev_body.keys()) == set(deploy_body.keys())
    assert ("result" in dev_body) == ("result" in deploy_body)


def test_e7_s06_ac3_respects_harness_root_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: ``HARNESS_ROOT=deploy`` loads the production bundle without ``--deploy``."""
    _seed_dev_and_deploy(tmp_path)
    _patch_project(monkeypatch, tmp_path)
    monkeypatch.setenv(HARNESS_ROOT_ENV, "deploy")

    prepared = prepare_mcp("example", project_root=tmp_path, deploy=False)

    expected = resolve_harness_path(tmp_path, "example", deploy_flag=False)
    serve_validation = validate_serve("example", project_root=tmp_path, deploy=False)
    assert expected == tmp_path / "deploy" / "example"
    assert prepared.harness_dir == expected
    assert prepared.harness_dir == serve_validation.harness_dir
    assert "usr-harnesses" not in prepared.harness_dir.parts
    assert prepared.validation.ok

    with TestClient(prepared.app) as client:
        _assert_mcp_surface(client)
