"""Hayhooks wrapper and MCP/REST/ACP boot."""

from zaumzeug.serve.acp import (
    ACP_PROTOCOL_VERSION,
    AcpPrepared,
    AcpSessionServer,
    prepare_acp,
    run_acp,
    serve_stdio,
)
from zaumzeug.serve.chainlit import (
    CHAINLIT_INSTALL_HINT,
    CHAINLIT_MISSING_MESSAGE,
    ChainlitMissingError,
    is_chainlit_available,
    require_chainlit,
)
from zaumzeug.serve.dry_run import dry_run_to_dict, dry_run_to_json, format_dry_run
from zaumzeug.serve.mcp import (
    DEFAULT_MCP_PORT,
    McpPrepared,
    prepare_mcp,
    run_mcp,
)
from zaumzeug.serve.runner import (
    DEFAULT_BIND_HOST,
    ServePrepareError,
    ServePrepared,
    prepare_serve,
    run_serve,
)
from zaumzeug.serve.validate import ServeValidationResult, validate_serve

__all__ = [
    "ACP_PROTOCOL_VERSION",
    "CHAINLIT_INSTALL_HINT",
    "CHAINLIT_MISSING_MESSAGE",
    "DEFAULT_BIND_HOST",
    "DEFAULT_MCP_PORT",
    "AcpPrepared",
    "AcpSessionServer",
    "ChainlitMissingError",
    "McpPrepared",
    "ServePrepareError",
    "ServePrepared",
    "ServeValidationResult",
    "dry_run_to_dict",
    "dry_run_to_json",
    "format_dry_run",
    "is_chainlit_available",
    "prepare_acp",
    "prepare_mcp",
    "prepare_serve",
    "require_chainlit",
    "run_acp",
    "run_mcp",
    "run_serve",
    "serve_stdio",
    "validate_serve",
]
