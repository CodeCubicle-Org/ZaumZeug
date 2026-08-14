"""Hayhooks MCP server boot — canonical entry for ``zaumzeug mcp`` (E7-S01)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from haystack.components.agents import Agent
from hayhooks.server.utils.mcp_utils import create_mcp_server, create_starlette_app
from hayhooks.settings import settings as hayhooks_settings
from starlette.responses import JSONResponse

from zaumzeug.config.harness_root import harness_root_segment, is_deploy_mode
from zaumzeug.doctor.project import find_project_root
from zaumzeug.runtime.factory import build_agent_bundle
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.runtime.tools.mcp import jsonrpc_error
from zaumzeug.serve.dry_run import format_dry_run
from zaumzeug.serve.runner import (
    DEFAULT_BIND_HOST,
    ServePrepareError,
    _enforce_localhost_bind,
    _register_agent_pipeline,
)
from zaumzeug.serve.validate import ServeValidationResult, validate_serve

DEFAULT_MCP_PORT = 1417
JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_INTERNAL_ERROR = -32000


def _mcp_port(validation: ServeValidationResult, port_override: int | None) -> int:
    if port_override is not None:
        return port_override
    harness = validation.harness_config
    if harness and harness.serve and harness.serve.hayhooks:
        return harness.serve.hayhooks.mcp_port
    return DEFAULT_MCP_PORT


def _configure_hayhooks_mcp(*, host: str, port: int, pipelines_dir: Path) -> None:
    hayhooks_settings.mcp_host = host
    hayhooks_settings.mcp_port = port
    hayhooks_settings.pipelines_dir = str(pipelines_dir)


def mcp_jsonrpc_error_response(
    message: str | BaseException,
    *,
    code: int = JSONRPC_INTERNAL_ERROR,
    error_id: Any = None,
    tool: str | None = None,
    server: str | None = None,
    status_code: int = 200,
) -> JSONResponse:
    """JSON-RPC 2.0 error with Architecture MCP envelope in ``error.data``."""
    return JSONResponse(
        jsonrpc_error(
            message,
            code=code,
            error_id=error_id,
            tool=tool,
            server=server,
        ),
        status_code=status_code,
    )


@dataclass(slots=True)
class McpPrepared:
    """Validated harness plus a ready-to-bind Hayhooks MCP Starlette app."""

    harness_name: str
    harness_dir: Path
    agent_name: str
    host: str
    port: int
    app: Any
    agent: Agent
    router: ModelRouter
    validation: ServeValidationResult


def prepare_mcp(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
    host: str = DEFAULT_BIND_HOST,
    port: int | None = None,
) -> McpPrepared:
    """Validate config, build the entry agent, and create the Hayhooks MCP app.

    Does not bind a socket. Serves Streamable HTTP at ``/mcp`` (plus ``/status``).
    Optional ``port`` overrides ``serve.hayhooks.mcp_port`` (default 1417).
    """
    import tempfile

    bind_host = _enforce_localhost_bind(host)
    root = Path(project_root) if project_root is not None else find_project_root()
    validation = validate_serve(
        harness_name,
        project_root=root,
        deploy=deploy,
    )
    if not validation.ok:
        raise ServePrepareError(validation)

    assert validation.entry is not None
    assert validation.merged_models is not None

    mcp_port = _mcp_port(validation, port)
    router = ModelRouter(validation.merged_models, project_root=root)
    built = build_agent_bundle(
        validation.harness_dir,
        harness_name=validation.harness_name,
        agent_name=validation.entry.agent_name,
        router=router,
    )

    pipelines_dir = Path(tempfile.mkdtemp(prefix="zaumzeug-hayhooks-mcp-pipelines-"))
    _configure_hayhooks_mcp(
        host=bind_host,
        port=mcp_port,
        pipelines_dir=pipelines_dir,
    )

    # Registry metadata (request_model) is filled by add_pipeline_api_route.
    fastapi_app = FastAPI()
    _register_agent_pipeline(
        fastapi_app,
        pipeline_name=validation.harness_name,
        agent=built.agent,
        router=router,
        input_rewrite_template=built.input_rewrite_template,
        skip_mcp=False,
    )

    server = create_mcp_server(name=f"zaumzeug-{validation.harness_name}")
    app = create_starlette_app(server, debug=False, json_response=True)
    asgi_app = _McpErrorASGI(app, harness_name=validation.harness_name)

    return McpPrepared(
        harness_name=validation.harness_name,
        harness_dir=validation.harness_dir,
        agent_name=validation.entry.agent_name,
        host=bind_host,
        port=mcp_port,
        app=asgi_app,
        agent=built.agent,
        router=router,
        validation=validation,
    )


class _McpErrorASGI:
    """ASGI wrapper: malformed ``POST /mcp`` bodies get a JSON-RPC error envelope."""

    def __init__(self, app: Any, *, harness_name: str) -> None:
        self.app = app
        self.harness_name = harness_name

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:  # type: ignore[no-untyped-def]
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path.rstrip("/") != "/mcp" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        body = b""
        more = True
        while more:
            message = await receive()
            body += message.get("body", b"")
            more = bool(message.get("more_body", False))

        error = _mcp_envelope_error(body, harness_name=self.harness_name)
        if error is not None:
            await error(scope, receive, send)
            return

        replayed = False

        async def replay_receive() -> dict[str, Any]:
            nonlocal replayed
            if replayed:
                return {"type": "http.disconnect"}
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)


def _mcp_envelope_error(raw: bytes, *, harness_name: str) -> JSONResponse | None:
    """Return a JSON-RPC error response when the MCP body is not a valid envelope."""
    if not raw:
        return mcp_jsonrpc_error_response(
            "Parse error: empty MCP request body",
            code=JSONRPC_PARSE_ERROR,
            server=harness_name,
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return mcp_jsonrpc_error_response(
            f"Parse error: {exc}",
            code=JSONRPC_PARSE_ERROR,
            server=harness_name,
        )
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        error_id = payload.get("id") if isinstance(payload, dict) else None
        return mcp_jsonrpc_error_response(
            "Invalid Request: MCP payload must be a JSON-RPC 2.0 object",
            code=JSONRPC_INVALID_REQUEST,
            error_id=error_id,
            server=harness_name,
        )
    method = payload.get("method")
    if not isinstance(method, str) or not method.strip():
        return mcp_jsonrpc_error_response(
            "Invalid Request: missing method",
            code=JSONRPC_INVALID_REQUEST,
            error_id=payload.get("id"),
            server=harness_name,
        )
    return None


def run_mcp(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
    host: str = DEFAULT_BIND_HOST,
    port: int | None = None,
) -> int:
    """Validate, build agent, and start Hayhooks MCP (blocking). Returns exit code."""
    import uvicorn

    try:
        prepared = prepare_mcp(
            harness_name,
            project_root=project_root,
            deploy=deploy,
            host=host,
            port=port,
        )
    except ServePrepareError as exc:
        print(format_dry_run(exc.validation), file=sys.stderr)
        return exc.validation.exit_code

    base = f"http://{prepared.host}:{prepared.port}"
    root_label = harness_root_segment(deploy=is_deploy_mode(deploy_flag=deploy))
    print(
        f"Serving MCP for harness '{prepared.harness_name}' from {root_label}/ "
        f"(entry agent: {prepared.agent_name}) at {base}/mcp"
    )
    print(f"  POST {base}/mcp")
    print(f"  GET  {base}/status")
    uvicorn.run(prepared.app, host=prepared.host, port=prepared.port, log_level="warning")
    return 0
