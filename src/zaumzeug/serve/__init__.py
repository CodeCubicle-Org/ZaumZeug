"""Hayhooks wrapper and MCP/REST/ACP/A2A boot."""

from zaumzeug.serve.a2a import (
    DEFAULT_A2A_PORT,
    A2aDisabledError,
    A2aPrepared,
    a2a_enabled,
    prepare_a2a,
    run_a2a,
)
from zaumzeug.serve.a2a_extra import (
    A2A_INSTALL_HINT,
    A2A_MISSING_MESSAGE,
    A2aMissingError,
    is_a2a_available,
    require_a2a,
)
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
    "A2A_INSTALL_HINT",
    "A2A_MISSING_MESSAGE",
    "CHAINLIT_INSTALL_HINT",
    "CHAINLIT_MISSING_MESSAGE",
    "DEFAULT_A2A_PORT",
    "DEFAULT_BIND_HOST",
    "DEFAULT_MCP_PORT",
    "A2aDisabledError",
    "A2aMissingError",
    "A2aPrepared",
    "AcpPrepared",
    "AcpSessionServer",
    "ChainlitMissingError",
    "McpPrepared",
    "ServePrepareError",
    "ServePrepared",
    "ServeValidationResult",
    "a2a_enabled",
    "dry_run_to_dict",
    "dry_run_to_json",
    "format_dry_run",
    "is_a2a_available",
    "is_chainlit_available",
    "prepare_a2a",
    "prepare_acp",
    "prepare_mcp",
    "prepare_serve",
    "require_a2a",
    "require_chainlit",
    "run_a2a",
    "run_acp",
    "run_mcp",
    "run_serve",
    "serve_stdio",
    "validate_serve",
]
