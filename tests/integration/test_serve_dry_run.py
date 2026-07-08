# Story: E2-S05 / E2.5
"""E2-S05 — `zaumzeug serve --dry-run` (integration)."""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from zaumzeug.cli import _serve_command, build_parser
from zaumzeug.config import load_harness, resolve_serve_entry
from zaumzeug.serve import validate_serve


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _minimal_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    agent_yaml: dict | None = None,
    agent_models: dict | None = None,
    harness_yaml: dict | None = None,
    workflow: dict | None = None,
    port: int = 1416,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    _write_yaml(
        harness_dir / "harness.yaml",
        harness_yaml
        or {
            "name": harness_name,
            "serve": {"hayhooks": {"port": port}},
        },
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        workflow
        or {
            "entry": "researcher",
            "stages": [{"agent": "researcher"}],
        },
    )
    agent_dir = harness_dir / "agents" / "researcher"
    _write_yaml(
        agent_dir / "agent.yaml",
        agent_yaml
        or {
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": {"builtin": ["web_fetch"]},
        },
    )
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("You are a researcher.", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        agent_models
        or {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    return harness_dir


def test_e2_s05_ac1_same_validation_path_as_serve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: dry-run validates via the same loader and resolver as real serve."""
    project_root = tmp_path / "project"
    harness_dir = _minimal_harness(project_root)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    load_calls: list[Path] = []
    resolve_calls: list[str] = []

    original_load = load_harness
    original_resolve = resolve_serve_entry

    def tracking_load(path: Path | str):
        load_calls.append(Path(path))
        return original_load(path)

    def tracking_resolve(harness_path: Path | str, *, harness_name: str):
        resolve_calls.append(harness_name)
        return original_resolve(harness_path, harness_name=harness_name)

    monkeypatch.setattr("zaumzeug.serve.validate.load_harness", tracking_load)
    monkeypatch.setattr("zaumzeug.serve.validate.resolve_serve_entry", tracking_resolve)

    result = validate_serve("example")

    assert result.ok
    assert load_calls == [harness_dir / "harness.yaml"]
    assert resolve_calls == ["example"]
    assert result.entry is not None
    assert result.entry.agent_name == "researcher"


def test_e2_s05_ac2_prints_resolved_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: human-readable output includes model id, runtime path, tools, and port."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root, port=4242)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    parser = build_parser()
    args = parser.parse_args(["serve", "example", "--dry-run"])
    code = _serve_command(args)
    captured = capsys.readouterr()

    assert code == 0
    output = captured.out
    assert "Serve dry-run: example" in output
    assert "port: 4242" in output
    assert "model_id: mock" in output
    assert "entry agent: researcher" in output
    assert "runtime: system_prompt" in output
    assert "system.md" in output
    assert "web_fetch" in output


def test_e2_s05_ac2_json_output_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: JSON dry-run output includes resolved summary fields."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root, port=5151)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    parser = build_parser()
    args = parser.parse_args(["serve", "example", "--dry-run", "--json"])
    code = _serve_command(args)
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["ok"] is True
    assert payload["exit_code"] == 0
    assert payload["harness"] == "example"
    assert payload["port"] == 5151
    assert payload["entry_agent"] == "researcher"
    assert payload["model_id"] == "mock"
    assert payload["runtime_source"] == "system_prompt"
    assert "system.md" in payload["runtime_path"]
    assert payload["tools"] == ["web_fetch"]
    assert isinstance(payload["checks"], list)


def test_e2_s05_ac3_no_port_bind_no_llm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: dry-run does not bind a port or invoke an LLM provider."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    bind_mock = MagicMock(side_effect=AssertionError("socket.bind must not be called"))
    monkeypatch.setattr(socket.socket, "bind", bind_mock)

    llm_mock = MagicMock(side_effect=AssertionError("litellm must not be called"))
    fake_litellm = MagicMock()
    fake_litellm.completion = llm_mock
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)

    hayhooks_mock = MagicMock(side_effect=AssertionError("hayhooks must not be called"))
    fake_hayhooks = MagicMock()
    fake_hayhooks.run = hayhooks_mock
    monkeypatch.setitem(sys.modules, "hayhooks", fake_hayhooks)

    result = validate_serve("example")

    assert result.ok
    bind_mock.assert_not_called()
    llm_mock.assert_not_called()
    hayhooks_mock.assert_not_called()


def test_e2_s05_ac4_exit_zero_on_valid_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: exit 0 when config and resolved paths are valid."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    result = validate_serve("example")
    assert result.exit_code == 0
    assert result.ok


def test_e2_s05_ac4_exit_nonzero_on_invalid_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: non-zero exit when validation fails."""
    project_root = tmp_path / "project"
    _minimal_harness(
        project_root,
        agent_yaml={
            "name": "researcher",
            "tools": {"builtin": ["web_fetch"]},
        },
    )
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    result = validate_serve("example")
    assert result.exit_code == 1
    assert not result.ok
    assert any(check.severity == "fail" for check in result.checks)

    parser = build_parser()
    args = parser.parse_args(["serve", "example", "--dry-run"])
    assert _serve_command(args) == 1
