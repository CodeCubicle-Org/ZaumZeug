# Story: E5-S05 / E5.5
"""E5-S05 — Target ship workflow: runtime-only install contract (Architecture §10.5)."""

from __future__ import annotations

import io
import re
import tomllib
from pathlib import Path

import pytest

from zaumzeug.deploy.packager import package_harness
from zaumzeug.doctor.report import CheckResult, DoctorReport

from tests.integration.deploy.test_deploy import _seed_deploy_harness

REPO_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT = REPO_ROOT / "pyproject.toml"
TARGET_INSTALL = REPO_ROOT / "install" / "target_install.py"
README_DEPLOY_TEMPLATE = (
    REPO_ROOT / "install" / "templates" / "deploy" / "README.deploy.md"
)
SHIP_GUIDE = REPO_ROOT / "user-docs" / "guides" / "deploy.md"

FORBIDDEN_RUNTIME_PACKAGES = frozenset(
    {
        "dspy",
        "dspy-ai",
        "gepa",
        "deepeval",
    }
)


def _dep_name(spec: str) -> str:
    for sep in ("[", ">", "<", "=", "!", " ", ";"):
        if sep in spec:
            return spec.split(sep, 1)[0].strip().lower()
    return spec.strip().lower()


def _ok_doctor(**kwargs) -> DoctorReport:  # noqa: ANN003
    del kwargs
    return DoctorReport(
        checks=[
            CheckResult(name="preflight", severity="pass", message="ok"),
        ]
    )


def test_e5_s05_ac2_runtime_only_install() -> None:
    """AC-2: Target installs runtime deps only (``pip install zaumzeug``)."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    runtime_names = {_dep_name(dep) for dep in project["dependencies"]}
    leaked = FORBIDDEN_RUNTIME_PACKAGES & runtime_names
    assert not leaked, f"core install must not include: {sorted(leaked)}"

    assert "haystack-ai" in runtime_names
    assert "hayhooks" in runtime_names
    extras = project["optional-dependencies"]
    assert "dspy-ai" in {_dep_name(d) for d in extras["dev"]}
    assert "gepa" in {_dep_name(d) for d in extras["dev"]}
    assert "deepeval" in {_dep_name(d) for d in extras["eval"]}

    script = TARGET_INSTALL.read_text(encoding="utf-8")
    assert "pip install zaumzeug" in script
    assert re.search(r"pip install zaumzeug\[(dev|eval)\]", script) is None
    assert "no [dev]" in script.lower() or "runtime only" in script.lower()

    readme = README_DEPLOY_TEMPLATE.read_text(encoding="utf-8")
    assert "pip install zaumzeug" in readme
    assert "runtime only" in readme.lower()
    assert "Ship workflow" in readme

    guide = SHIP_GUIDE.read_text(encoding="utf-8")
    assert "pip install zaumzeug" in guide
    assert "runtime only" in guide.lower()


def test_e5_s05_ac3_no_dspy_gepa_deepeval() -> None:
    """AC-3: No DSPy, GEPA, or DeepEval on production server by default."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    runtime_names = {_dep_name(dep) for dep in project["dependencies"]}
    for name in ("dspy-ai", "dspy", "gepa", "deepeval"):
        assert name not in runtime_names

    for path in (TARGET_INSTALL, README_DEPLOY_TEMPLATE, SHIP_GUIDE):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        assert "dspy" in lower, f"{path.name} should mention DSPy"
        assert "gepa" in lower, f"{path.name} should mention GEPA"
        assert "deepeval" in lower, f"{path.name} should mention DeepEval"
        # Docs must state these stay off the default production path.
        asserts_absence = (
            "no dspy" in lower
            or "no [dev]" in lower
            or "**no**" in lower
            or "not installed by default" in lower
            or "compile on" in lower
            or "dev/ci" in lower
            or "dev / ci" in lower
            or ("never" in lower and ("dspy" in lower or "gepa" in lower))
        )
        assert asserts_absence, (
            f"{path.name} must document that DSPy/GEPA/DeepEval stay off the target"
        )


def test_e5_s05_docs_ship_workflow_steps() -> None:
    """AC-1 / AC-4 (docs): ship path + Python 3.11+ prerequisite are documented."""
    readme = README_DEPLOY_TEMPLATE.read_text(encoding="utf-8")
    guide = SHIP_GUIDE.read_text(encoding="utf-8")

    for text in (readme, guide):
        assert "3.11" in text
        assert "target-install.ps1" in text
        assert "target-install.sh" in text
        assert ".env" in text
        assert "zaumzeug serve" in text
        assert "--deploy" in text
        assert "Windows" in text and "Linux" in text and "macOS" in text


def test_e5_s05_bundled_readme_renders_ship_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Packaged README.deploy.md retains the ship workflow after deploy."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    result = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert result.bundle_dir is not None
    readme = (result.bundle_dir / "README.deploy.md").read_text(encoding="utf-8")
    assert "Ship workflow" in readme
    assert "example" in readme
    assert "pip install zaumzeug" in readme
    assert "3.11" in readme
    assert ".env" in readme
    assert "never" in readme.lower()
    assert "target-install.ps1" in readme
    assert "target-install.sh" in readme
