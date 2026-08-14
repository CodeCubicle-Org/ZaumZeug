"""Load DSPy modules from harness agent folders (compile-time only).

Architecture §2.1 / §3.3 / §4.2: DSPy lives on the ``zaumzeug compile`` path
only. Serve, MCP, and ACP must never import this module.
"""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from zaumzeug.config.resolver import (
    AgentResolutionError,
    CompileResolution,
    resolve_agent_compile,
)

__all__ = [
    "ModuleLoaderError",
    "load_dspy_module",
    "parse_compile_module_ref",
]


class ModuleLoaderError(ValueError):
    """Failed to load or validate a harness DSPy module."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        harness_name: str | None = None,
        agent_name: str | None = None,
        module_ref: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.harness_name = harness_name
        self.agent_name = agent_name
        self.module_ref = module_ref
        self.suggestion = suggestion
        super().__init__(message)


def parse_compile_module_ref(ref: str) -> tuple[str, str]:
    """Parse ``compile.module`` as ``dotted.module:ClassName``."""
    raw = ref.strip()
    if ":" not in raw:
        raise ModuleLoaderError(
            f"compile.module must be 'module.path:ClassName', got {ref!r}",
            module_ref=ref,
            suggestion=(
                "Use an import path relative to the agent folder, e.g. "
                "`modules.researcher:ResearchModule`"
            ),
        )
    module_name, class_name = raw.split(":", 1)
    module_name = module_name.strip()
    class_name = class_name.strip()
    if not module_name or not class_name:
        raise ModuleLoaderError(
            f"compile.module must be 'module.path:ClassName', got {ref!r}",
            module_ref=ref,
            suggestion=(
                "Use an import path relative to the agent folder, e.g. "
                "`modules.researcher:ResearchModule`"
            ),
        )
    _validate_import_name(module_name, module_ref=ref)
    if not class_name.isidentifier():
        raise ModuleLoaderError(
            f"compile.module class name is invalid: {class_name!r} (from {ref!r})",
            module_ref=ref,
            suggestion="Class name must be a valid Python identifier",
        )
    return module_name, class_name


def load_dspy_module(
    harness_dir: Path | str,
    *,
    harness_name: str,
    agent_name: str,
) -> Any:
    """Resolve ``compile.module`` and instantiate the DSPy ``Module`` subclass.

    Adds the agent directory (``agents/<name>/``) to ``sys.path`` so imports
    like ``modules.researcher:ResearchModule`` resolve under
    ``agents/<name>/modules/``. Path segments are validated to prevent
    traversal outside the agent folder.
    """
    try:
        resolution = resolve_agent_compile(
            harness_dir,
            harness_name=harness_name,
            agent_name=agent_name,
        )
    except AgentResolutionError as exc:
        raise ModuleLoaderError(
            str(exc),
            path=exc.path,
            harness_name=exc.harness_name or harness_name,
            agent_name=exc.agent_name or agent_name,
            suggestion=exc.suggestion,
        ) from exc

    return load_dspy_module_from_resolution(resolution)


def load_dspy_module_from_resolution(resolution: CompileResolution) -> Any:
    """Instantiate the DSPy module described by a compile resolution."""
    agent_dir = resolution.agent_yaml_path.parent.resolve()
    module_ref = resolution.compile_module
    if not module_ref:
        raise ModuleLoaderError(
            (
                f"Harness '{resolution.harness_name}' agent '{resolution.agent_name}': "
                "Pattern A compile requires `compile.module` (DSPy Module import path). "
                "For Pattern B use `zaumzeug.compile.gepa_adapter.optimize_haystack_artifact`."
            ),
            path=resolution.agent_yaml_path,
            harness_name=resolution.harness_name,
            agent_name=resolution.agent_name,
            module_ref=module_ref,
            suggestion=(
                "Set compile.module for dspy.GEPA, or call optimize_haystack_artifact "
                "when optimizer is optimize_anything"
            ),
        )
    try:
        module_name, class_name = parse_compile_module_ref(module_ref)
    except ModuleLoaderError as exc:
        raise ModuleLoaderError(
            str(exc),
            path=resolution.agent_yaml_path,
            harness_name=resolution.harness_name,
            agent_name=resolution.agent_name,
            module_ref=module_ref,
            suggestion=exc.suggestion,
        ) from exc

    expected_file = _expected_module_file(agent_dir, module_name)

    with _agent_import_path(agent_dir):
        # Generic names like ``modules.researcher`` collide across harnesses
        # (and pytest tmp dirs) if a prior import is left in ``sys.modules``.
        importlib.invalidate_caches()
        _drop_cached_import_chain(module_name)
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            raise ModuleLoaderError(
                _import_error_message(
                    harness_name=resolution.harness_name,
                    agent_name=resolution.agent_name,
                    module_ref=module_ref,
                    module_name=module_name,
                    expected_file=expected_file,
                    detail=str(exc),
                ),
                path=expected_file,
                harness_name=resolution.harness_name,
                agent_name=resolution.agent_name,
                module_ref=module_ref,
                suggestion=(
                    f"Create {expected_file} (under agents/{resolution.agent_name}/modules/) "
                    f"or fix `compile.module` in {resolution.agent_yaml_path}"
                ),
            ) from exc

    _ensure_module_file_under_agent(module, agent_dir=agent_dir, module_ref=module_ref)

    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ModuleLoaderError(
            (
                f"Harness '{resolution.harness_name}' agent '{resolution.agent_name}': "
                f"module {module_name!r} has no attribute {class_name!r} "
                f"(compile.module={module_ref!r}). Expected class in {expected_file}."
            ),
            path=expected_file,
            harness_name=resolution.harness_name,
            agent_name=resolution.agent_name,
            module_ref=module_ref,
            suggestion=(
                f"Define class {class_name} in {expected_file} "
                f"or fix `compile.module` in {resolution.agent_yaml_path}"
            ),
        ) from exc

    dspy_module_cls = _dspy_module_base()
    if not isinstance(cls, type) or not issubclass(cls, dspy_module_cls):
        raise ModuleLoaderError(
            (
                f"Harness '{resolution.harness_name}' agent '{resolution.agent_name}': "
                f"{module_ref!r} must be a subclass of dspy.Module "
                f"(got {cls!r})."
            ),
            path=expected_file,
            harness_name=resolution.harness_name,
            agent_name=resolution.agent_name,
            module_ref=module_ref,
            suggestion=(
                f"Make {class_name} subclass dspy.Module in {expected_file} "
                "(install with `pip install -e \".[dev]\"` if dspy is missing)"
            ),
        )

    return cls()


def _dspy_module_base() -> type[Any]:
    try:
        import dspy
    except ImportError as exc:
        raise ModuleLoaderError(
            "DSPy is required for compile (pip install -e \".[dev]\" or pip install dspy-ai)",
            suggestion='pip install -e ".[dev]"',
        ) from exc
    return dspy.Module


def _validate_import_name(module_name: str, *, module_ref: str) -> None:
    if (
        module_name.startswith(".")
        or ".." in module_name
        or "/" in module_name
        or "\\" in module_name
    ):
        raise ModuleLoaderError(
            (
                f"compile.module import path must stay inside the agent folder "
                f"(no traversal); got {module_ref!r}"
            ),
            module_ref=module_ref,
            suggestion=(
                "Use a dotted name under agents/<name>/, e.g. "
                "`modules.researcher:ResearchModule`"
            ),
        )
    parts = module_name.split(".")
    if not parts or any(not part.isidentifier() for part in parts):
        raise ModuleLoaderError(
            f"compile.module import path is invalid: {module_name!r} (from {module_ref!r})",
            module_ref=module_ref,
            suggestion=(
                "Use a dotted Python module path relative to the agent folder, "
                "e.g. `modules.researcher:ResearchModule`"
            ),
        )


def _expected_module_file(agent_dir: Path, module_name: str) -> Path:
    return agent_dir.joinpath(*module_name.split(".")).with_suffix(".py")


def _drop_cached_import_chain(module_name: str) -> None:
    """Remove ``module_name`` and ancestor packages from ``sys.modules``.

    Agent-relative imports share names across harness folders. Leaving a
    parent package cached keeps its stale ``__path__``, so the next import
    never sees the current agent directory.
    """
    parts = module_name.split(".")
    names = [".".join(parts[:i]) for i in range(1, len(parts) + 1)]
    drop: set[str] = set()
    for name in names:
        drop.add(name)
        prefix = name + "."
        drop.update(key for key in sys.modules if key.startswith(prefix))
    for key in drop:
        sys.modules.pop(key, None)


def _ensure_module_file_under_agent(
    module: Any,
    *,
    agent_dir: Path,
    module_ref: str,
) -> None:
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        return
    resolved = Path(module_file).resolve()
    try:
        resolved.relative_to(agent_dir.resolve())
    except ValueError as exc:
        raise ModuleLoaderError(
            (
                f"compile.module resolved outside the agent folder: {resolved} "
                f"(compile.module={module_ref!r}; agent_dir={agent_dir})"
            ),
            path=resolved,
            module_ref=module_ref,
            suggestion=(
                "Keep DSPy modules under agents/<name>/modules/ and use an "
                "agent-relative import path"
            ),
        ) from exc


@contextmanager
def _agent_import_path(agent_dir: Path) -> Iterator[None]:
    """Temporarily prepend the agent directory to ``sys.path``."""
    entry = str(agent_dir.resolve())
    inserted = False
    if sys.path[:1] != [entry]:
        sys.path.insert(0, entry)
        inserted = True
    try:
        yield
    finally:
        if inserted:
            try:
                sys.path.remove(entry)
            except ValueError:
                pass


def _import_error_message(
    *,
    harness_name: str,
    agent_name: str,
    module_ref: str,
    module_name: str,
    expected_file: Path,
    detail: str,
) -> str:
    return (
        f"Harness '{harness_name}' agent '{agent_name}': failed to import "
        f"{module_name!r} (compile.module={module_ref!r}). "
        f"Expected file: {expected_file}. Import error: {detail}"
    )
