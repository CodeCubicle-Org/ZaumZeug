# Story: E6-S01 / E6.1
"""E6-S01 — Optional ``[eval]`` extra (DeepEval not in core)."""

from __future__ import annotations

import builtins
import importlib
import inspect
import sys
import tomllib
from pathlib import Path

import pytest

from zaumzeug.eval import (
    DEEPEVAL_INSTALL_HINT,
    DEEPEVAL_MISSING_MESSAGE,
    DeepEvalMissingError,
    is_deepeval_available,
    require_deepeval,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT = REPO_ROOT / "pyproject.toml"
LIVE_INSTALLATION = REPO_ROOT / "user-docs" / "getting-started" / "installation.md"
TEMPLATE_INSTALLATION = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "getting-started" / "installation.md"
)


def _load_pyproject() -> dict:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def _dep_name(spec: str) -> str:
    for sep in ("[", ">", "<", "=", "!", " ", ";"):
        if sep in spec:
            return spec.split(sep, 1)[0].strip().lower()
    return spec.strip().lower()


def test_e6_s01_ac1_core_has_no_deepeval_dependency() -> None:
    """AC-1: Core ``zaumzeug`` install has no ``deepeval`` dependency."""
    project = _load_pyproject()["project"]
    dep_names = {_dep_name(dep) for dep in project["dependencies"]}
    assert "deepeval" not in dep_names


def test_e6_s01_ac2_eval_extra_installs_deepeval() -> None:
    """AC-2: ``[eval]`` extra installs ``deepeval``."""
    extras = _load_pyproject()["project"]["optional-dependencies"]
    assert "eval" in extras
    eval_names = {_dep_name(dep) for dep in extras["eval"]}
    assert "deepeval" in eval_names


def test_e6_s01_ac3_user_docs_document_eval_extra() -> None:
    """AC-3: user-docs document ``pip install \"zaumzeug[eval]\"``."""
    needle = 'pip install "zaumzeug[eval]"'
    for path in (LIVE_INSTALLATION, TEMPLATE_INSTALLATION):
        text = path.read_text(encoding="utf-8")
        assert needle in text, f"{path} must document {needle}"


def test_e6_s01_eval_package_import_does_not_load_deepeval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Importing ``zaumzeug.eval`` must succeed even when ``deepeval`` is absent."""
    real_import = builtins.__import__

    def _block_deepeval(name: str, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "deepeval" or name.startswith("deepeval."):
            raise ImportError("blocked for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _block_deepeval)
    monkeypatch.delitem(sys.modules, "deepeval", raising=False)
    sys.modules.pop("zaumzeug.eval", None)

    module = importlib.import_module("zaumzeug.eval")
    assert hasattr(module, "require_deepeval")
    assert hasattr(module, "is_deepeval_available")
    assert module.is_deepeval_available() is False


def test_e6_s01_require_deepeval_friendly_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing DeepEval raises an actionable ``[eval]`` install hint."""
    real_import = builtins.__import__

    def _block_deepeval(name: str, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "deepeval" or name.startswith("deepeval."):
            raise ImportError("blocked for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _block_deepeval)
    monkeypatch.delitem(sys.modules, "deepeval", raising=False)

    with pytest.raises(DeepEvalMissingError) as exc_info:
        require_deepeval()

    message = str(exc_info.value)
    assert message == DEEPEVAL_MISSING_MESSAGE
    assert DEEPEVAL_INSTALL_HINT in message
    assert exc_info.value.suggestion == DEEPEVAL_INSTALL_HINT
    assert is_deepeval_available() is False


def test_e6_s01_doctor_does_not_require_deepeval() -> None:
    """DoD: ``zaumzeug doctor`` does not import or require deepeval."""
    import zaumzeug.doctor.checks as checks
    import zaumzeug.doctor.runner as runner

    for module in (checks, runner):
        source = inspect.getsource(module)
        assert "deepeval" not in source.lower()
        assert "require_deepeval" not in source
