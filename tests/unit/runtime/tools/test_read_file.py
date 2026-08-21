# Story: E7-S07 / E7.7
"""E7-S07 — ``read_file`` sandbox stays inside the harness workspace."""

from __future__ import annotations

from pathlib import Path

import pytest

from zaumzeug.runtime.tools.read_file import (
    ReadFile,
    ReadFileError,
    read_text_file,
    resolve_workspace_file,
)


def test_e7_s07_ac2_sandbox_blocks_outside_workspace(tmp_path: Path) -> None:
    """AC-2: ``read_file`` cannot read paths outside the harness workspace."""
    workspace = tmp_path / "harness"
    workspace.mkdir()
    (workspace / "notes.md").write_text("inside", encoding="utf-8")
    outside = tmp_path / "secret.txt"
    outside.write_text("leaked", encoding="utf-8")

    component = ReadFile(workspace=workspace)
    assert component.run(path="notes.md") == {"content": "inside"}
    assert read_text_file("notes.md", workspace=workspace) == "inside"

    resolved = resolve_workspace_file("notes.md", workspace=workspace)
    assert resolved == (workspace / "notes.md").resolve()

    with pytest.raises(ReadFileError, match="outside harness workspace"):
        component.run(path=str(outside))

    with pytest.raises(ReadFileError, match="outside harness workspace"):
        component.run(path="../secret.txt")

    with pytest.raises(ReadFileError, match="outside harness workspace"):
        read_text_file("..", workspace=workspace)
