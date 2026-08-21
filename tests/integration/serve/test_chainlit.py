# Story: E7-S04 / E7.4
"""E7-S04 — Chainlit embedded UI at ``/chat`` on the same port as REST."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from hayhooks.settings import settings as hayhooks_settings

from zaumzeug.serve.chainlit import (
    CHAINLIT_INSTALL_HINT,
    ChainlitMissingError,
)
from zaumzeug.serve.runner import prepare_serve

REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_INSTALLATION = REPO_ROOT / "user-docs" / "getting-started" / "installation.md"
TEMPLATE_INSTALLATION = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "getting-started" / "installation.md"
)
LIVE_WEB_DEPLOY = REPO_ROOT / "user-docs" / "guides" / "web-deployment.md"
TEMPLATE_WEB_DEPLOY = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "guides" / "web-deployment.md"
)


@pytest.fixture(autouse=True)
def _reset_hayhooks_chainlit() -> Iterator[None]:
    """Do not leak Hayhooks Chainlit settings into later serve tests."""
    previous_enabled = hayhooks_settings.chainlit_enabled
    previous_model = hayhooks_settings.chainlit_default_model
    yield
    hayhooks_settings.chainlit_enabled = previous_enabled
    hayhooks_settings.chainlit_default_model = previous_model


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _minimal_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    port: int = 1416,
    chainlit: bool = False,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    hayhooks: dict = {"port": port}
    if chainlit:
        hayhooks["chainlit"] = True
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": harness_name,
            "serve": {"hayhooks": hayhooks},
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


def _stub_chainlit_ui(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mount a lean ``/chat`` HTML route so CI does not need ``hayhooks[chainlit]``."""

    def _mount(app) -> None:
        def _chat() -> HTMLResponse:
            return HTMLResponse("<html><body>ZaumZeug Chainlit UI</body></html>")

        app.add_api_route("/chat", _chat, methods=["GET"])
        app.add_api_route("/chat/", _chat, methods=["GET"])

    monkeypatch.setattr("hayhooks.server.app._mount_chainlit_ui", _mount)
    monkeypatch.setattr("zaumzeug.serve.runner.require_chainlit", lambda: None)


def _prepare_chainlit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> object:
    project_root = tmp_path / "project"
    _minimal_harness(project_root, chainlit=True)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    _stub_chainlit_ui(monkeypatch)
    return prepare_serve("example", project_root=project_root)


def test_e7_s04_ac1_chat_route_loads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: ``serve.hayhooks.chainlit: true`` serves ``/chat`` on the REST port."""
    prepared = _prepare_chainlit(tmp_path, monkeypatch)

    assert prepared.chainlit is True
    assert hayhooks_settings.chainlit_enabled is True
    assert hayhooks_settings.chainlit_path == "/chat"
    assert hayhooks_settings.chainlit_default_model == "example"
    assert prepared.port == prepared.validation.port

    client = TestClient(prepared.app)
    response = client.get("/chat")
    assert response.status_code in {200, 307, 308}
    assert response.status_code != 404


def test_e7_s04_ac2_user_docs_list_chainlit_extra() -> None:
    """AC-2: user-docs list ``pip install "hayhooks[chainlit]"`` as an optional extra."""
    needle = 'pip install "hayhooks[chainlit]"'
    for path in (
        LIVE_INSTALLATION,
        TEMPLATE_INSTALLATION,
        LIVE_WEB_DEPLOY,
        TEMPLATE_WEB_DEPLOY,
    ):
        text = path.read_text(encoding="utf-8")
        assert needle in text, f"{path} must document {needle}"
        assert "/chat" in text, f"{path} must mention the /chat UI path"


def test_e7_s04_ac3_openai_rest_still_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: OpenAI REST remains available alongside Chainlit on the same app."""
    prepared = _prepare_chainlit(tmp_path, monkeypatch)
    client = TestClient(prepared.app)

    chat = client.get("/chat")
    assert chat.status_code != 404

    models = client.get("/v1/models")
    assert models.status_code == 200
    model_ids = {item["id"] for item in models.json()["data"]}
    assert "example" in model_ids

    completion = client.post(
        "/v1/chat/completions",
        json={
            "model": "example",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert completion.status_code == 200
    payload = completion.json()
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["content"]


def test_e7_s04_missing_extra_fails_with_install_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``chainlit: true`` without the extra fails before bind with an install hint."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root, chainlit=True)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    monkeypatch.setattr(
        "zaumzeug.serve.chainlit.is_chainlit_available",
        lambda: False,
    )

    with pytest.raises(ChainlitMissingError) as exc_info:
        prepare_serve("example", project_root=project_root)

    message = str(exc_info.value)
    assert CHAINLIT_INSTALL_HINT in message
    assert "/chat" in message
