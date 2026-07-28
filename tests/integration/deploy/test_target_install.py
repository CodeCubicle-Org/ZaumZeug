# Story: E5-S05 / E5.5 · E5-S09a / E5.9
"""E5-S05 / E5-S09a — Target ship workflow + target_install core (Architecture §10.5 / §10.7)."""

from __future__ import annotations

import ast
import importlib.util
import io
import re
import sys
import tomllib
from pathlib import Path
from types import ModuleType
from typing import Any

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


def _load_target_install() -> ModuleType:
    """Load ``install/target_install.py`` without requiring ``install`` as a package."""
    spec = importlib.util.spec_from_file_location(
        "zaumzeug_target_install",
        TARGET_INSTALL,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def target_install() -> ModuleType:
    return _load_target_install()


def _fake_completed(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> Any:
    class _Result:
        def __init__(self) -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    return _Result()


def _seed_minimal_bundle(deploy_dir: Path) -> None:
    """Write the minimum files ``preflight_bundle`` requires."""
    deploy_dir.mkdir(parents=True, exist_ok=True)
    (deploy_dir / "harness.yaml").write_text("name: example\n", encoding="utf-8")
    (deploy_dir / "manifest.json").write_text("{}\n", encoding="utf-8")


def _fake_venv_builder(module: ModuleType) -> type:
    class FakeBuilder:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def create(self, env_dir: str | Path) -> None:
            path = Path(env_dir)
            scripts = path / ("Scripts" if module.is_windows() else "bin")
            scripts.mkdir(parents=True)
            python_name = "python.exe" if module.is_windows() else "python"
            (scripts / python_name).write_text("", encoding="utf-8")

    return FakeBuilder


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


# --- E5-S09a / E5.9 — target_install core ---------------------------------


def test_e5_s09_ac1_runs_on_linux(target_install: ModuleType) -> None:
    """AC-1: ``target_install.py`` is Linux-capable (OS-neutral pathlib, no hard-coded seps)."""
    source = TARGET_INSTALL.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Must be a plain script runnable with ``python target_install.py`` on Linux.
    assert source.startswith("#!/usr/bin/env python3")
    assert "from pathlib import Path" in source
    assert 'venv_dir / "bin"' in source  # POSIX venv layout
    assert "Scripts" in source  # Windows layout also supported

    # No hard-coded OS path separators in string literals (same rule as E1-S01).
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if "\\" in value and not value.startswith("\\"):
                # Allow escaped newlines / regex-ish text, not Windows paths.
                assert "\\\\" in value or value.count("\\") == value.count("\\n"), (
                    f"suspicious backslash string at line {node.lineno}: {value!r}"
                )

    assert callable(target_install.preflight_bundle)
    assert callable(target_install.run_install)
    assert target_install.RUNTIME_PIP_SPEC == "zaumzeug"
    assert target_install.MIN_PYTHON == (3, 11)


def test_e5_s09_ac2_optional_venv(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: Assumes Python 3.11+; creates optional ``.venv`` beside the bundle."""
    created: list[Path] = []
    FakeBuilder = _fake_venv_builder(target_install)

    class TrackingBuilder(FakeBuilder):  # type: ignore[valid-type,misc]
        def create(self, env_dir: str | Path) -> None:
            created.append(Path(env_dir))
            super().create(env_dir)

    monkeypatch.setattr(target_install.venv, "EnvBuilder", TrackingBuilder)
    monkeypatch.setattr(
        target_install.subprocess,
        "run",
        lambda *_a, **_k: _fake_completed(stdout="zaumzeug 0.1.0\n"),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)

    code = target_install.run_install(deploy_dir, skip_venv=False)
    assert code == 0
    assert created == [deploy_dir / ".venv"]
    assert (deploy_dir / ".venv").exists()

    # --skip-venv must not create .venv
    other = tmp_path / "deploy" / "skip"
    _seed_minimal_bundle(other)
    created.clear()
    code = target_install.run_install(other, skip_venv=True)
    assert code == 0
    assert created == []
    assert not (other / ".venv").exists()


def test_e5_s09_ac3_runtime_only_pip_install(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: ``pip install zaumzeug`` runtime only — no ``[dev]``, ``[eval]``, DSPy, GEPA."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: Any) -> Any:
        calls.append(list(cmd))
        return _fake_completed(stdout="ok\n")

    monkeypatch.setattr(target_install.subprocess, "run", fake_run)
    monkeypatch.setattr(
        target_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)

    code = target_install.run_install(deploy_dir, skip_venv=True)
    assert code == 0
    assert calls, "expected pip / version subprocess calls"

    pip_cmds = [c for c in calls if "pip" in c]
    assert pip_cmds, f"expected a pip install call; got {calls}"
    pip_cmd = pip_cmds[0]
    assert pip_cmd[-4:] == ["-m", "pip", "install", "zaumzeug"]
    joined = " ".join(pip_cmd)
    assert "[dev]" not in joined
    assert "[eval]" not in joined
    assert "dspy" not in joined.lower()
    assert "gepa" not in joined.lower()
    assert "deepeval" not in joined.lower()
    assert target_install.RUNTIME_PIP_SPEC == "zaumzeug"


def test_e5_s09_ac5_env_example_copy_preserves_existing(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: Copies ``.env.example`` → ``.env`` if missing; never overwrites ``.env``."""
    monkeypatch.setattr(
        target_install.subprocess,
        "run",
        lambda *_a, **_k: _fake_completed(),
    )
    monkeypatch.setattr(
        target_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)

    # Prefer project-root ``.env.example`` (parent of deploy/<name>/).
    project_root = tmp_path
    example = project_root / ".env.example"
    example.write_text("OPENAI_API_KEY=replace-me\n", encoding="utf-8")

    code = target_install.run_install(deploy_dir, skip_venv=True)
    assert code == 0
    env_path = project_root / ".env"
    assert env_path.is_file()
    assert env_path.read_text(encoding="utf-8") == "OPENAI_API_KEY=replace-me\n"

    # Existing .env must never be overwritten.
    env_path.write_text("OPENAI_API_KEY=keep-me\n", encoding="utf-8")
    example.write_text("OPENAI_API_KEY=should-not-land\n", encoding="utf-8")
    code = target_install.run_install(deploy_dir, skip_venv=True)
    assert code == 0
    assert env_path.read_text(encoding="utf-8") == "OPENAI_API_KEY=keep-me\n"


def test_e5_s09_ac8_idempotent_rerun(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-5: Idempotent re-run (reuse existing ``.venv``; no broken state)."""
    create_count = {"n": 0}
    FakeBuilder = _fake_venv_builder(target_install)

    class CountingBuilder(FakeBuilder):  # type: ignore[valid-type,misc]
        def create(self, env_dir: str | Path) -> None:
            create_count["n"] += 1
            super().create(env_dir)

    monkeypatch.setattr(target_install.venv, "EnvBuilder", CountingBuilder)
    monkeypatch.setattr(
        target_install.subprocess,
        "run",
        lambda *_a, **_k: _fake_completed(),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)
    (tmp_path / ".env.example").write_text("KEY=1\n", encoding="utf-8")

    assert target_install.run_install(deploy_dir) == 0
    assert create_count["n"] == 1
    assert (tmp_path / ".env").is_file()

    assert target_install.run_install(deploy_dir) == 0
    assert create_count["n"] == 1  # existing .venv reused
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "KEY=1\n"


def test_e5_s09a_preflight_requires_manifest_and_harness(
    target_install: ModuleType,
    tmp_path: Path,
) -> None:
    """Build task: preflight verifies deploy ``manifest.json`` + ``harness.yaml``."""
    empty = tmp_path / "deploy" / "empty"
    empty.mkdir(parents=True)
    errors = target_install.preflight_bundle(empty)
    assert any("harness.yaml" in e for e in errors)
    assert any("manifest.json" in e for e in errors)

    _seed_minimal_bundle(empty)
    assert target_install.preflight_bundle(empty) == []

    code = target_install.main(["--deploy-dir", str(tmp_path / "missing")])
    assert code == 1
