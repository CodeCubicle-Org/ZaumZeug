"""Load ``tools.custom`` Python modules from an agent folder (E7-S02 / E7.2).

Entries in ``agent.yaml`` may be a file path (``tools/search_docs.py``), a dotted
module (``tools.search_docs``), or ``module:attribute``. Import errors include
the module path so doctor and serve fail with an actionable location.
"""

from __future__ import annotations

import importlib
import inspect
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

__all__ = [
    "CustomToolError",
    "CustomToolRef",
    "build_custom_tools",
    "custom_tool_source_rel",
    "load_custom_tools",
    "parse_custom_tool_ref",
]


class CustomToolError(RuntimeError):
    """Failed to import or register a harness custom tool."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        module_path: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.module_path = module_path
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CustomToolRef:
    """Parsed ``tools.custom`` entry."""

    module_name: str
    attr: str | None
    source_rel: str
    raw: str


def parse_custom_tool_ref(entry: str) -> CustomToolRef:
    """Parse a ``tools.custom`` yaml string into a module name and optional attr.

    Accepted forms::

        tools/search_docs.py
        tools.search_docs
        tools.search_docs:search_tool
        tools/search_docs.py:search_tool
    """
    raw = entry.strip()
    if not raw:
        raise CustomToolError(
            "tools.custom entry must be a non-empty string",
            suggestion="Use tools/<name>.py or tools.<name>[:attr]",
        )

    attr: str | None = None
    locator = raw.replace("\\", "/")
    if ":" in locator:
        left, right = locator.rsplit(":", 1)
        right = right.strip()
        left = left.strip()
        # ``tools.search_docs:search_tool`` — not a Windows drive letter.
        if right.isidentifier() and not (len(left) == 1 and left.isalpha()):
            attr = right
            locator = left

    if not locator:
        raise CustomToolError(
            f"tools.custom entry is missing a module path: {entry!r}",
            suggestion="Use tools/<name>.py or tools.<name>[:attr]",
        )
    if locator.startswith("/") or (len(locator) >= 2 and locator[1] == ":"):
        raise CustomToolError(
            f"tools.custom path must stay inside the agent folder; got {entry!r}",
            module_path=locator,
            suggestion="Use a path relative to agents/<name>/, e.g. tools/search_docs.py",
        )
    if ".." in locator.split("/"):
        raise CustomToolError(
            f"tools.custom import path must stay inside the agent folder "
            f"(no traversal); got {entry!r}",
            module_path=locator,
            suggestion="Use tools/<name>.py or tools.<name>[:attr]",
        )

    if locator.endswith(".py") or "/" in locator:
        rel = locator[2:] if locator.startswith("./") else locator
        if rel.endswith(".py"):
            rel = rel[:-3]
        parts = [part for part in rel.split("/") if part]
        if not parts or any(not part.isidentifier() for part in parts):
            raise CustomToolError(
                f"tools.custom import path is invalid: {entry!r}",
                module_path=locator,
                suggestion="Use tools/<name>.py under agents/<name>/",
            )
        module_name = ".".join(parts)
        source_rel = "/".join(parts) + ".py"
    else:
        if "/" in locator or "\\" in locator:
            raise CustomToolError(
                f"tools.custom import path is invalid: {entry!r}",
                module_path=locator,
            )
        parts = locator.split(".")
        if not parts or any(not part.isidentifier() for part in parts):
            raise CustomToolError(
                f"tools.custom import path is invalid: {locator!r} (from {entry!r})",
                module_path=locator,
                suggestion="Use a dotted name under agents/<name>/, e.g. tools.search_docs",
            )
        module_name = locator
        source_rel = "/".join(parts) + ".py"

    return CustomToolRef(
        module_name=module_name,
        attr=attr,
        source_rel=source_rel,
        raw=raw,
    )


def custom_tool_source_rel(entry: str) -> str:
    """Return the agent-relative POSIX source path for a ``tools.custom`` entry."""
    return parse_custom_tool_ref(entry).source_rel


def load_custom_tools(
    entries: list[Any] | None,
    *,
    agent_dir: Path | str,
) -> list[Any]:
    """Import ``tools.custom`` entries relative to ``agents/<name>/``."""
    if not entries:
        return []
    agent_dir = Path(agent_dir).resolve()
    tools: list[Any] = []
    for item in entries:
        if not isinstance(item, str) or not item.strip():
            raise CustomToolError(
                f"tools.custom entry must be a string, got {type(item).__name__}",
                suggestion="List module paths such as tools/search_docs.py",
            )
        tools.extend(_load_one_entry(item.strip(), agent_dir=agent_dir))
    return tools


def build_custom_tools(
    entries: list[Any] | None,
    *,
    agent_dir: Path | str,
) -> list[Any]:
    """Build Haystack tools from ``tools.custom`` (empty list when unset)."""
    return load_custom_tools(entries, agent_dir=agent_dir)


def _load_one_entry(entry: str, *, agent_dir: Path) -> list[Any]:
    try:
        ref = parse_custom_tool_ref(entry)
    except CustomToolError:
        raise
    expected_file = (agent_dir / ref.source_rel).resolve()
    try:
        expected_file.relative_to(agent_dir)
    except ValueError as exc:
        raise CustomToolError(
            f"tools.custom resolved outside the agent folder: {expected_file} "
            f"(entry={entry!r}; agent_dir={agent_dir})",
            path=expected_file,
            module_path=ref.module_name,
            suggestion="Keep custom tools under agents/<name>/tools/",
        ) from exc

    with _agent_import_path(agent_dir, ref.module_name):
        importlib.invalidate_caches()
        _drop_cached_import_chain(ref.module_name)
        try:
            module = importlib.import_module(ref.module_name)
        except Exception as exc:
            raise CustomToolError(
                _import_error_message(
                    module_name=ref.module_name,
                    entry=entry,
                    expected_file=expected_file,
                    detail=str(exc),
                ),
                path=expected_file,
                module_path=ref.module_name,
                suggestion=(
                    f"Create {expected_file} (under agents/<name>/tools/) "
                    f"or fix tools.custom in agent.yaml"
                ),
            ) from exc

    _ensure_module_file_under_agent(
        module,
        agent_dir=agent_dir,
        module_path=ref.module_name,
        expected_file=expected_file,
    )
    return _tools_from_module(module, ref=ref, expected_file=expected_file)


def _tools_from_module(
    module: Any,
    *,
    ref: CustomToolRef,
    expected_file: Path,
) -> list[Any]:
    if ref.attr:
        try:
            obj = getattr(module, ref.attr)
        except AttributeError as exc:
            raise CustomToolError(
                (
                    f"module {ref.module_name!r} has no attribute {ref.attr!r} "
                    f"(tools.custom={ref.raw!r}). Expected in {expected_file}."
                ),
                path=expected_file,
                module_path=f"{ref.module_name}:{ref.attr}",
                suggestion=(
                    f"Define {ref.attr} in {expected_file} or fix tools.custom"
                ),
            ) from exc
        return [_coerce_tool(obj, module_path=f"{ref.module_name}:{ref.attr}", path=expected_file)]

    collected: list[Any] = []
    for name, obj in vars(module).items():
        if name.startswith("_"):
            continue
        # Tool/Component *instances* bound on the module are exports even when
        # their class lives in haystack. Skip imported classes/functions.
        if _is_tool_instance(obj) or _is_component_instance(obj):
            collected.append(
                _coerce_tool(obj, module_path=f"{ref.module_name}.{name}", path=expected_file)
            )
            continue
        if _is_component_class(obj) and getattr(obj, "__module__", None) == module.__name__:
            collected.append(
                _coerce_tool(obj, module_path=f"{ref.module_name}.{name}", path=expected_file)
            )

    if collected:
        return collected

    raise CustomToolError(
        (
            f"module {ref.module_name!r} exported no Haystack tools "
            f"(tools.custom={ref.raw!r}). Expected Tool, ComponentTool, "
            f"@component, or a named attribute in {expected_file}."
        ),
        path=expected_file,
        module_path=ref.module_name,
        suggestion=(
            "Export a Tool / ComponentTool instance, a @component class, "
            "or set tools.custom to module:attribute"
        ),
    )


def _coerce_tool(obj: Any, *, module_path: str, path: Path) -> Any:
    if _is_tool_instance(obj):
        return obj
    if _is_component_class(obj):
        try:
            instance = obj()
        except Exception as exc:
            raise CustomToolError(
                f"failed to instantiate component {obj!r} from {module_path}: {exc}",
                path=path,
                module_path=module_path,
                suggestion="Give the @component class a no-arg constructor",
            ) from exc
        return _component_tool(instance, module_path=module_path, path=path)
    if _is_component_instance(obj):
        return _component_tool(obj, module_path=module_path, path=path)
    if callable(obj) and not inspect.isclass(obj):
        return _tool_from_function(obj, module_path=module_path, path=path)
    raise CustomToolError(
        (
            f"{module_path} is not a Haystack Tool, ComponentTool, "
            f"@component, or callable (got {type(obj).__name__})"
        ),
        path=path,
        module_path=module_path,
        suggestion="Export a Tool / ComponentTool / @component or a typed function",
    )


def _component_tool(component: Any, *, module_path: str, path: Path) -> Any:
    from haystack.tools import ComponentTool

    name = getattr(component, "__class__", type(component)).__name__
    try:
        return ComponentTool(component=component)
    except Exception as exc:
        raise CustomToolError(
            f"failed to wrap {name} as ComponentTool ({module_path}): {exc}",
            path=path,
            module_path=module_path,
            suggestion="Ensure the Haystack component has a typed run() method",
        ) from exc


def _tool_from_function(func: Any, *, module_path: str, path: Path) -> Any:
    from haystack.tools import create_tool_from_function

    try:
        return create_tool_from_function(func)
    except Exception as exc:
        raise CustomToolError(
            f"failed to register function {getattr(func, '__name__', func)!r} "
            f"as a Haystack Tool ({module_path}): {exc}",
            path=path,
            module_path=module_path,
            suggestion="Add type hints and a docstring, or wrap with ComponentTool",
        ) from exc


def _is_tool_instance(obj: Any) -> bool:
    try:
        from haystack.tools import Tool
    except ImportError:
        return False
    return isinstance(obj, Tool)


def _is_component_instance(obj: Any) -> bool:
    try:
        from haystack.core.component.component import Component
    except ImportError:
        return False
    return (not inspect.isclass(obj)) and isinstance(obj, Component)


def _is_component_class(obj: Any) -> bool:
    try:
        from haystack.core.component.component import Component
    except ImportError:
        return False
    return inspect.isclass(obj) and issubclass(obj, Component)


def _ensure_module_file_under_agent(
    module: Any,
    *,
    agent_dir: Path,
    module_path: str,
    expected_file: Path,
) -> None:
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        return
    resolved = Path(module_file).resolve()
    try:
        resolved.relative_to(agent_dir.resolve())
    except ValueError as exc:
        raise CustomToolError(
            (
                f"tools.custom resolved outside the agent folder: {resolved} "
                f"(module={module_path!r}; agent_dir={agent_dir})"
            ),
            path=resolved,
            module_path=module_path,
            suggestion="Keep custom tools under agents/<name>/tools/",
        ) from exc
    if resolved != expected_file and resolved.parent != expected_file.parent:
        # Accept .pyc / different suffix in the same tools tree.
        try:
            resolved.relative_to((agent_dir / "tools").resolve())
        except ValueError:
            pass


def _drop_cached_import_chain(module_name: str) -> None:
    """Remove ``module_name`` and ancestor packages from ``sys.modules``."""
    parts = module_name.split(".")
    names = [".".join(parts[:i]) for i in range(1, len(parts) + 1)]
    drop: set[str] = set()
    for name in names:
        drop.add(name)
        prefix = name + "."
        drop.update(key for key in sys.modules if key.startswith(prefix))
    for key in drop:
        sys.modules.pop(key, None)


@contextmanager
def _agent_import_path(agent_dir: Path, module_name: str) -> Iterator[None]:
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
        _drop_cached_import_chain(module_name)


def _import_error_message(
    *,
    module_name: str,
    entry: str,
    expected_file: Path,
    detail: str,
) -> str:
    return (
        f"failed to import custom tool module {module_name!r} "
        f"(tools.custom={entry!r}). Expected file: {expected_file}. "
        f"Import error: {detail}"
    )
