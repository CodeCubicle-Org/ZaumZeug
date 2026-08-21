"""Builtin, MCP, and custom agent tools (Architecture §6.5)."""

from zaumzeug.runtime.tools.calculator import (
    MAX_EXPRESSION_CHARS,
    Calculator,
    CalculatorError,
    evaluate_expression,
)
from zaumzeug.runtime.tools.catalog import (
    available_builtin_tool_ids,
    build_builtin_tools,
    create_builtin_tool,
    validate_builtin_tool_ids,
)
from zaumzeug.runtime.tools.custom import (
    CustomToolError,
    build_custom_tools,
    load_custom_tools,
    parse_custom_tool_ref,
)
from zaumzeug.runtime.tools.mcp import (
    MCP_DEFAULT_TIMEOUT_S,
    McpBoundaryError,
    build_mcp_toolsets,
    format_mcp_error,
    jsonrpc_error,
)
from zaumzeug.runtime.tools.read_file import (
    MAX_FILE_BYTES,
    ReadFile,
    ReadFileError,
    read_text_file,
    resolve_workspace_file,
)
from zaumzeug.runtime.tools.web_fetch import (
    FETCH_TIMEOUT_S,
    MAX_RESPONSE_BYTES,
    WebFetch,
    WebFetchError,
    fetch_url,
    is_public_host,
    validate_fetch_url,
)

__all__ = [
    "FETCH_TIMEOUT_S",
    "MAX_EXPRESSION_CHARS",
    "MAX_FILE_BYTES",
    "MCP_DEFAULT_TIMEOUT_S",
    "MAX_RESPONSE_BYTES",
    "Calculator",
    "CalculatorError",
    "CustomToolError",
    "McpBoundaryError",
    "ReadFile",
    "ReadFileError",
    "WebFetch",
    "WebFetchError",
    "available_builtin_tool_ids",
    "build_builtin_tools",
    "build_custom_tools",
    "build_mcp_toolsets",
    "create_builtin_tool",
    "evaluate_expression",
    "fetch_url",
    "format_mcp_error",
    "is_public_host",
    "jsonrpc_error",
    "load_custom_tools",
    "parse_custom_tool_ref",
    "read_text_file",
    "resolve_workspace_file",
    "validate_builtin_tool_ids",
    "validate_fetch_url",
]
