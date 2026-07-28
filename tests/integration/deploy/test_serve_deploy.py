# Story: E5-S03 / E5.3
"""E5-S03 — ``zaumzeug serve --deploy`` (production bundle root)."""

from __future__ import annotations

import importlib.util
import io
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from fastapi.testclient import TestClient

from zaumzeug.config.resolver import ARTIFACT_MANIFEST
from zaumzeug.deploy.packager import package_harness
from zaumzeug.doctor.report import CheckResult, DoctorReport
from zaumzeug.serve.runner import ServePrepareError, prepare_serve
from zaumzeug.serve.validate import validate_serve


def _load_bundle_target_install(bundle_dir: Path) -> ModuleType:
    """Load ``target_install.py`` from a deploy bundle (simulates target host)."""
    script = bundle_dir / "target_install.py"
    spec = importlib.util.spec_from_file_location(
        "zaumzeug_bundle_target_install",
        script,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _ok_doctor(**kwargs) -> DoctorReport:  # noqa: ANN003
    del kwargs
    return DoctorReport(
        checks=[
            CheckResult(name="preflight", severity="pass", message="ok"),
        ]
    )


def _deploy_manifest(
    *,
    artifact_run_id: str | dict[str, str] = "20260728T120000Z",
) -> dict:
    return {
        "build_id": "test-build-id",
        "source_git_sha": "abc123",
        "harness_yaml_hash": "sha256-deadbeef",
        "artifact_run_id": artifact_run_id,
        "created_at": "2026-07-28T12:00:00Z",
    }


def _seed_dev_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    run_id: str = "20260728T120000Z",
    port: int = 1416,
    prompt_text: str = "You are a researcher.\n",
) -> Path:
    """Minimal compile-ready harness under ``usr-harnesses/`` for packaging."""
    harness_dir = project_root / "usr-harnesses" / harness_name
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": harness_name,
            "serve": {"hayhooks": {"port": port}},
            "deploy": {"eval_gate": "skip"},
        },
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    diagram = harness_dir / "docs" / "workflow-diagram.md"
    diagram.parent.mkdir(parents=True, exist_ok=True)
    diagram.write_text("# Workflow diagram\n", encoding="utf-8")

    agent_dir = harness_dir / "agents" / "researcher"
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
    prompt = agent_dir / "prompts" / "system.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text(prompt_text, encoding="utf-8")

    artifact_dir = agent_dir / "artifacts" / run_id
    (artifact_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (artifact_dir / "prompts" / "system.md").write_text(
        "Optimized researcher prompt.\n",
        encoding="utf-8",
    )
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
    return harness_dir


def _package_bundle(
    project_root: Path,
    *,
    harness_name: str = "example",
) -> Path:
    result = package_harness(
        harness_name,
        project_root=project_root,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert result.bundle_dir is not None
    return result.bundle_dir


def _manual_deploy_bundle(
    project_root: Path,
    *,
    harness_name: str = "example",
    port: int = 1416,
    manifest: dict | None = None,
    with_manifest: bool = True,
) -> Path:
    """Write a minimal ``deploy/<name>/`` layout without the packager."""
    bundle_dir = project_root / "deploy" / harness_name
    _write_yaml(
        bundle_dir / "harness.yaml",
        {"name": harness_name, "serve": {"hayhooks": {"port": port}}},
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
            "agent": {"system_prompt": "prompts/system.md"},
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
    prompt = agent_dir / "prompts" / "system.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("Deploy-only prompt.\n", encoding="utf-8")
    if with_manifest:
        (bundle_dir / "manifest.json").write_text(
            json.dumps(manifest or _deploy_manifest()) + "\n",
            encoding="utf-8",
        )
    return bundle_dir


def test_e5_s03_ac1_loads_deploy_root_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: ``serve --deploy`` loads only ``deploy/<name>/``, not ``usr-harnesses/``."""
    monkeypatch.chdir(tmp_path)
    _seed_dev_harness(tmp_path, prompt_text="DEV ONLY — must not be used.\n")
    bundle = _package_bundle(tmp_path)

    # Divergent / broken content under usr-harnesses must be ignored.
    broken = tmp_path / "usr-harnesses" / "example" / "harness.yaml"
    broken.write_text("name: example\nthis: is: broken\n", encoding="utf-8")

    prepared = prepare_serve("example", project_root=tmp_path, deploy=True)

    assert prepared.harness_dir == bundle
    assert prepared.harness_dir.parts[-2:] == ("deploy", "example")
    assert "usr-harnesses" not in prepared.harness_dir.parts
    assert prepared.validation.ok

    # Without --deploy, the same project still resolves the (broken) dev tree.
    dev_result = validate_serve("example", project_root=tmp_path, deploy=False)
    assert not dev_result.ok
    assert "usr-harnesses" in str(dev_result.harness_dir)


def test_e5_s03_ac2_openai_rest_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: deploy serve exposes the same OpenAI REST surface as dev serve."""
    monkeypatch.chdir(tmp_path)
    _seed_dev_harness(tmp_path)
    _package_bundle(tmp_path)

    prepared = prepare_serve("example", project_root=tmp_path, deploy=True)
    client = TestClient(prepared.app)

    models = client.get("/v1/models")
    assert models.status_code == 200
    payload = models.json()
    assert payload["object"] == "list"
    assert "example" in {item["id"] for item in payload["data"]}

    chat = client.post(
        "/v1/chat/completions",
        json={
            "model": "example",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert chat.status_code == 200
    body = chat.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"]


def test_e5_s03_ac3_fails_missing_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: missing deploy folder or invalid/missing manifest fails before bind."""
    monkeypatch.chdir(tmp_path)

    # Missing deploy/<name>/ entirely.
    with pytest.raises(ServePrepareError) as missing_folder:
        prepare_serve("ghost", project_root=tmp_path, deploy=True)
    assert not missing_folder.value.validation.ok
    assert any(
        c.name == "harness_discovery" and c.severity == "fail"
        for c in missing_folder.value.validation.checks
    )

    # Bundle present but manifest missing.
    _manual_deploy_bundle(tmp_path, harness_name="no-manifest", with_manifest=False)
    with pytest.raises(ServePrepareError) as missing_manifest:
        prepare_serve("no-manifest", project_root=tmp_path, deploy=True)
    assert not missing_manifest.value.validation.ok
    assert any(
        c.name == "deploy_manifest" and c.severity == "fail"
        for c in missing_manifest.value.validation.checks
    )

    # Invalid manifest JSON.
    bad = _manual_deploy_bundle(tmp_path, harness_name="bad-manifest")
    (bad / "manifest.json").write_text("{not-json", encoding="utf-8")
    with pytest.raises(ServePrepareError) as invalid_manifest:
        prepare_serve("bad-manifest", project_root=tmp_path, deploy=True)
    assert not invalid_manifest.value.validation.ok
    assert any(
        c.name == "deploy_manifest" and c.severity == "fail"
        for c in invalid_manifest.value.validation.checks
    )


def test_e5_s03_ac4_after_target_install_clean_venv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: serve --deploy works with only ``deploy/<name>/`` (no usr-harnesses)."""
    monkeypatch.chdir(tmp_path)
    _seed_dev_harness(tmp_path)
    bundle = _package_bundle(tmp_path)

    # Simulate shipping the bundle alone: drop the dev tree.
    shutil.rmtree(tmp_path / "usr-harnesses")
    assert not (tmp_path / "usr-harnesses").exists()
    assert (tmp_path / "deploy" / "example" / "harness.yaml").is_file()

    # target_install stub preflight (full install is E5-S09).
    assert (bundle / "target_install.py").is_file()
    target_install = _load_bundle_target_install(bundle)
    assert target_install.preflight_bundle(bundle) == []

    prepared = prepare_serve("example", project_root=tmp_path, deploy=True)
    assert prepared.harness_dir == bundle
    assert prepared.validation.ok
    assert "usr-harnesses" not in prepared.harness_dir.parts

    client = TestClient(prepared.app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "example",
            "messages": [{"role": "user", "content": "hi from clean target"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"]
