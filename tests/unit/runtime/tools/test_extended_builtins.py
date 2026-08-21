# Story: E7-S07 / E7.7
"""E7-S07 — Extended builtin tools catalog (``calculator``, ``read_file``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from zaumzeug.config import BUILTIN_CATALOG_PHASE, available_builtin_tool_ids
from zaumzeug.config.builtins import BuiltinToolValidationError, validate_builtin_tool_ids
from zaumzeug.runtime.tools.calculator import Calculator, CalculatorError, evaluate_expression
from zaumzeug.runtime.tools.catalog import create_builtin_tool
from zaumzeug.runtime.tools.read_file import ReadFile


def test_e7_s07_ac1_calculator_and_read_file_in_catalog(tmp_path: Path) -> None:
    """AC-1: Phase 3 catalog ships ``calculator`` and ``read_file``."""
    ids = available_builtin_tool_ids(phase=3)
    assert "calculator" in ids
    assert "read_file" in ids
    assert "web_fetch" in ids
    assert BUILTIN_CATALOG_PHASE == 4
    assert "search_docs" in available_builtin_tool_ids()
    assert available_builtin_tool_ids(phase=3) == ids

    calc = create_builtin_tool("calculator")
    assert calc.name == "calculator"
    assert evaluate_expression("2 + 3 * 4") == 14
    assert Calculator().run(expression="(1 + 2) ** 2") == {"result": "9"}

    notes = tmp_path / "notes.md"
    notes.write_text("workspace-ok", encoding="utf-8")
    reader = create_builtin_tool("read_file", workspace=tmp_path)
    assert reader.name == "read_file"
    assert ReadFile(workspace=tmp_path).run(path="notes.md") == {"content": "workspace-ok"}

    with pytest.raises(CalculatorError, match="operators only"):
        evaluate_expression("__import__('os')")


def test_e7_s07_ac4_search_docs_not_phase3() -> None:
    """AC-4: ``search_docs`` remains Phase 4 and is not in the Phase 3 catalog."""
    ids = available_builtin_tool_ids(phase=3)
    assert "search_docs" not in ids
    assert "search_docs" in available_builtin_tool_ids(phase=4)

    with pytest.raises(BuiltinToolValidationError, match="search_docs") as exc_info:
        validate_builtin_tool_ids(["search_docs"], phase=3)
    message = str(exc_info.value)
    assert "Phase 3" in message
    assert "calculator" in message
    assert "read_file" in message
    assert "web_fetch" in message

    validate_builtin_tool_ids(["search_docs"])
