# Story: E3-S02 / E3.2
# Story: E3-S04 / E3.4 (AC-4)
# Story: E3-S06 (AC-4)
"""E3-S02 — ``zaumzeug serve`` (dev mode) integration tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from fastapi.testclient import TestClient

from zaumzeug.serve.runner import (
    DEFAULT_BIND_HOST,
    ServePrepareError,
    prepare_serve,
    run_serve,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _minimal_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    port: int = 1416,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": harness_name,
            "serve": {"hayhooks": {"port": port}},
        },
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {
            "entry": "researcher",
            "stages": [{"agent": "researcher"}],
        },
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


def test_e3_s02_ac1_loads_usr_harnesses_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: serve loads ``usr-harnesses/<name>/`` by default."""
    project_root = tmp_path / "project"
    harness_dir = _minimal_harness(project_root)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    monkeypatch.setattr(
        "zaumzeug.serve.runner.find_project_root",
        lambda start=None: project_root,
    )

    prepared = prepare_serve("example", project_root=project_root)

    assert prepared.harness_dir == harness_dir
    assert prepared.harness_dir.parts[-2:] == ("usr-harnesses", "example")
    assert "deploy" not in prepared.harness_dir.parts


def test_e3_s02_ac2_hayhooks_port_from_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: Hayhooks listens on ``serve.hayhooks.port`` from harness.yaml."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root, port=4242)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    prepared = prepare_serve("example", project_root=project_root)

    assert prepared.port == 4242
    assert prepared.validation.port == 4242


def test_e3_s02_ac3_localhost_bind_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: Phase 1 binds localhost (127.0.0.1), not 0.0.0.0."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root, port=5151)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    prepared = prepare_serve("example", project_root=project_root)
    assert prepared.host == DEFAULT_BIND_HOST
    assert prepared.host == "127.0.0.1"
    assert prepared.host != "0.0.0.0"

    run_app_mock = MagicMock()
    monkeypatch.setattr("zaumzeug.serve.runner.run_app", run_app_mock)
    monkeypatch.setattr(
        "zaumzeug.serve.runner.prepare_serve",
        lambda *args, **kwargs: prepared,
    )

    code = run_serve("example", project_root=project_root)

    assert code == 0
    run_app_mock.assert_called_once()
    _args, kwargs = run_app_mock.call_args
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 5151


def test_e3_s02_ac5_get_v1_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-5: ``GET /v1/models`` lists the served harness pipeline."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    prepared = prepare_serve("example", project_root=project_root)
    client = TestClient(prepared.app)
    response = client.get("/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    model_ids = {item["id"] for item in payload["data"]}
    assert "example" in model_ids


def test_e3_s02_prepare_fails_on_invalid_harness(tmp_path: Path) -> None:
    """Validation failures surface before Hayhooks bind."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    with pytest.raises(ServePrepareError) as exc_info:
        prepare_serve("missing", project_root=project_root)
    assert not exc_info.value.validation.ok


def test_e3_s06_ac4_localhost_bind_enforced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: Phase 1 serve enforces localhost bind; rejects wide-open hosts."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root, port=6161)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    prepared = prepare_serve("example", project_root=project_root)
    assert prepared.host == DEFAULT_BIND_HOST
    assert prepared.host == "127.0.0.1"

    with pytest.raises(ValueError, match="localhost only"):
        prepare_serve("example", project_root=project_root, host="0.0.0.0")

    run_app_mock = MagicMock()
    monkeypatch.setattr("zaumzeug.serve.runner.run_app", run_app_mock)
    monkeypatch.setattr(
        "zaumzeug.serve.runner.prepare_serve",
        lambda *args, **kwargs: prepared,
    )
    code = run_serve("example", project_root=project_root)
    assert code == 0
    _args, kwargs = run_app_mock.call_args
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["host"] != "0.0.0.0"


def test_e3_s04_ac4_serve_example_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: ``zaumzeug serve example`` works without ``.env`` (mock profile)."""
    for key in (
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_BASE",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: REPO_ROOT,
    )
    monkeypatch.setattr(
        "zaumzeug.serve.runner.find_project_root",
        lambda start=None: REPO_ROOT,
    )

    prepared = prepare_serve("example", project_root=REPO_ROOT)

    assert prepared.harness_dir == REPO_ROOT / "usr-harnesses" / "example"
    assert prepared.agent_name == "researcher"
    assert prepared.validation.model_id == "mock"
    assert prepared.validation.ok

    client = TestClient(prepared.app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "example",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["content"]
