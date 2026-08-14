# Story: E4-S01 / E4.1
"""E4-S01 — DSPy module loader (compile-time only)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest
import yaml

from zaumzeug.compile.module_loader import ModuleLoaderError, load_dspy_module

SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "zaumzeug"
SERVE_RUNTIME_ROOTS = (
    SRC_ROOT / "serve",
    SRC_ROOT / "runtime",
)


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _layout(
    tmp_path: Path,
    *,
    agent_name: str = "researcher",
    agent_yaml: dict,
    harness_name: str = "example",
) -> tuple[Path, Path]:
    harness_dir = tmp_path / "usr-harnesses" / harness_name
    agent_dir = harness_dir / "agents" / agent_name
    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    return harness_dir, agent_dir


def _write_module(
    agent_dir: Path,
    *,
    relative: str,
    source: str,
) -> Path:
    path = agent_dir.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure package dirs are importable.
    package_root = path.parent
    while package_root != agent_dir and not (package_root / "__init__.py").exists():
        (package_root / "__init__.py").write_text("", encoding="utf-8")
        package_root = package_root.parent
    path.write_text(source, encoding="utf-8")
    return path


def _purge_import(module_name: str) -> None:
    """Drop a module and its children from ``sys.modules`` (test isolation)."""
    prefix = module_name + "."
    for key in list(sys.modules):
        if key == module_name or key.startswith(prefix):
            del sys.modules[key]


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module)
    return roots


def _forbidden_hits(roots: set[str]) -> list[str]:
    hits: list[str] = []
    for name in roots:
        top = name.split(".", 1)[0]
        if top in {"dspy", "gepa"}:
            hits.append(name)
        if name == "zaumzeug.compile" or name.startswith("zaumzeug.compile."):
            hits.append(name)
    return sorted(set(hits))


VALID_MODULE_SOURCE = '''\
import dspy


class ResearchModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()

    def forward(self, question: str = "") -> dspy.Prediction:
        return dspy.Prediction(answer=f"echo:{question}")
'''

NOT_DSPY_SOURCE = '''\
class PlainClass:
    pass
'''


def test_e4_s01_ac1_valid_module_loads(tmp_path: Path) -> None:
    """AC-1: Loads compile.module from agents/<name>/agent.yaml."""
    harness_dir, agent_dir = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "compile": {"module": "modules.researcher:ResearchModule"},
        },
    )
    _write_module(
        agent_dir,
        relative="modules/researcher.py",
        source=VALID_MODULE_SOURCE,
    )

    try:
        instance = load_dspy_module(
            harness_dir,
            harness_name="example",
            agent_name="researcher",
        )
    finally:
        _purge_import("modules")
        _purge_import("modules.researcher")

    import dspy

    assert isinstance(instance, dspy.Module)
    assert type(instance).__name__ == "ResearchModule"


def test_e4_s01_reloads_same_module_name_from_other_agent_dir(tmp_path: Path) -> None:
    """Same compile.module name must load from the current agent folder, not sys.modules."""
    first_dir, second_dir = tmp_path / "first", tmp_path / "second"

    def _load(root: Path) -> Path:
        harness_dir, agent_dir = _layout(
            root,
            agent_yaml={
                "name": "researcher",
                "compile": {"module": "modules.researcher:ResearchModule"},
            },
        )
        written = _write_module(
            agent_dir,
            relative="modules/researcher.py",
            source=VALID_MODULE_SOURCE,
        )
        instance = load_dspy_module(
            harness_dir,
            harness_name="example",
            agent_name="researcher",
        )
        loaded_file = Path(sys.modules["modules.researcher"].__file__).resolve()
        assert type(instance).__name__ == "ResearchModule"
        assert loaded_file == written.resolve()
        return loaded_file

    try:
        first_file = _load(first_dir)
        second_file = _load(second_dir)
    finally:
        _purge_import("modules")
        _purge_import("modules.researcher")

    assert first_file != second_file
    assert first_dir.resolve() in first_file.parents
    assert second_dir.resolve() in second_file.parents


def test_e4_s01_ac2_not_imported_on_serve_path() -> None:
    """AC-2: serve/runtime must not import DSPy, GEPA, or zaumzeug.compile."""
    offenders: list[str] = []
    for root in SERVE_RUNTIME_ROOTS:
        for path in sorted(root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            hits = _forbidden_hits(_imported_roots(tree))
            for hit in hits:
                offenders.append(f"{path.relative_to(SRC_ROOT)}: {hit}")

    assert offenders == [], (
        "serve/runtime import forbidden compile-time modules:\n"
        + "\n".join(offenders)
    )


def test_e4_s01_ac3_invalid_path_actionable_error(tmp_path: Path) -> None:
    """AC-3: Import errors surface with module path and file hint."""
    harness_dir, _ = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "compile": {"module": "modules.missing:ResearchModule"},
        },
    )

    with pytest.raises(ModuleLoaderError) as exc_info:
        load_dspy_module(
            harness_dir,
            harness_name="example",
            agent_name="researcher",
        )

    err = exc_info.value
    message = str(err)
    assert "modules.missing" in message
    assert "compile.module" in message
    assert "modules" in message.lower()
    assert err.path is not None
    assert err.path.name == "missing.py"
    assert err.suggestion is not None
    assert "agents/researcher/modules" in err.suggestion.replace("\\", "/")

    # Traversal rejected before import.
    harness_dir2, _ = _layout(
        tmp_path / "traversal",
        agent_yaml={
            "name": "researcher",
            "compile": {"module": "modules...evil:ResearchModule"},
        },
    )
    with pytest.raises(ModuleLoaderError) as trav_info:
        load_dspy_module(
            harness_dir2,
            harness_name="example",
            agent_name="researcher",
        )
    assert "traversal" in str(trav_info.value).lower() or "invalid" in str(
        trav_info.value
    ).lower()


def test_e4_s01_ac4_requires_dspy_module_subclass(tmp_path: Path) -> None:
    """AC-4: Validates module is a DSPy Module subclass."""
    harness_dir, agent_dir = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "compile": {"module": "modules.plain:PlainClass"},
        },
    )
    _write_module(
        agent_dir,
        relative="modules/plain.py",
        source=NOT_DSPY_SOURCE,
    )

    try:
        with pytest.raises(ModuleLoaderError) as exc_info:
            load_dspy_module(
                harness_dir,
                harness_name="example",
                agent_name="researcher",
            )
    finally:
        _purge_import("modules")
        _purge_import("modules.plain")

    err = exc_info.value
    assert "dspy.Module" in str(err)
    assert err.module_ref == "modules.plain:PlainClass"


def test_e4_s02a_ac3_missing_module_actionable_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: Fails with actionable error when module not importable (no GEPA)."""
    from zaumzeug.compile import gepa_runner, runner

    harness_dir = tmp_path / "usr-harnesses" / "example"
    agent_dir = harness_dir / "agents" / "researcher"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "compile": {"module": "modules.missing:ResearchModule"},
        },
    )
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {"mock": {"provider": "mock", "model": "harness-fixture"}},
        },
    )

    gepa_calls: list[object] = []

    def _gepa_spy(*args: object, **kwargs: object) -> None:
        gepa_calls.append((args, kwargs))
        raise AssertionError("GEPA must not be invoked on missing module")

    monkeypatch.setattr(gepa_runner, "invoke_gepa", _gepa_spy)
    monkeypatch.setattr(runner, "invoke_gepa", _gepa_spy, raising=False)

    with pytest.raises(runner.CompileError) as exc_info:
        runner.run_compile(
            "example",
            agent_name="researcher",
            project_root=tmp_path,
        )

    message = str(exc_info.value)
    assert "modules.missing" in message or "compile.module" in message
    assert "missing" in message.lower()
    assert gepa_calls == []
