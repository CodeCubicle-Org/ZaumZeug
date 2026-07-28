# Story: E2-S04a / E2.4
# Story: E2-S04b / E2.4
# Story: E2-S04c / E2.4
# Story: E4-S05 / E4.5
# Story: E4-S07
"""E2-S04 — `zaumzeug doctor` checks (integration); E4-S05/S07 artifact checks."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
import yaml

from zaumzeug.compile.export import compute_source_file_hash
from zaumzeug.config.harness_root import harness_dir
from zaumzeug.config.resolver import ARTIFACT_MANIFEST
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


def _deploy_manifest(
    *,
    artifact_run_id: str | dict[str, str] = "20260624-001",
) -> dict:
    return {
        "build_id": "test-build-id",
        "source_git_sha": "abc123",
        "harness_yaml_hash": "sha256-deadbeef",
        "artifact_run_id": artifact_run_id,
        "created_at": "2026-06-24T12:00:00Z",
    }


def _deploy_bundle_layout(
    project_root: Path,
    *,
    harness_name: str,
    agent_yaml: dict,
    agent_models: dict,
    workflow: dict | None = None,
    manifest: dict | None = None,
    artifact_run_id: str = "20260624-001",
    with_artifact_manifest: bool = True,
) -> Path:
    bundle_dir = project_root / "deploy" / harness_name
    _write_yaml(
        bundle_dir / "harness.yaml",
        {"name": harness_name, "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        bundle_dir / "workflow.yaml",
        workflow
        or {
            "entry": "researcher",
            "stages": [{"agent": "researcher"}],
        },
    )
    agent_dir = bundle_dir / "agents" / "researcher"
    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    _write_yaml(agent_dir / "agents-models.yaml", agent_models)
    if with_artifact_manifest:
        artifact_dir = agent_dir / "artifacts" / artifact_run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / ARTIFACT_MANIFEST).write_text(
            json.dumps({"version": 1, "module_hash": "abc"}),
            encoding="utf-8",
        )
    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest or _deploy_manifest(artifact_run_id=artifact_run_id)),
        encoding="utf-8",
    )
    return bundle_dir


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


def test_e2_s04_ac11_stale_workflow_diagram_warn(tmp_path: Path) -> None:
    """AC-3 (E2-S04b): warn when workflow.yaml is newer than workflow-diagram.md."""
    project_root = tmp_path / "project"
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    workflow_path = _write_yaml(
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

    docs_dir = harness_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    diagram_path = docs_dir / "workflow-diagram.md"
    diagram_path.write_text("# stale diagram\n", encoding="utf-8")

    # Ensure workflow.yaml mtime is strictly newer than the diagram.
    stale_time = time.time() - 60
    os.utime(diagram_path, (stale_time, stale_time))
    os.utime(workflow_path, (time.time(), time.time()))

    report = run_doctor(harness_name="example", project_root=project_root)
    diagram_warns = [
        c
        for c in report.checks
        if c.name == "workflow_diagram" and c.severity == "warn"
    ]
    assert diagram_warns
    assert "workflow.yaml" in diagram_warns[0].message
    assert report.exit_code == 0


def test_e2_s04c_ac1_deploy_root_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1 (E2-S04c): --deploy resolves harness from deploy/<name>/."""
    project_root = tmp_path / "project"
    bundle_dir = _deploy_bundle_layout(
        project_root,
        harness_name="shipped",
        agent_yaml={
            "name": "researcher",
            "agent": {"artifact": "artifacts/20260624-001"},
        },
        agent_models={
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    dev_dir = project_root / "usr-harnesses" / "shipped"
    dev_dir.mkdir(parents=True)
    _write_yaml(dev_dir / "harness.yaml", {"name": "shipped"})

    report = run_doctor(harness_name="shipped", project_root=project_root, deploy=True)
    assert report.exit_code == 0
    manifest_pass = next(
        c for c in report.checks if c.name == "deploy_manifest" and c.severity == "pass"
    )
    assert "manifest" in manifest_pass.message
    assert harness_dir(project_root, "shipped", deploy=True) == bundle_dir

    monkeypatch.delenv("HARNESS_ROOT", raising=False)
    env_report = run_doctor(harness_name="shipped", project_root=project_root)
    assert not any(c.name == "deploy_manifest" for c in env_report.checks)

    monkeypatch.setenv("HARNESS_ROOT", "deploy")
    env_deploy_report = run_doctor(harness_name="shipped", project_root=project_root)
    assert any(c.name == "deploy_manifest" for c in env_deploy_report.checks)
    assert env_deploy_report.exit_code == 0


def test_e2_s04c_ac2_validates_deploy_manifest(tmp_path: Path) -> None:
    """AC-2 (E2-S04c): validates deploy manifest.json and pinned artifact runs."""
    project_root = tmp_path / "project"
    _deploy_bundle_layout(
        project_root,
        harness_name="valid",
        agent_yaml={
            "name": "researcher",
            "agent": {"artifact": "artifacts/20260624-001"},
        },
        agent_models={
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
        manifest=_deploy_manifest(
            artifact_run_id={"researcher": "20260624-001"},
        ),
    )

    report = run_doctor(harness_name="valid", project_root=project_root, deploy=True)
    manifest_pass = next(
        c for c in report.checks if c.name == "deploy_manifest" and c.severity == "pass"
    )
    artifact_pass = next(
        c for c in report.checks if c.name == "deploy_artifact" and c.severity == "pass"
    )
    assert manifest_pass.harness == "valid"
    assert "researcher" in artifact_pass.message
    assert report.exit_code == 0


def test_e2_s04c_ac3_reuses_core_checks(tmp_path: Path) -> None:
    """AC-3 (E2-S04c): reuses E2-S04a core checks against deploy bundle layout."""
    project_root = tmp_path / "project"
    _deploy_bundle_layout(
        project_root,
        harness_name="core",
        agent_yaml={
            "name": "researcher",
            "agent": {"artifact": "artifacts/20260624-001"},
        },
        agent_models={
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )

    report = run_doctor(harness_name="core", project_root=project_root, deploy=True)
    check_names = {c.name for c in report.checks}
    assert "harness_config" in check_names
    assert "model_registry" in check_names
    assert "runtime_path" in check_names
    assert "port_conflict" in check_names
    assert "mcp_uv" not in check_names
    assert "workflow_diagram" not in check_names
    assert report.exit_code == 0


def test_e2_s04c_ac4_fails_on_broken_bundle(tmp_path: Path) -> None:
    """AC-4 (E2-S04c): non-zero exit on missing manifest or broken artifact refs."""
    project_root = tmp_path / "project"

    missing_manifest_dir = project_root / "deploy" / "no-manifest"
    _deploy_bundle_layout(
        project_root,
        harness_name="no-manifest",
        agent_yaml={
            "name": "researcher",
            "agent": {"artifact": "artifacts/20260624-001"},
        },
        agent_models={
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    (missing_manifest_dir / "manifest.json").unlink()

    missing_report = run_doctor(
        harness_name="no-manifest",
        project_root=project_root,
        deploy=True,
    )
    assert missing_report.exit_code == 1
    assert any(
        c.name == "deploy_manifest" and c.severity == "fail"
        for c in missing_report.checks
    )

    broken_dir = _deploy_bundle_layout(
        project_root,
        harness_name="broken-artifact",
        agent_yaml={
            "name": "researcher",
            "agent": {"artifact": "artifacts/missing-run"},
        },
        agent_models={
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
        with_artifact_manifest=False,
    )

    broken_report = run_doctor(
        harness_name="broken-artifact",
        project_root=project_root,
        deploy=True,
    )
    assert broken_report.exit_code == 1
    runtime_fails = [
        c
        for c in broken_report.checks
        if c.name == "runtime_path" and c.severity == "fail"
    ]
    assert runtime_fails
    assert broken_dir.exists()


# Story: E1-S04 / E1.4
def test_e1_s04_init_then_doctor_passes(tmp_path: Path) -> None:
    """AC-2 (integration): ``zaumzeug init`` then ``doctor`` passes on mock."""
    from zaumzeug.scaffold import init_harness

    project_root = tmp_path / "project"
    (project_root / "usr-harnesses").mkdir(parents=True)

    harness_dir = init_harness("newbie", project_root=project_root)
    assert (harness_dir / "harness.yaml").is_file()

    report = run_doctor(harness_name="newbie", project_root=project_root)
    assert report.exit_code == 0, report.format(verbose=True)


def test_e4_s05_ac5_stale_artifact_warn(tmp_path: Path) -> None:
    """AC-5 (E4-S05): doctor warns when artifact source_hash mismatches compile.module."""
    project_root = tmp_path / "project"
    harness_path = project_root / "usr-harnesses" / "example"
    agent_dir = harness_path / "agents" / "researcher"
    module_path = agent_dir / "modules" / "researcher.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    (module_path.parent / "__init__.py").write_text("", encoding="utf-8")
    module_path.write_text(
        "import dspy\n\nclass ResearchModule(dspy.Module):\n    pass\n",
        encoding="utf-8",
    )
    matching_hash = compute_source_file_hash(module_path)

    artifact_dir = agent_dir / "artifacts" / "current"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (artifact_dir / "prompts" / "system.md").write_text("from artifact\n", encoding="utf-8")
    (artifact_dir / ARTIFACT_MANIFEST).write_text(
        json.dumps(
            {
                "export_version": 1,
                "run_id": "test-run",
                "module_hash": "deadbeef",
                "source_hash": matching_hash,
                "paths": {"system_prompt": "prompts/system.md"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    _write_yaml(
        harness_path / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        harness_path / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"artifact": "artifacts/current"},
            "compile": {
                "module": "modules.researcher:ResearchModule",
                "task_model_id": "mock",
                "reflection_model_id": "mock",
                "auto": "light",
            },
        },
    )
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )

    fresh = run_doctor(harness_name="example", project_root=project_root)
    fresh_pass = [
        c
        for c in fresh.checks
        if c.name == "artifact_module" and c.severity == "pass"
    ]
    assert fresh_pass
    assert "source_hash matches" in fresh_pass[0].message
    assert fresh.exit_code == 0

    module_path.write_text(
        "import dspy\n\nclass ResearchModule(dspy.Module):\n    # edited after compile\n    pass\n",
        encoding="utf-8",
    )
    stale = run_doctor(harness_name="example", project_root=project_root)
    stale_warns = [
        c
        for c in stale.checks
        if c.name == "artifact_module" and c.severity == "warn"
    ]
    assert stale_warns
    assert "stale" in stale_warns[0].message.lower()
    assert "module_hash=deadbeef" in stale_warns[0].message
    assert "compile" in stale_warns[0].message
    assert stale.exit_code == 0


def test_e4_s07_ac2_doctor_validates_pinned_manifest(tmp_path: Path) -> None:
    """AC-2 (E4-S07): doctor validates pinned run manifest; warns when pin ≠ current."""
    project_root = tmp_path / "project"
    harness_path = project_root / "usr-harnesses" / "example"
    agent_dir = harness_path / "agents" / "researcher"
    run_a = "20260728T100001Z"
    run_b = "20260728T100002Z"

    def _write_run(run_id: str, *, system: str) -> Path:
        artifact_dir = agent_dir / "artifacts" / run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "prompts").mkdir(parents=True, exist_ok=True)
        (artifact_dir / "prompts" / "system.md").write_text(system, encoding="utf-8")
        (artifact_dir / ARTIFACT_MANIFEST).write_text(
            json.dumps(
                {
                    "export_version": 1,
                    "run_id": run_id,
                    "paths": {"system_prompt": "prompts/system.md"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return artifact_dir

    _write_run(run_a, system="first compile\n")
    _write_run(run_b, system="second compile\n")

    # Point ``current`` at the newer run (symlink preferred; copy fallback ok).
    current = agent_dir / "artifacts" / "current"
    try:
        current.symlink_to(run_b, target_is_directory=True)
    except OSError:
        import shutil

        shutil.copytree(agent_dir / "artifacts" / run_b, current)

    _write_yaml(
        harness_path / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        harness_path / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"artifact": f"artifacts/{run_a}"},
        },
    )
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )

    report = run_doctor(harness_name="example", project_root=project_root)
    pin_warns = [
        c for c in report.checks if c.name == "pinned_artifact" and c.severity == "warn"
    ]
    assert pin_warns
    assert run_a in pin_warns[0].message
    assert run_b in pin_warns[0].message
    assert report.exit_code == 0

    # Broken pin (no manifest) fails doctor.
    broken_run = "20260728T999999Z"
    broken_dir = agent_dir / "artifacts" / broken_run
    broken_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"artifact": f"artifacts/{broken_run}"},
        },
    )
    broken = run_doctor(harness_name="example", project_root=project_root)
    pin_fails = [
        c for c in broken.checks if c.name == "pinned_artifact" and c.severity == "fail"
    ]
    assert pin_fails
    assert broken_run in pin_fails[0].message or ARTIFACT_MANIFEST in pin_fails[0].message
    assert broken.exit_code != 0

    # Valid pin matching current passes.
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"artifact": f"artifacts/{run_b}"},
        },
    )
    aligned = run_doctor(harness_name="example", project_root=project_root)
    pin_pass = [
        c for c in aligned.checks if c.name == "pinned_artifact" and c.severity == "pass"
    ]
    assert pin_pass
    assert run_b in pin_pass[0].message
    assert aligned.exit_code == 0
