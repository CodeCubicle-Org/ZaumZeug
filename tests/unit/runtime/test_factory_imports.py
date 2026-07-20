# Story: E3-S00
"""E3-S00 — factory module must not import DSPy or GEPA (compile-time only)."""

from __future__ import annotations

import ast
from pathlib import Path

FACTORY_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "zaumzeug"
    / "runtime"
    / "factory.py"
)

_FORBIDDEN_ROOTS = frozenset({"dspy", "gepa"})


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_e3_s00_ac5_no_dspy_gepa_imports() -> None:
    """AC-5: runtime factory must not import DSPy or GEPA."""
    source = FACTORY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(FACTORY_PATH))
    roots = _imported_roots(tree)
    forbidden = sorted(roots & _FORBIDDEN_ROOTS)
    assert forbidden == [], f"factory.py imports forbidden modules: {forbidden}"
