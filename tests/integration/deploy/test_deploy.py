# Story: E5-S01 / E5.1
"""E5-S01 — ``zaumzeug deploy`` full bundle write (Architecture §10.2 / §10.3)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import yaml

from zaumzeug.config.resolver import ARTIFACT_MANIFEST
from zaumzeug.deploy.packager import DeployError, package_harness, write_deploy_bundle
from zaumzeug.doctor.report import CheckResult, DoctorReport


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


def _seed_deploy_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    with_artifact: bool = True,
    run_id: str = "20260728T120000Z",
) -> Path:
    """Minimal compile-ready harness for deploy packager tests."""
    harness_dir = project_root / "usr-harnesses" / harness_name
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": harness_name,
            "description": "Deploy test harness",
            "models": "models.yaml",
            "serve": {"hayhooks": {"port": 1416}},
            "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
            "deploy": {"eval_gate": "skip"},
        },
    )
    _write_yaml(
        harness_dir / "models.yaml",
        {
            "models": {
                "shared-mock": {"provider": "mock", "model": "harness-shared"},
            }
        },
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    diagram = harness_dir / "docs" / "workflow-diagram.md"
    diagram.parent.mkdir(parents=True, exist_ok=True)
    diagram.write_text(
        "# Workflow diagram — example\n\n"
        "```mermaid\nflowchart LR\n  s0[researcher]\n```\n",
        encoding="utf-8",
    )
    (harness_dir / "data").mkdir(parents=True, exist_ok=True)
    (harness_dir / "data" / "val.jsonl").write_text(
        json.dumps({"input": "hi", "expected_output": "ok"}) + "\n",
        encoding="utf-8",
    )
    (harness_dir / "eval" / "metrics.py").parent.mkdir(parents=True, exist_ok=True)
    (harness_dir / "eval" / "metrics.py").write_text("# eval only\n", encoding="utf-8")

    agent_dir = harness_dir / "agents" / "researcher"
    agent_yaml: dict = {
        "name": "researcher",
        "default_model_id": "mock",
        "compile": {
            "module": "modules.researcher:ResearchModule",
            "task_model_id": "mock",
            "reflection_model_id": "mock",
            "trainset": "data/train.jsonl",
            "valset": "data/val.jsonl",
            "auto": "light",
        },
    }
    if with_artifact:
        agent_yaml["agent"] = {"artifact": f"artifacts/{run_id}"}
    else:
        agent_yaml["agent"] = {"system_prompt": "prompts/system.md"}

    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
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
    prompt.write_text("You are a researcher.\n", encoding="utf-8")
    (agent_dir / "modules" / "researcher.py").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / "modules" / "researcher.py").write_text("# DSPy module\n", encoding="utf-8")
    (agent_dir / "data" / "train.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / "data" / "train.jsonl").write_text("{}\n", encoding="utf-8")

    if with_artifact:
        artifact_dir = agent_dir / "artifacts" / run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
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


def test_e5_s01_ac1_writes_deploy_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: deploy/<name>/ has stripped yaml, workflow, runtime files, diagram, pins."""
    monkeypatch.chdir(tmp_path)
    run_id = "20260728T120000Z"
    _seed_deploy_harness(tmp_path, run_id=run_id)

    result = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert result.packaged is True
    assert result.bundle_dir is not None
    bundle = result.bundle_dir

    assert (bundle / "harness.yaml").is_file()
    assert (bundle / "workflow.yaml").is_file()
    assert (bundle / "docs" / "workflow-diagram.md").is_file()
    assert (bundle / "models.yaml").is_file()
    assert (bundle / "agents" / "researcher" / "agent.yaml").is_file()
    assert (bundle / "agents" / "researcher" / "agents-models.yaml").is_file()
    assert (
        bundle / "agents" / "researcher" / "artifacts" / run_id / ARTIFACT_MANIFEST
    ).is_file()

    harness_data = yaml.safe_load((bundle / "harness.yaml").read_text(encoding="utf-8"))
    assert "eval" not in harness_data
    assert "deploy" not in harness_data
    assert "compile" not in harness_data
    assert harness_data.get("serve", {}).get("hayhooks", {}).get("port") == 1416

    agent_data = yaml.safe_load(
        (bundle / "agents" / "researcher" / "agent.yaml").read_text(encoding="utf-8")
    )
    assert "compile" not in agent_data
    assert agent_data["agent"]["artifact"] == f"artifacts/{run_id}"

    # Dev-only paths must not leak into the bundle.
    assert not (bundle / "eval").exists()
    assert not (bundle / "data").exists()
    assert not (bundle / "agents" / "researcher" / "modules").exists()


def test_e5_s01_ac2_manifest_json_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: manifest.json matches Architecture §10.3 required fields."""
    monkeypatch.chdir(tmp_path)
    run_id = "20260728T120000Z"
    _seed_deploy_harness(tmp_path, run_id=run_id)

    result = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    manifest_path = result.bundle_dir / "manifest.json"  # type: ignore[union-attr]
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    for field in (
        "build_id",
        "source_git_sha",
        "harness_yaml_hash",
        "artifact_run_id",
        "created_at",
    ):
        assert field in raw
        assert raw[field] not in (None, "")
    assert raw["harness_yaml_hash"].startswith("sha256:")
    assert isinstance(raw["artifact_run_id"], dict)
    assert raw["artifact_run_id"]["researcher"] == run_id


def test_e5_s01_ac3_readme_deploy_md_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: README.deploy.md with ops instructions is written."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    result = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    readme = (result.bundle_dir / "README.deploy.md").read_text(encoding="utf-8")  # type: ignore[union-attr]
    assert "example" in readme
    assert "zaumzeug serve" in readme
    assert "--deploy" in readme
    assert "target_install" in readme or "target-install" in readme
    assert "Linux" in readme


def test_e5_s01_ac4_target_install_scripts_in_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: target_install.py and wrappers are copied into the bundle."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    result = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    bundle = result.bundle_dir
    assert bundle is not None
    assert (bundle / "target_install.py").is_file()
    assert (bundle / "target-install.sh").is_file()
    assert (bundle / "target-install.ps1").is_file()
    script = (bundle / "target_install.py").read_text(encoding="utf-8")
    assert "preflight_bundle" in script or "manifest.json" in script


def test_e5_s01_ac5_idempotent_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-5: re-running deploy overwrites deploy/<name>/ idempotently."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    first = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert first.bundle_dir is not None
    stale = first.bundle_dir / "stale-marker.txt"
    stale.write_text("remove me\n", encoding="utf-8")
    first_build = json.loads(
        (first.bundle_dir / "manifest.json").read_text(encoding="utf-8")
    )["build_id"]

    second = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert second.bundle_dir == first.bundle_dir
    assert not stale.exists()
    second_build = json.loads(
        (second.bundle_dir / "manifest.json").read_text(encoding="utf-8")
    )["build_id"]
    assert second_build != first_build
    assert (second.bundle_dir / "harness.yaml").is_file()
    assert (second.bundle_dir / "manifest.json").is_file()


def test_e5_s01_doctor_preflight_blocks_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctor failures abort before packaging."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    def _failing_doctor(**kwargs) -> DoctorReport:  # noqa: ANN003
        del kwargs
        return DoctorReport(
            checks=[
                CheckResult(
                    name="runtime_path",
                    severity="fail",
                    message="broken",
                    harness="example",
                )
            ]
        )

    with pytest.raises(DeployError, match="Doctor preflight failed"):
        package_harness(
            "example",
            project_root=tmp_path,
            run_doctor_fn=_failing_doctor,
            output=io.StringIO(),
        )
    assert not (tmp_path / "deploy" / "example").exists()


def test_e5_s01_system_prompt_only_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agents without artifacts still package via system_prompt."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path, with_artifact=False)

    result = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    bundle = result.bundle_dir
    assert bundle is not None
    assert (bundle / "agents" / "researcher" / "prompts" / "system.md").is_file()
    assert not (bundle / "agents" / "researcher" / "artifacts").exists()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_run_id"] == {}


def test_write_deploy_bundle_direct_api(tmp_path: Path) -> None:
    """write_deploy_bundle is the default BundleWriter used by package_harness."""
    from zaumzeug.config import load_harness

    harness_dir = _seed_deploy_harness(tmp_path)
    config = load_harness(harness_dir / "harness.yaml")
    dest = write_deploy_bundle(
        "example",
        project_root=tmp_path,
        harness_dir=harness_dir,
        harness_config=config,
    )
    assert dest == tmp_path / "deploy" / "example"
    assert (dest / "README.deploy.md").is_file()


def test_e5_s05_ac5_no_env_in_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-5 (E5-S05): ``.env`` is never shipped inside the deploy bundle."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    # Plant secrets where a careless packager might pick them up.
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-secret-project\n", encoding="utf-8")
    (tmp_path / "usr-harnesses" / "example" / ".env").write_text(
        "OPENAI_API_KEY=sk-secret-harness\n",
        encoding="utf-8",
    )
    (tmp_path / "usr-harnesses" / "example" / "agents" / "researcher" / ".env").write_text(
        "OPENAI_API_KEY=sk-secret-agent\n",
        encoding="utf-8",
    )

    result = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert result.bundle_dir is not None
    bundle = result.bundle_dir

    assert not (bundle / ".env").exists()
    env_leaks = [p for p in bundle.rglob(".env") if p.is_file()]
    assert env_leaks == [], f".env must not appear in deploy bundle: {env_leaks}"

    # Bundle text must not contain planted secret values.
    for path in bundle.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".yaml", ".yml", ".json", ".py", ".txt"}:
            content = path.read_text(encoding="utf-8", errors="ignore")
            assert "sk-secret" not in content, f"secret leaked into {path.relative_to(bundle)}"

    readme = (bundle / "README.deploy.md").read_text(encoding="utf-8")
    assert ".env" in readme
    assert "never" in readme.lower()
