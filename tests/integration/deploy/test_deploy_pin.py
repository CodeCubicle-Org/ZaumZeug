# Story: E4-S07
# Story: E5-S01 (shared — deploy packager writes artifact_run_id)
"""E4-S07 AC-3 — deploy ``manifest.json`` can pin ``artifact_run_id``.

Full ``zaumzeug deploy`` packager lands in E5-S01. This test locks the shared
contract: a deploy bundle may pin a specific per-agent run id, and
``zaumzeug doctor --deploy`` validates the pinned ``artifact-manifest.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from zaumzeug.config.resolver import ARTIFACT_MANIFEST
from zaumzeug.doctor.runner import run_doctor


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_e4_s07_ac3_deploy_manifest_artifact_run_id(tmp_path: Path) -> None:
    """AC-3 (E4-S07 / shared E5-S01): deploy manifest pins ``artifact_run_id``."""
    project_root = tmp_path / "project"
    harness_name = "shipped"
    run_id = "20260728T100001Z"
    bundle_dir = project_root / "deploy" / harness_name

    _write_yaml(
        bundle_dir / "harness.yaml",
        {"name": harness_name, "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        bundle_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = bundle_dir / "agents" / "researcher"
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"artifact": f"artifacts/{run_id}"},
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
    artifact_dir = agent_dir / "artifacts" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
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
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "build_id": "e4-s07-test",
                "source_git_sha": "deadbeef",
                "harness_yaml_hash": "sha256-test",
                "artifact_run_id": {"researcher": run_id},
                "created_at": "2026-07-28T12:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = run_doctor(
        harness_name=harness_name,
        project_root=project_root,
        deploy=True,
    )
    artifact_pass = next(
        c for c in report.checks if c.name == "deploy_artifact" and c.severity == "pass"
    )
    assert run_id in artifact_pass.message
    assert "researcher" in artifact_pass.message
    assert report.exit_code == 0
