# Story: E2-S04a / E2.4
# Story: E2-S04b / E2.4
"""E2-S04 — `zaumzeug doctor` checks (unit)."""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import pytest
import yaml

from zaumzeug.cli import _doctor_command, build_parser
from zaumzeug.doctor.checks import (
    check_env_for_live_models,
    check_mcp_uv_presence,
    check_package_import,
    check_phase_gated_agent_tools,
    check_port_conflict,
    check_python_version,
)
from zaumzeug.doctor.runner import run_doctor


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
    harness_dir.mkdir(parents=True, exist_ok=True)

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


def test_e2_s04_ac1_python_version_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-1: doctor checks Python version (3.11+)."""
    assert check_python_version().severity == "pass"

    monkeypatch.setattr(sys, "version_info", (3, 10, 0))
    result = check_python_version()
    assert result.severity == "fail"
    assert "3.11" in result.message


def test_e2_s04_ac2_package_import_check() -> None:
    """AC-2: doctor checks zaumzeug package import."""
    result = check_package_import()
    assert result.severity == "pass"
    assert "importable" in result.message


def test_e2_s04_ac3_env_warn_without_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-3: warn when live models are configured without API keys or .env."""
    project_root = tmp_path / "project"
    _minimal_harness(
        project_root,
        agent_models={
            "default_model_id": "default",
            "models": {
                "default": {"provider": "openai", "model": "gpt-4o-mini"},
            },
        },
    )
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    report = run_doctor(harness_name="example", project_root=project_root)
    env_checks = [c for c in report.checks if c.name in {"env_file", "env_keys"}]
    assert any(c.severity == "warn" for c in env_checks)

    direct = check_env_for_live_models(project_root, live_providers={"openai"})
    assert any(c.severity == "warn" for c in direct)


def test_e2_s04_ac6_unknown_model_id_fails(tmp_path: Path) -> None:
    """AC-6: unknown model_id referenced in agent.yaml fails."""
    project_root = tmp_path / "project"
    _minimal_harness(
        project_root,
        agent_yaml={
            "name": "researcher",
            "default_model_id": "missing-model",
            "agent": {"system_prompt": "prompts/system.md"},
        },
        agent_models={
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )

    report = run_doctor(harness_name="example", project_root=project_root)
    model_fails = [
        c
        for c in report.checks
        if c.name == "model_registry" and c.severity == "fail"
    ]
    assert model_fails
    assert "missing-model" in model_fails[0].message
    assert report.exit_code == 1


def test_e2_s04_ac7_port_conflict_warn(tmp_path: Path) -> None:
    """AC-7: warn when the configured serve port is already in use."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        result = check_port_conflict("example", port=port)
        assert result.severity == "warn"
        assert str(port) in result.message
    finally:
        sock.close()


def test_e2_s04_ac9_verbose_and_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-9: doctor supports --verbose and --json output."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root)
    monkeypatch.setattr(
        "zaumzeug.doctor.runner.find_project_root",
        lambda start=None: project_root,
    )

    parser = build_parser()
    args_json = parser.parse_args(["doctor", "example", "--json"])
    code_json = _doctor_command(args_json)
    captured_json = capsys.readouterr()
    payload = json.loads(captured_json.out)
    assert code_json == 0
    assert payload["ok"] is True
    assert payload["exit_code"] == 0
    assert isinstance(payload["checks"], list)
    assert payload["checks"][0]["name"] == "python_version"

    args_verbose = parser.parse_args(["doctor", "example", "--verbose"])
    code_verbose = _doctor_command(args_verbose)
    captured_verbose = capsys.readouterr()
    assert code_verbose == 0
    assert "PASS python_version" in captured_verbose.out

    args_quiet = parser.parse_args(["doctor", "example"])
    _doctor_command(args_quiet)
    captured_quiet = capsys.readouterr()
    assert "PASS python_version" not in captured_quiet.out


def test_e2_s04_ac4_eval_section_supported_after_e6_s02(tmp_path: Path) -> None:
    """E2-S04b AC-1 updated: after E6-S02, ``eval`` no longer emits a Phase 2 warn."""
    project_root = tmp_path / "project"
    _minimal_harness(
        project_root,
        harness_yaml={
            "name": "example",
            "serve": {"hayhooks": {"port": 1416}},
            "eval": {
                "framework": "builtin",
                "valset": "eval/val.jsonl",
            },
        },
    )
    # Valset file is optional for doctor validation of the eval schema.
    valset = project_root / "usr-harnesses" / "example" / "eval" / "val.jsonl"
    valset.parent.mkdir(parents=True, exist_ok=True)
    valset.write_text('{"input": "x"}\n', encoding="utf-8")

    report = run_doctor(harness_name="example", project_root=project_root)
    eval_warns = [
        c for c in report.checks if c.name == "eval_section" and c.severity == "warn"
    ]
    assert not eval_warns
    assert report.exit_code == 0


def test_e2_s04_ac8_mcp_without_uv_warns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2 (E2-S04b): warn when MCP is configured but uv is missing."""
    project_root = tmp_path / "project"
    _minimal_harness(
        project_root,
        agent_yaml={
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": {
                "mcp": [
                    {
                        "name": "filesystem",
                        "command": "uv",
                        "args": ["run", "mcp-server-filesystem", "/workspace"],
                    }
                ]
            },
        },
    )
    monkeypatch.setattr("zaumzeug.doctor.checks.shutil.which", lambda cmd: None)

    report = run_doctor(harness_name="example", project_root=project_root)
    mcp_warns = [c for c in report.checks if c.name == "mcp_uv" and c.severity == "warn"]
    assert mcp_warns
    assert "uv" in mcp_warns[0].message.lower()
    assert report.exit_code == 0

    harness_dir = project_root / "usr-harnesses" / "example"
    direct = check_mcp_uv_presence("example", harness_dir)
    assert direct.severity == "warn"


def test_e7_s01_ac3_mcp_without_uv_warns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3 (E7-S01): doctor warns when MCP configured but ``uv`` is missing (non-blocking)."""
    test_e2_s04_ac8_mcp_without_uv_warns(tmp_path, monkeypatch)


def _write_custom_search_tool(agent_dir: Path) -> None:
    tools_dir = agent_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "my_tool.py").write_text(
        "from haystack.tools import create_tool_from_function\n"
        "\n"
        "def ping(query: str) -> str:\n"
        '    """Echo query for doctor tests."""\n'
        "    return query\n"
        "\n"
        "MyTool = create_tool_from_function(ping, name='ping')\n",
        encoding="utf-8",
    )


def test_e8_s07_ac5_phase_gated_mcp_fails_not_false_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-5 residual: tools.custom is allowed (E7-S02); phase_gated_tools passes."""
    project_root = tmp_path / "project"
    harness_dir = _minimal_harness(
        project_root,
        agent_yaml={
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": {
                "custom": ["tools.my_tool:MyTool"],
            },
        },
    )
    _write_custom_search_tool(harness_dir / "agents" / "researcher")
    monkeypatch.setattr(
        "zaumzeug.doctor.checks.shutil.which",
        lambda cmd: "/usr/bin/uv" if cmd == "uv" else None,
    )

    report = run_doctor(harness_name="example", project_root=project_root)
    gated = [c for c in report.checks if c.name == "phase_gated_tools"]
    assert gated
    assert gated[0].severity == "pass"
    custom = [c for c in report.checks if c.name == "custom_tools"]
    assert custom
    assert custom[0].severity == "pass"
    assert report.exit_code == 0

    mcp_uv = [c for c in report.checks if c.name == "mcp_uv"]
    assert mcp_uv
    assert "MCP configured and `uv` is available" not in mcp_uv[0].message

    assert check_phase_gated_agent_tools("example", harness_dir).severity == "pass"


def test_e8_s07_ac5_phase_gated_mcp_fails_in_deploy_mode(tmp_path: Path) -> None:
    """AC-5 residual: tools.custom is allowed under doctor --deploy (E7-S02)."""
    import json

    from zaumzeug.config.resolver import ARTIFACT_MANIFEST

    project_root = tmp_path / "project"
    deploy_dir = project_root / "deploy" / "example"
    _write_yaml(
        deploy_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        deploy_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = deploy_dir / "agents" / "researcher"
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "agent": {"artifact": "artifacts/20260624-001"},
            "tools": {
                "custom": ["tools.my_tool:MyTool"],
            },
        },
    )
    _write_custom_search_tool(agent_dir)
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    artifact_dir = agent_dir / "artifacts" / "20260624-001"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / ARTIFACT_MANIFEST).write_text(
        json.dumps({"version": 1, "module_hash": "abc"}),
        encoding="utf-8",
    )
    (artifact_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (artifact_dir / "prompts" / "system.md").write_text("prompt", encoding="utf-8")
    (deploy_dir / "manifest.json").write_text(
        json.dumps(
            {
                "build_id": "test-build-id",
                "source_git_sha": "abc123",
                "harness_yaml_hash": "sha256-deadbeef",
                "artifact_run_id": "20260624-001",
                "created_at": "2026-08-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    report = run_doctor(
        harness_name="example",
        project_root=project_root,
        deploy=True,
    )
    gated = [c for c in report.checks if c.name == "phase_gated_tools"]
    assert gated
    assert gated[0].severity == "pass"
    custom = [c for c in report.checks if c.name == "custom_tools"]
    assert custom
    assert custom[0].severity == "pass"
    assert report.exit_code == 0
    # Dev-only mcp_uv remains skipped in deploy.
    assert not any(c.name == "mcp_uv" for c in report.checks)
