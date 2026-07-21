# Story: E3-S07 / OpenAI REST contract (ephemeral serve fixture)
"""Shared integration fixtures — ephemeral localhost serve for contract tests."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import uvicorn
import yaml

from zaumzeug.serve.runner import prepare_serve

REPO_ROOT = Path(__file__).resolve().parents[2]


def _free_localhost_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_contract_harness(
    project_root: Path,
    *,
    port: int,
    with_web_fetch: bool = False,
    models: dict | None = None,
) -> Path:
    """Scaffold a minimal ``example`` harness suitable for OpenAI contract tests."""
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": port}}},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"
    agent_yaml: dict = {
        "name": "researcher",
        "default_model_id": "mock",
        "agent": {"system_prompt": "prompts/system.md"},
    }
    if with_web_fetch:
        agent_yaml["tools"] = {"builtin": ["web_fetch"]}
    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("You are a researcher.", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        models
        or {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    return harness_dir


@pytest.fixture
def ephemeral_serve_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Start ``prepare_serve`` on an ephemeral localhost port; yield base URL.

    Optional indirect params (dict):
    - ``with_web_fetch`` (bool)
    - ``models`` (agents-models.yaml payload)
    """
    options = getattr(request, "param", None) or {}
    port = _free_localhost_port()
    project_root = tmp_path / "project"
    # Point fixture loading at the real repo fixtures directory.
    (project_root / "tests" / "fixtures" / "responses").mkdir(parents=True)
    for name in ("harness-fixture.txt", "alt-fixture.txt"):
        src = REPO_ROOT / "tests" / "fixtures" / "responses" / name
        if src.is_file():
            (project_root / "tests" / "fixtures" / "responses" / name).write_text(
                src.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    write_contract_harness(
        project_root,
        port=port,
        with_web_fetch=bool(options.get("with_web_fetch", False)),
        models=options.get("models"),
    )
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    monkeypatch.chdir(project_root)

    prepared = prepare_serve("example", project_root=project_root)
    config = uvicorn.Config(
        prepared.app,
        host="127.0.0.1",
        port=port,
        log_level="error",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 15.0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if server.started:
            try:
                response = httpx.get(f"{base}/v1/models", timeout=0.5)
                if response.status_code == 200:
                    break
            except Exception as exc:  # noqa: BLE001 — wait-for-ready loop
                last_error = exc
        time.sleep(0.05)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError(f"ephemeral serve did not become ready: {last_error!r}")

    try:
        yield base
    finally:
        server.should_exit = True
        thread.join(timeout=5)
