# Story: E8-S05 / E8.5
"""E8-S05 — optional Dockerfile template in the deploy bundle."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
import yaml

from zaumzeug.deploy.packager import package_harness, write_deploy_bundle

# Reuse the deploy harness seed from the main deploy suite.
from tests.integration.deploy.test_deploy import _ok_doctor, _seed_deploy_harness


def test_e8_s05_ac1_dockerfile_generated_when_flagged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: Dockerfile is generated only when config or CLI flag enables it."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    # Default: no Dockerfile.
    plain = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert plain.bundle_dir is not None
    assert not (plain.bundle_dir / "Dockerfile").exists()
    assert not (plain.bundle_dir / ".dockerignore").exists()
    assert not (plain.bundle_dir / "docker-compose.example.yml").exists()

    # CLI --dockerfile override.
    flagged = package_harness(
        "example",
        project_root=tmp_path,
        dockerfile=True,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert flagged.bundle_dir is not None
    assert (flagged.bundle_dir / "Dockerfile").is_file()
    assert (flagged.bundle_dir / ".dockerignore").is_file()
    assert (flagged.bundle_dir / "docker-compose.example.yml").is_file()

    # Config deploy.dockerfile: true (no CLI override).
    harness_yaml = tmp_path / "usr-harnesses" / "example" / "harness.yaml"
    data = yaml.safe_load(harness_yaml.read_text(encoding="utf-8"))
    data["deploy"] = {"eval_gate": "skip", "dockerfile": True}
    harness_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    from_config = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert from_config.bundle_dir is not None
    assert (from_config.bundle_dir / "Dockerfile").is_file()
    # deploy: section is stripped from the shipped harness.yaml.
    shipped = yaml.safe_load(
        (from_config.bundle_dir / "harness.yaml").read_text(encoding="utf-8")
    )
    assert "deploy" not in shipped


def test_e8_s05_ac2_python311_base_and_target_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: base image Python 3.11+; target_install pattern in Dockerfile."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    result = package_harness(
        "example",
        project_root=tmp_path,
        dockerfile=True,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert result.bundle_dir is not None
    dockerfile = (result.bundle_dir / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.11" in dockerfile
    assert "target_install.py" in dockerfile
    assert "--skip-venv" in dockerfile
    assert "deploy/example" in dockerfile.replace("\\", "/")


def test_e8_s05_ac3_readme_documents_cmd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3 (documented): README.deploy.md documents container CMD."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    result = package_harness(
        "example",
        project_root=tmp_path,
        dockerfile=True,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert result.bundle_dir is not None
    readme = (result.bundle_dir / "README.deploy.md").read_text(encoding="utf-8")
    assert "zaumzeug serve example --deploy" in readme
    assert "CMD" in readme
    assert "docker build" in readme
    assert "Container (Dockerfile)" in readme

    dockerfile = (result.bundle_dir / "Dockerfile").read_text(encoding="utf-8")
    assert 'CMD ["zaumzeug", "serve", "example", "--deploy"]' in dockerfile


def test_e8_s05_ac4_no_env_baked_in_image(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: .env is not baked into the image (dockerignore + Dockerfile comments)."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    # Plant a secret .env next to the harness so a careless packager might copy it.
    (tmp_path / "usr-harnesses" / "example" / ".env").write_text(
        "OPENAI_API_KEY=sk-secret-docker\n",
        encoding="utf-8",
    )

    result = package_harness(
        "example",
        project_root=tmp_path,
        dockerfile=True,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert result.bundle_dir is not None
    bundle = result.bundle_dir

    assert not (bundle / ".env").exists()
    dockerignore = (bundle / ".dockerignore").read_text(encoding="utf-8")
    assert ".env" in dockerignore

    dockerfile = (bundle / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY .env" not in dockerfile
    assert "env-file" in dockerfile.lower() or "runtime" in dockerfile.lower()
    assert "sk-secret-docker" not in dockerfile

    # Bundle text must not contain the planted secret.
    for path in bundle.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {
            ".md",
            ".yaml",
            ".yml",
            ".json",
            ".py",
            ".txt",
            "",
        } and path.name not in {"Dockerfile", ".dockerignore"}:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert "sk-secret-docker" not in content, (
            f"secret leaked into {path.relative_to(bundle)}"
        )

    readme = (bundle / "README.deploy.md").read_text(encoding="utf-8")
    assert "env-file" in readme.lower() or "runtime" in readme.lower()
    assert "never" in readme.lower()


def test_e8_s05_write_bundle_direct_api(tmp_path: Path) -> None:
    """write_deploy_bundle honours the dockerfile kwarg."""
    from zaumzeug.config import load_harness

    harness_dir = _seed_deploy_harness(tmp_path)
    config = load_harness(harness_dir / "harness.yaml")
    dest = write_deploy_bundle(
        "example",
        project_root=tmp_path,
        harness_dir=harness_dir,
        harness_config=config,
        dockerfile=True,
    )
    assert (dest / "Dockerfile").is_file()
    assert (dest / "docker-compose.example.yml").is_file()
