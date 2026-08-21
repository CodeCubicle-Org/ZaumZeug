"""Builtin ``read_file`` tool — text files sandboxed to the harness workspace (E7-S07)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from haystack import component
from haystack.tools import ComponentTool

MAX_FILE_BYTES = 1_048_576


class ReadFileError(ValueError):
    """Raised when a path cannot be read inside the harness workspace."""


def resolve_workspace_file(path: str, *, workspace: Path | str) -> Path:
    """Resolve *path* under *workspace*; reject traversal and outside targets."""
    text = path.strip()
    if not text:
        raise ReadFileError("read_file requires a non-empty path")

    root = Path(workspace).resolve()
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReadFileError(
            f"read_file blocked path outside harness workspace: {path!r}"
        ) from exc
    return resolved


def read_text_file(
    path: str,
    *,
    workspace: Path | str,
    max_bytes: int = MAX_FILE_BYTES,
) -> str:
    """Read a UTF-8 text file that resolves inside *workspace*."""
    target = resolve_workspace_file(path, workspace=workspace)
    if not target.is_file():
        raise ReadFileError(f"read_file path is not a file: {path!r}")
    size = target.stat().st_size
    if size > max_bytes:
        raise ReadFileError(
            f"read_file response exceeds {max_bytes} byte cap for {path!r}"
        )
    return target.read_text(encoding="utf-8", errors="replace")


@component
class ReadFile:
    """Haystack component that reads a text file under the harness folder."""

    def __init__(
        self,
        *,
        workspace: Path | str,
        max_bytes: int = MAX_FILE_BYTES,
    ) -> None:
        self._workspace = Path(workspace)
        self._max_bytes = max_bytes

    @component.output_types(content=str)
    def run(self, path: str) -> dict[str, str]:
        content = read_text_file(
            path,
            workspace=self._workspace,
            max_bytes=self._max_bytes,
        )
        return {"content": content}


def read_file_tool(
    *,
    workspace: Path | str,
    max_bytes: int = MAX_FILE_BYTES,
) -> ComponentTool:
    """Return a Haystack ``ComponentTool`` for the builtin ``read_file`` id."""
    return ComponentTool(
        component=ReadFile(workspace=workspace, max_bytes=max_bytes),
        name="read_file",
        description=(
            "Read a UTF-8 text file under the harness workspace. "
            "Paths are sandboxed; traversal outside the harness folder is blocked."
        ),
    )


def build_read_file_tool(**kwargs: Any) -> ComponentTool:
    """Catalog factory entry for ``read_file``."""
    workspace = kwargs.get("workspace")
    if workspace is None:
        raise ReadFileError("read_file requires a harness workspace path")
    allowed = {k: kwargs[k] for k in ("workspace", "max_bytes") if k in kwargs}
    return read_file_tool(**allowed)
