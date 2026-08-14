"""Wire ``tools.mcp`` YAML entries to Haystack ``MCPToolset`` (E7-S01 / E7.1).

Architecture MCP boundary: schema (typed config) + timeout (default 30s) +
idempotent construction (``eager_connect=False``) + consistent error shape.
"""

from __future__ import annotations

from typing import Any

from zaumzeug.config.schemas import McpServerConfig

MCP_DEFAULT_TIMEOUT_S = 30.0
MCP_INSTALL_HINT = 'pip install "mcp-haystack"'

# Stable envelope for MCP boundary failures (Architecture §2.4).
MCP_ERROR_OK_KEY = "ok"
MCP_ERROR_KEY = "error"


class McpBoundaryError(RuntimeError):
    """MCP client/server failure with a consistent JSON-serializable payload."""

    def __init__(
        self,
        message: str,
        *,
        error_type: str = "mcp_error",
        code: int | str | None = None,
        tool: str | None = None,
        server: str | None = None,
    ) -> None:
        self.error_type = error_type
        self.code = code
        self.tool = tool
        self.server = server
        self.payload = format_mcp_error(
            message,
            error_type=error_type,
            code=code,
            tool=tool,
            server=server,
        )
        super().__init__(message)


def format_mcp_error(
    message: str | BaseException,
    *,
    error_type: str = "mcp_error",
    code: int | str | None = None,
    tool: str | None = None,
    server: str | None = None,
) -> dict[str, Any]:
    """Return the Architecture MCP error envelope.

    Shape::

        {"ok": false, "error": {"type", "message", "code", "tool", "server"}}
    """
    text = str(message)
    resolved_type = _classify_mcp_error(message, error_type)
    return {
        MCP_ERROR_OK_KEY: False,
        MCP_ERROR_KEY: {
            "type": resolved_type,
            "message": text,
            "code": code,
            "tool": tool,
            "server": server,
        },
    }


def jsonrpc_error(
    message: str | BaseException,
    *,
    code: int = -32000,
    error_id: Any = None,
    tool: str | None = None,
    server: str | None = None,
) -> dict[str, Any]:
    """JSON-RPC 2.0 error wrapping :func:`format_mcp_error` in ``error.data``."""
    payload = format_mcp_error(
        message,
        code=code,
        tool=tool,
        server=server,
    )
    return {
        "jsonrpc": "2.0",
        "id": error_id,
        "error": {
            "code": code,
            "message": payload[MCP_ERROR_KEY]["message"],
            "data": payload,
        },
    }


def _classify_mcp_error(message: str | BaseException, default: str) -> str:
    name = type(message).__name__ if isinstance(message, BaseException) else ""
    text = str(message).lower()
    combined = f"{name} {text}".lower()
    if "timeout" in combined:
        return "mcp_timeout"
    if "connection" in combined or "unavailable" in combined:
        return "mcp_unavailable"
    if "invocation" in combined:
        return "mcp_invoke"
    if "config" in combined or "validation" in combined:
        return "mcp_config"
    return default


def _require_mcp_haystack() -> tuple[Any, Any, Any]:
    try:
        from haystack_integrations.tools.mcp import (
            MCPToolset,
            StdioServerInfo,
            StreamableHttpServerInfo,
        )
    except ImportError as exc:
        raise McpBoundaryError(
            f"MCP tools require mcp-haystack ({MCP_INSTALL_HINT}): {exc}",
            error_type="mcp_unavailable",
        ) from exc
    return MCPToolset, StdioServerInfo, StreamableHttpServerInfo


def _coerce_entries(entries: list[Any]) -> list[McpServerConfig]:
    configs: list[McpServerConfig] = []
    for item in entries:
        if isinstance(item, McpServerConfig):
            configs.append(item)
        elif isinstance(item, dict):
            configs.append(McpServerConfig.model_validate(item))
        else:
            raise McpBoundaryError(
                f"tools.mcp entry must be a mapping, got {type(item).__name__}",
                error_type="mcp_config",
            )
    return configs


def build_mcp_toolsets(entries: list[Any] | None) -> list[Any]:
    """Build Haystack ``MCPToolset`` instances from ``tools.mcp`` config.

    Construction is deferred (``eager_connect=False``) so config validation and
    agent build stay idempotent; the toolset connects on first warm-up/invoke.
    """
    if not entries:
        return []

    MCPToolset, StdioServerInfo, StreamableHttpServerInfo = _require_mcp_haystack()
    toolsets: list[Any] = []
    for config in _coerce_entries(entries):
        timeout = config.timeout_s if config.timeout_s else MCP_DEFAULT_TIMEOUT_S
        try:
            if config.command:
                server_info = StdioServerInfo(
                    command=config.command,
                    args=list(config.args) if config.args else None,
                    env=dict(config.env) if config.env else None,
                )
            else:
                assert config.url is not None
                server_info = StreamableHttpServerInfo(
                    url=config.url,
                    timeout=int(timeout),
                )
            toolset = MCPToolset(
                server_info=server_info,
                tool_names=config.tool_names,
                connection_timeout=timeout,
                invocation_timeout=timeout,
                eager_connect=False,
            )
        except McpBoundaryError:
            raise
        except Exception as exc:
            raise McpBoundaryError(
                str(exc),
                error_type=_classify_mcp_error(exc, "mcp_error"),
                server=config.name,
            ) from exc
        toolsets.append(toolset)
    return toolsets
