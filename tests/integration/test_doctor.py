# Story: E2-S04a / E2.4
"""E2-S04a — `zaumzeug doctor` core checks (integration)."""

from __future__ import annotations

from pathlib import Path

import yaml

from zaumzeug.doctor.runner import run_doctor


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _harness_layout(
    project_root: Path,
    *,
    harness_name: str,
    agent_yaml: dict,
    agent_models: dict,
    workflow: dict | None = None,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": harness_name, "serve": {"hayhooks": {"port": 1416}}},
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
    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    _write_yaml(agent_dir / "agents-models.yaml", agent_models)
    return harness_dir


def test_e2_s04_ac5_missing_artifact_and_system_prompt_fails(tmp_path: Path) -> None:
    """AC-5: missing artifact and system_prompt fails via shared resolver."""
    project_root = tmp_path / "project"
    _harness_layout(
        project_root,
        harness_name="broken",
        agent_yaml={
            "name": "researcher",
            "tools": {"builtin": ["web_fetch"]},
        },
        agent_models={
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )

    report = run_doctor(harness_name="broken", project_root=project_root)
    runtime_fails = [
        c
        for c in report.checks
        if c.name == "runtime_path" and c.severity == "fail"
    ]
    assert runtime_fails
    assert "runtime path" in runtime_fails[0].message.lower()
    assert report.exit_code == 1


def test_e2_s04_ac10_named_harness_and_project_scan(tmp_path: Path) -> None:
    """AC-10: doctor accepts a harness name or scans the project."""
    project_root = tmp_path / "project"

    for name in ("alpha", "beta"):
        harness_dir = project_root / "usr-harnesses" / name
        _write_yaml(
            harness_dir / "harness.yaml",
            {"name": name, "serve": {"hayhooks": {"port": 1416}}},
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
                "agent": {"system_prompt": "prompts/system.md"},
            },
        )
        prompt = agent_dir / "prompts" / "system.md"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text("prompt", encoding="utf-8")
        _write_yaml(
            agent_dir / "agents-models.yaml",
            {
                "default_model_id": "mock",
                "models": {
                    "mock": {"provider": "mock", "model": "harness-fixture"},
                },
            },
        )

    named = run_doctor(harness_name="alpha", project_root=project_root)
    named_harnesses = {c.harness for c in named.checks if c.harness}
    assert named_harnesses == {"alpha"}
    assert named.exit_code == 0

    scanned = run_doctor(project_root=project_root)
    scanned_harnesses = {c.harness for c in scanned.checks if c.harness}
    assert scanned_harnesses == {"alpha", "beta"}
    discovery = next(c for c in scanned.checks if c.name == "harness_discovery")
    assert discovery.severity == "pass"
    assert "2 harness" in discovery.message
