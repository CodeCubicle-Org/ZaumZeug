# Story: E1-S07 / E1.7
"""E1-S07 — ``--port`` override and CI serve smoke helper."""

from __future__ import annotations

import importlib.util
import socket
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest
import yaml

from zaumzeug.cli import build_parser
from zaumzeug.serve import prepare_serve, validate_serve

REPO_ROOT = Path(__file__).resolve().parents[3]
SMOKE_PATH = REPO_ROOT / "install" / "ci_serve_smoke.py"


def _load_ci_serve_smoke() -> ModuleType:
    """Load ``install/ci_serve_smoke.py`` without requiring ``install`` as a package."""
    spec = importlib.util.spec_from_file_location(
        "zaumzeug_ci_serve_smoke",
        SMOKE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ci_serve_smoke() -> ModuleType:
    return _load_ci_serve_smoke()


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


def test_e1_s07_ac4_port_override_in_validate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: ``--port`` overrides harness.yaml serve.hayhooks.port."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root, port=1416)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    result = validate_serve("example", project_root=project_root, port=9876)
    assert result.ok
    assert result.port == 9876


def test_e1_s07_ac4_prepare_serve_uses_port_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    _minimal_harness(project_root, port=1416)
    fixtures = project_root / "tests" / "fixtures" / "responses"
    fixtures.mkdir(parents=True)
    src = REPO_ROOT / "tests" / "fixtures" / "responses" / "harness-fixture.txt"
    if src.is_file():
        (fixtures / "harness-fixture.txt").write_text(
            src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    prepared = prepare_serve("example", project_root=project_root, port=9555)
    assert prepared.port == 9555


def test_e1_s07_cli_accepts_port_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(["serve", "example", "--port", "0"])
    assert args.port == 0
    args_dry = parser.parse_args(["serve", "example", "--dry-run", "--port", "4242"])
    assert args_dry.port == 4242
    assert args_dry.dry_run is True


def test_e1_s07_free_localhost_port_is_bindable(ci_serve_smoke: ModuleType) -> None:
    port = ci_serve_smoke.free_localhost_port()
    assert isinstance(port, int)
    assert 0 < port < 65536
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_e1_s07_ac4_smoke_probes_and_terminates(
    ci_serve_smoke: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: smoke helper starts CLI serve, probes /v1/models, terminates."""
    calls: list[list[str]] = []

    class FakeProc:
        def __init__(self) -> None:
            self.returncode: int | None = None
            self.stdout = MagicMock()

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.returncode = -15

        def kill(self) -> None:
            self.returncode = -9

        def wait(self, timeout: float | None = None) -> int:
            assert self.returncode is not None
            return self.returncode

    fake = FakeProc()

    def fake_popen(cmd: list[str], **_kwargs: object) -> FakeProc:
        calls.append(list(cmd))
        return fake

    class FakeResponse:
        status_code = 200

    monkeypatch.setattr(ci_serve_smoke.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        ci_serve_smoke.httpx,
        "get",
        lambda *_a, **_k: FakeResponse(),
    )
    monkeypatch.setattr(ci_serve_smoke, "free_localhost_port", lambda: 54321)

    code = ci_serve_smoke.run_smoke("example", timeout_s=5.0)
    assert code == 0
    assert calls, "expected serve subprocess"
    assert "serve" in calls[0]
    assert "--port" in calls[0]
    assert "54321" in calls[0]
    assert fake.returncode is not None
