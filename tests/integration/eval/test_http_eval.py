# Story: E6-S06 / E6.6
"""E6-S06 — HTTP black-box eval (Mode C) against running ``zaumzeug serve``."""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import uvicorn
import yaml

from zaumzeug.cli import build_parser
from zaumzeug.config import EvalConfig, HarnessConfig
from zaumzeug.eval.runner import (
    DEFAULT_EVAL_HOST,
    DEFAULT_HAYHOOKS_PORT,
    default_eval_base_url,
    resolve_eval_base_url,
    run_eval,
)
from zaumzeug.serve.runner import prepare_serve

REPO_ROOT = Path(__file__).resolve().parents[3]
MOCK_FIXTURE_TEXT = (
    REPO_ROOT / "tests" / "fixtures" / "responses" / "harness-fixture.txt"
).read_text(encoding="utf-8").strip()


def _free_localhost_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _copy_mock_fixtures(project_root: Path) -> None:
    dest = project_root / "tests" / "fixtures" / "responses"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("harness-fixture.txt", "alt-fixture.txt"):
        src = REPO_ROOT / "tests" / "fixtures" / "responses" / name
        if src.is_file():
            (dest / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _eval_harness(
    project_root: Path,
    *,
    port: int,
    harness_name: str = "example",
    eval_section: dict | None = None,
    valset_rows: list[dict] | None = None,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    if eval_section is None:
        eval_section = {
            "framework": "builtin",
            "valset": "data/val.jsonl",
        }
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": harness_name,
            "serve": {"hayhooks": {"port": port}},
            "eval": eval_section,
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
    rows = valset_rows or [
        {"input": "hi", "expected_output": "Mock harness fixture"},
    ]
    _write_jsonl(harness_dir / eval_section["valset"], rows)
    return harness_dir


def _start_serve(
    project_root: Path,
    *,
    port: int,
    harness_name: str = "example",
) -> tuple[uvicorn.Server, threading.Thread, str]:
    prepared = prepare_serve(harness_name, project_root=project_root, port=port)
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
                    return server, thread, base
            except Exception as exc:  # noqa: BLE001 — wait-for-ready
                last_error = exc
        time.sleep(0.05)
    server.should_exit = True
    thread.join(timeout=5)
    raise RuntimeError(f"ephemeral serve did not become ready: {last_error!r}")


@pytest.fixture
def mode_c_serve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, str, int]]:
    """Project root + live serve base URL + port for Mode C eval tests."""
    port = _free_localhost_port()
    project_root = tmp_path / "project"
    _copy_mock_fixtures(project_root)
    _eval_harness(project_root, port=port)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )
    monkeypatch.chdir(project_root)

    server, thread, base = _start_serve(project_root, port=port)
    try:
        yield project_root, base, port
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_e6_s06_ac2_base_url_override() -> None:
    """AC-2: configurable base URL; default is localhost + harness port."""
    harness = HarnessConfig.model_validate(
        {
            "name": "example",
            "serve": {"hayhooks": {"port": 2424}},
            "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
        }
    )
    assert harness.eval is not None
    assert default_eval_base_url(harness) == f"http://{DEFAULT_EVAL_HOST}:2424"

    default_harness = HarnessConfig.model_validate(
        {
            "name": "example",
            "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
        }
    )
    assert default_eval_base_url(default_harness) == (
        f"http://{DEFAULT_EVAL_HOST}:{DEFAULT_HAYHOOKS_PORT}"
    )

    # CLI --base-url alone (empty) → default from harness port
    assert (
        resolve_eval_base_url(
            cli_base_url="",
            eval_config=harness.eval,
            harness_config=harness,
        )
        == f"http://{DEFAULT_EVAL_HOST}:2424"
    )

    # Explicit CLI override wins over config
    cfg = EvalConfig(
        framework="builtin",
        valset="data/val.jsonl",
        base_url="http://config.example:9999",
    )
    assert (
        resolve_eval_base_url(
            cli_base_url="http://staging.example:8080/",
            eval_config=cfg,
            harness_config=harness,
        )
        == "http://staging.example:8080"
    )

    # Config field alone enables Mode C
    assert (
        resolve_eval_base_url(
            cli_base_url=None,
            eval_config=cfg,
            harness_config=harness,
        )
        == "http://config.example:9999"
    )

    # No CLI / no config → in-process Mode A
    assert (
        resolve_eval_base_url(
            cli_base_url=None,
            eval_config=EvalConfig(framework="builtin", valset="data/val.jsonl"),
            harness_config=harness,
        )
        is None
    )

    parser = build_parser()
    alone = parser.parse_args(["eval", "example", "--base-url"])
    assert alone.base_url == ""
    explicit = parser.parse_args(
        ["eval", "example", "--base-url", "http://127.0.0.1:3000"]
    )
    assert explicit.base_url == "http://127.0.0.1:3000"
    omitted = parser.parse_args(["eval", "example"])
    assert omitted.base_url is None


def test_e6_s06_ac1_calls_serve_chat_completions(
    mode_c_serve: tuple[Path, str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: Mode C eval POSTs to running serve ``/v1/chat/completions``."""
    project_root, base, _port = mode_c_serve
    posted: list[str] = []
    real_post = httpx.post

    def _tracking_post(url: str, *args: object, **kwargs: object):
        posted.append(str(url))
        return real_post(url, *args, **kwargs)

    monkeypatch.setattr(httpx, "post", _tracking_post)

    result = run_eval(
        "example",
        project_root=project_root,
        framework="builtin",
        base_url=base,
    )

    assert any(url.rstrip("/").endswith("/v1/chat/completions") for url in posted)
    assert f"{base}/v1/chat/completions" in posted
    assert result.framework == "builtin"
    assert result.passed == 1
    assert result.failed == 0
    assert result.exit_code == 0
    assert "Mock harness fixture" in result.cases[0].actual_output


def test_e6_s06_ac3_same_metrics_as_inprocess(
    mode_c_serve: tuple[Path, str, int],
) -> None:
    """AC-3: Mode C uses the same builtin metrics as in-process Mode A."""
    project_root, base, _port = mode_c_serve

    inprocess = run_eval(
        "example",
        project_root=project_root,
        framework="builtin",
        agent_runner=lambda _inp: MOCK_FIXTURE_TEXT,
    )
    http_mode = run_eval(
        "example",
        project_root=project_root,
        framework="builtin",
        base_url=base,
    )

    assert inprocess.framework == http_mode.framework == "builtin"
    assert inprocess.passed == http_mode.passed
    assert inprocess.failed == http_mode.failed
    assert len(inprocess.cases) == len(http_mode.cases)
    for left, right in zip(inprocess.cases, http_mode.cases, strict=True):
        assert left.passed == right.passed
        assert left.input == right.input
        assert left.expected_output == right.expected_output
        # Both paths surface the same mock fixture content for scoring.
        assert "Mock harness fixture" in left.actual_output
        assert "Mock harness fixture" in right.actual_output


def test_e6_s06_default_base_url_hits_harness_port(
    mode_c_serve: tuple[Path, str, int],
) -> None:
    """AC-2 (integration): empty ``--base-url`` uses harness serve port."""
    project_root, _base, port = mode_c_serve
    result = run_eval(
        "example",
        project_root=project_root,
        framework="builtin",
        base_url="",  # resolve default from harness.yaml port
    )
    assert result.passed == 1
    assert result.failed == 0
    # Sanity: default would have targeted this port
    assert default_eval_base_url(
        HarnessConfig.model_validate(
            {
                "name": "example",
                "serve": {"hayhooks": {"port": port}},
                "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
            }
        )
    ) == f"http://127.0.0.1:{port}"
