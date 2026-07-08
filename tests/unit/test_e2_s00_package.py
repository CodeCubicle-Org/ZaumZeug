# Story: E2-S00
"""E2-S00 — SDK package skeleton and CLI foundation (package metadata)."""

from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"

REQUIRED_RUNTIME_DEPS = {
    "haystack-ai",
    "hayhooks",
    "litellm",
    "pydantic",
    "pyyaml",
}

REQUIRED_DEV_EXTRAS = {
    "dspy-ai",
    "gepa",
    "pytest",
    "pytest-asyncio",
    "httpx",
    "respx",
    "debugpy",
}

REQUIRED_LAYOUT = (
    "cli.py",
    "config",
    "runtime",
    "compile",
    "deploy",
    "eval",
    "serve",
    "integrations",
)


def _load_pyproject() -> dict:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def _dep_name(spec: str) -> str:
    for sep in ("[", ">", "<", "=", "!", " ", ";"):
        if sep in spec:
            return spec.split(sep, 1)[0].strip().lower()
    return spec.strip().lower()


def test_e2_s00_ac1_pyproject_metadata() -> None:
    """AC-1: name, requires-python, and runtime deps per Architecture §4.4."""
    project = _load_pyproject()["project"]
    assert project["name"] == "zaumzeug"
    assert project["requires-python"] == ">=3.11"

    dep_names = {_dep_name(dep) for dep in project["dependencies"]}
    missing = REQUIRED_RUNTIME_DEPS - dep_names
    assert not missing, f"missing runtime dependencies: {sorted(missing)}"

    pydantic_specs = [d for d in project["dependencies"] if _dep_name(d) == "pydantic"]
    assert any(">=2" in d for d in pydantic_specs), "pydantic must be constrained to >=2"


def test_e2_s00_ac2_optional_extras_dev_eval() -> None:
    """AC-2: [project.optional-dependencies] includes dev and eval extras."""
    extras = _load_pyproject()["project"]["optional-dependencies"]
    assert "dev" in extras
    assert "eval" in extras

    dev_names = {_dep_name(dep) for dep in extras["dev"]}
    missing_dev = REQUIRED_DEV_EXTRAS - dev_names
    assert not missing_dev, f"missing [dev] extras: {sorted(missing_dev)}"

    eval_names = {_dep_name(dep) for dep in extras["eval"]}
    assert "deepeval" in eval_names


def test_e2_s00_ac3_entry_point_registered() -> None:
    """AC-3: zaumzeug console script points at zaumzeug.cli:main."""
    scripts = _load_pyproject()["project"]["scripts"]
    assert scripts.get("zaumzeug") == "zaumzeug.cli:main"

    eps = metadata.entry_points()
    # importlib.metadata API differs slightly across Python versions.
    if hasattr(eps, "select"):
        console = list(eps.select(group="console_scripts"))
    else:  # pragma: no cover
        console = list(eps.get("console_scripts", []))

    zaumzeug_eps = [ep for ep in console if ep.name == "zaumzeug"]
    assert zaumzeug_eps, "zaumzeug console script not registered; run pip install -e ."
    assert zaumzeug_eps[0].value == "zaumzeug.cli:main"


def test_e2_s00_ac4_package_layout() -> None:
    """AC-4: src/zaumzeug/ layout matches Architecture §3."""
    package_root = REPO_ROOT / "src" / "zaumzeug"
    assert package_root.is_dir()
    assert (package_root / "__init__.py").is_file()

    for name in REQUIRED_LAYOUT:
        path = package_root / name
        if name.endswith(".py"):
            assert path.is_file(), f"missing module file: {path}"
        else:
            assert path.is_dir(), f"missing package directory: {path}"
            assert (path / "__init__.py").is_file(), f"missing {name}/__init__.py"
