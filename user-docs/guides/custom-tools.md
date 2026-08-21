# Custom tools

Add Python tools under `agents/<name>/tools/` and list them in `tools.custom`. ZaumZeug imports those modules at doctor, serve, and run time and registers them as Haystack tools.

## Layout

```text
usr-harnesses/<harness>/
└── agents/<agent-name>/
    ├── agent.yaml
    └── tools/
        ├── __init__.py
        └── search_docs.py
```

## `agent.yaml`

```yaml
tools:
  builtin: [web_fetch]
  custom:
    - tools/search_docs.py          # path relative to the agent folder
    # - tools.search_docs           # dotted module (same file)
    # - tools.search_docs:search_docs_tool  # one named export
```

Accepted entry forms:

| Entry | Resolves to |
|---|---|
| `tools/search_docs.py` | `agents/<name>/tools/search_docs.py` |
| `tools.search_docs` | same file; collect exported tools |
| `tools.search_docs:search_docs_tool` | that attribute only |

Only files listed in `tools.custom` are copied into `deploy/<harness>/` (`zaumzeug deploy`). Extra `.py` files under `tools/` stay in the dev tree.

## Example — function tool

`agents/<name>/tools/search_docs.py`:

```python
from haystack.tools import create_tool_from_function

def search_docs(query: str) -> str:
    """Search local notes for the query (demo)."""
    notes = {
        "zaumzeug": "ZaumZeug is a harness SDK: workflow + named agents.",
        "workflow": "Serial stages in workflow.yaml; entry agent runs first.",
    }
    key = query.strip().lower()
    for token, snippet in notes.items():
        if token in key:
            return snippet
    return f"No local docs for: {query}"

search_docs_tool = create_tool_from_function(
    search_docs,
    name="search_docs",
    description="Search local documentation snippets for a query.",
)
```

Functions need type hints. The loader also accepts a Haystack `Tool` instance, `@tool`, or a named attribute.

## Example — `ComponentTool`

Wrap a Haystack `@component` (same pattern as builtin `web_fetch`):

```python
from haystack import component


@component
class SearchDocs:
    """Search local documentation snippets."""

    @component.output_types(result=str)
    def run(self, query: str) -> dict[str, str]:
        return {"result": f"No local docs for: {query}"}
```

List `tools.search_docs` (or `tools/search_docs.py`). The loader instantiates the component and registers a `ComponentTool`.

## Failures

Import errors fail **`zaumzeug doctor`** and **`zaumzeug serve` / `zaumzeug run`** with the module path and expected file, for example:

```text
failed to import custom tool module 'tools.broken' (tools.custom='tools.broken').
Expected file: .../agents/researcher/tools/broken.py. Import error: ...
```

Keep modules inside `agents/<name>/tools/` — traversal (`../`) and absolute paths are rejected.

## Related

- [CLI — doctor](../reference/cli.md#zaumzeug-doctor) — `custom_tools` check
- Builtin catalog (`web_fetch`) is separate: `tools.builtin` in `agent.yaml`
- External MCP servers: `tools.mcp` — see [CLI — mcp](../reference/cli.md#zaumzeug-mcp)
- Cursor as MCP host: [Cursor MCP setup](cursor-mcp.md)
