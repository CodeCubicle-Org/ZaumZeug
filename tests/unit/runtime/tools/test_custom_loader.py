# Story: E7-S02 / E7.2
"""E7-S02 — Custom tool loader imports harness ``tools.custom`` modules."""

from __future__ import annotations

from pathlib import Path

import pytest
from haystack.tools import ComponentTool, Tool

from zaumzeug.runtime.factory import RuntimeFactoryError, build_agent_tools
from zaumzeug.runtime.tools.custom import (
    CustomToolError,
    load_custom_tools,
    parse_custom_tool_ref,
)

_FUNCTION_TOOL = '''\
from haystack.tools import create_tool_from_function

def search_docs(query: str) -> str:
    """Search local documentation snippets."""
    return f"hits:{query}"

search_docs_tool = create_tool_from_function(
    search_docs,
    name="search_docs",
    description="Search local documentation snippets.",
)
'''

_COMPONENT_TOOL = '''\
from haystack import component


@component
class SearchDocs:
    """Search local documentation snippets."""

    @component.output_types(result=str)
    def run(self, query: str) -> dict[str, str]:
        return {"result": f"hits:{query}"}
'''

_BROKEN_IMPORT = '''\
import definitely_not_a_zaumzeug_module_e7s02  # noqa: F401
'''


def _write_tool(agent_dir: Path, filename: str, source: str) -> Path:
    tools_dir = agent_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    path = tools_dir / filename
    path.write_text(source, encoding="utf-8")
    return path


def test_e7_s02_ac1_imports_custom_modules(tmp_path: Path) -> None:
    """AC-1: ``tools.custom`` imports modules from the harness agent folder."""
    agent_dir = tmp_path / "agents" / "researcher"
    _write_tool(agent_dir, "search_docs.py", _FUNCTION_TOOL)

    by_path = load_custom_tools(["tools/search_docs.py"], agent_dir=agent_dir)
    assert len(by_path) == 1
    assert isinstance(by_path[0], Tool)
    assert by_path[0].name == "search_docs"

    by_dotted = load_custom_tools(["tools.search_docs"], agent_dir=agent_dir)
    assert len(by_dotted) == 1
    assert by_dotted[0].name == "search_docs"

    by_attr = load_custom_tools(
        ["tools.search_docs:search_docs_tool"],
        agent_dir=agent_dir,
    )
    assert len(by_attr) == 1
    assert by_attr[0].name == "search_docs"

    wired = build_agent_tools(
        {"tools": {"custom": ["tools/search_docs.py"]}},
        agent_dir=agent_dir,
    )
    assert any(getattr(tool, "name", None) == "search_docs" for tool in wired)


def test_e7_s02_ac2_registers_component_tool(tmp_path: Path) -> None:
    """AC-2: Custom tools register as Haystack ``ComponentTool`` (or equivalent)."""
    agent_dir = tmp_path / "agents" / "researcher"
    _write_tool(agent_dir, "search_docs.py", _COMPONENT_TOOL)

    tools = load_custom_tools(["tools.search_docs"], agent_dir=agent_dir)
    assert len(tools) == 1
    assert isinstance(tools[0], ComponentTool)
    assert "search" in tools[0].name.lower()


def test_e7_s02_import_error_includes_module_path(tmp_path: Path) -> None:
    """Import failures include the module path (serve/factory + loader)."""
    agent_dir = tmp_path / "agents" / "researcher"
    _write_tool(agent_dir, "broken.py", _BROKEN_IMPORT)

    with pytest.raises(CustomToolError, match=r"tools\.broken") as exc_info:
        load_custom_tools(["tools.broken"], agent_dir=agent_dir)
    assert "broken.py" in str(exc_info.value)
    assert exc_info.value.module_path == "tools.broken"

    with pytest.raises(RuntimeFactoryError, match=r"tools\.broken"):
        build_agent_tools(
            {"tools": {"custom": ["tools.broken"]}},
            agent_dir=agent_dir,
        )


def test_e7_s02_rejects_traversal(tmp_path: Path) -> None:
    """Custom tool refs must stay inside the agent folder."""
    with pytest.raises(CustomToolError, match="traversal"):
        parse_custom_tool_ref("tools/../secret.py")
    with pytest.raises(CustomToolError, match="agent folder"):
        parse_custom_tool_ref("/tmp/evil.py")
