"""ACP (Agent Client Protocol) stdio adapter — ``zaumzeug acp`` (E7-S05).

Zed / JetBrains / Neovim spawn this process and speak JSON-RPC 2.0 over
newline-delimited stdio. This is **Agent Client Protocol**, not IBM ACP/A2A.

Stdout is reserved for protocol messages. Status and logs go to stderr.
"""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from haystack.components.agents import Agent
from haystack.dataclasses import ChatMessage

from zaumzeug.config.harness_root import harness_root_segment, is_deploy_mode
from zaumzeug.doctor.project import find_project_root
from zaumzeug.runtime.factory import build_agent_bundle
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.runtime.preprocess import preprocess_user_text
from zaumzeug.serve.dry_run import format_dry_run
from zaumzeug.serve.runner import ServePrepareError, _assistant_text
from zaumzeug.serve.validate import ServeValidationResult, validate_serve

# ACP v1 major version (https://agentclientprotocol.com/protocol/v1/initialization).
ACP_PROTOCOL_VERSION = 1
JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603


def _sdk_version() -> str:
    try:
        from importlib.metadata import version

        return version("zaumzeug")
    except Exception:
        return "0.1.0"


@dataclass(slots=True)
class AcpPrepared:
    """Validated harness plus a factory-built entry agent for ACP stdio."""

    harness_name: str
    harness_dir: Path
    agent_name: str
    agent: Agent
    router: ModelRouter
    validation: ServeValidationResult
    input_rewrite_template: str | None = None


@dataclass
class AcpSessionServer:
    """In-memory ACP v1 agent: initialize, session/new, session/prompt."""

    prepared: AcpPrepared
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)

    def handle_raw(self, raw: str) -> list[dict[str, Any]]:
        """Parse one NDJSON line and return outbound JSON-RPC objects."""
        stripped = raw.strip()
        if not stripped:
            return []
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            return [
                _jsonrpc_error(
                    None,
                    JSONRPC_PARSE_ERROR,
                    f"Parse error: {exc}",
                )
            ]
        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
            error_id = payload.get("id") if isinstance(payload, dict) else None
            return [
                _jsonrpc_error(
                    error_id,
                    JSONRPC_INVALID_REQUEST,
                    "Invalid Request: ACP payload must be a JSON-RPC 2.0 object",
                )
            ]
        return self.handle_message(payload)

    def handle_message(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        method = payload.get("method")
        msg_id = payload.get("id")
        params = payload.get("params")
        if params is None:
            params = {}
        if not isinstance(params, dict):
            if msg_id is None:
                return []
            return [
                _jsonrpc_error(
                    msg_id,
                    JSONRPC_INVALID_PARAMS,
                    "Invalid params: expected an object",
                )
            ]
        if not isinstance(method, str) or not method.strip():
            if msg_id is None:
                return []
            return [
                _jsonrpc_error(
                    msg_id,
                    JSONRPC_INVALID_REQUEST,
                    "Invalid Request: missing method",
                )
            ]

        if method == "initialize":
            return [_jsonrpc_result(msg_id, self._initialize(params))]
        if method == "session/new":
            return [_jsonrpc_result(msg_id, self._session_new(params))]
        if method == "session/prompt":
            return self._session_prompt(msg_id, params)
        if method == "session/cancel":
            return []
        if msg_id is None:
            return []
        return [
            _jsonrpc_error(
                msg_id,
                JSONRPC_METHOD_NOT_FOUND,
                f"Method not found: {method}",
            )
        ]

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        del params
        return {
            "protocolVersion": ACP_PROTOCOL_VERSION,
            "agentCapabilities": {
                "loadSession": False,
                "promptCapabilities": {
                    "image": False,
                    "audio": False,
                    "embeddedContext": False,
                },
                "mcpCapabilities": {
                    "http": False,
                    "sse": False,
                },
            },
            "agentInfo": {
                "name": f"zaumzeug-{self.prepared.harness_name}",
                "title": f"ZaumZeug ({self.prepared.harness_name})",
                "version": _sdk_version(),
            },
            "authMethods": [],
        }

    def _session_new(self, params: dict[str, Any]) -> dict[str, Any]:
        session_id = str(uuid.uuid4())
        cwd = params.get("cwd")
        self.sessions[session_id] = {
            "cwd": cwd if isinstance(cwd, str) else None,
        }
        return {"sessionId": session_id}

    def _session_prompt(
        self,
        msg_id: Any,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        session_id = params.get("sessionId")
        if not isinstance(session_id, str) or session_id not in self.sessions:
            return [
                _jsonrpc_error(
                    msg_id,
                    JSONRPC_INVALID_PARAMS,
                    "Invalid params: unknown or missing sessionId",
                )
            ]
        text = _prompt_text(params.get("prompt"))
        rewritten = preprocess_user_text(
            self.prepared.input_rewrite_template,
            text,
        )
        try:
            result = self.prepared.agent.run(
                messages=[ChatMessage.from_user(rewritten)],
            )
            reply = _assistant_text(result)
        except Exception as exc:  # noqa: BLE001 — surface as JSON-RPC
            return [
                _jsonrpc_error(
                    msg_id,
                    JSONRPC_INTERNAL_ERROR,
                    f"Agent error: {exc}",
                )
            ]

        outbound: list[dict[str, Any]] = []
        if reply:
            outbound.append(
                {
                    "jsonrpc": "2.0",
                    "method": "session/update",
                    "params": {
                        "sessionId": session_id,
                        "update": {
                            "sessionUpdate": "agent_message_chunk",
                            "content": {"type": "text", "text": reply},
                        },
                    },
                }
            )
        outbound.append(
            _jsonrpc_result(msg_id, {"stopReason": "end_turn"})
        )
        return outbound


def _prompt_text(prompt: Any) -> str:
    if isinstance(prompt, str):
        return prompt
    if not isinstance(prompt, list):
        return ""
    parts: list[str] = []
    for block in prompt:
        if not isinstance(block, dict):
            continue
        text = block.get("text")
        if isinstance(text, str) and text:
            parts.append(text)
    return "\n".join(parts)


def _jsonrpc_result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _jsonrpc_error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": code, "message": message},
    }


def _write_jsonrpc(writer: TextIO, message: dict[str, Any]) -> None:
    writer.write(json.dumps(message, separators=(",", ":")) + "\n")
    writer.flush()


def prepare_acp(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
) -> AcpPrepared:
    """Validate config and build the entry agent for ACP stdio.

    Does not start the JSON-RPC loop. Call :func:`serve_stdio` or :func:`run_acp`.
    The factory still wires ``tools.mcp`` (internal MCP client) when declared.
    """
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

    router = ModelRouter(validation.merged_models, project_root=root)
    built = build_agent_bundle(
        validation.harness_dir,
        harness_name=validation.harness_name,
        agent_name=validation.entry.agent_name,
        router=router,
    )
    return AcpPrepared(
        harness_name=validation.harness_name,
        harness_dir=validation.harness_dir,
        agent_name=validation.entry.agent_name,
        agent=built.agent,
        router=router,
        validation=validation,
        input_rewrite_template=built.input_rewrite_template,
    )


def serve_stdio(
    prepared: AcpPrepared,
    *,
    reader: TextIO | None = None,
    writer: TextIO | None = None,
) -> None:
    """Read NDJSON JSON-RPC from *reader* and write replies to *writer*."""
    inbound = sys.stdin if reader is None else reader
    outbound = sys.stdout if writer is None else writer
    server = AcpSessionServer(prepared)
    while True:
        line = inbound.readline()
        if line == "":
            break
        for message in server.handle_raw(line):
            _write_jsonrpc(outbound, message)


def run_acp(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
) -> int:
    """Validate, build the entry agent, and serve ACP on stdio. Returns exit code."""
    protocol_out = sys.stdout
    sys.stdout = sys.stderr
    try:
        try:
            prepared = prepare_acp(
                harness_name,
                project_root=project_root,
                deploy=deploy,
            )
        except ServePrepareError as exc:
            print(format_dry_run(exc.validation), file=sys.stderr)
            return exc.validation.exit_code

        root_label = harness_root_segment(deploy=is_deploy_mode(deploy_flag=deploy))
        print(
            f"ACP stdio for harness '{prepared.harness_name}' from {root_label}/ "
            f"(entry agent: {prepared.agent_name}). "
            "Agent Client Protocol JSON-RPC on stdin/stdout "
            "(not IBM ACP / A2A).",
            file=sys.stderr,
        )
        serve_stdio(prepared, reader=sys.stdin, writer=protocol_out)
        return 0
    finally:
        sys.stdout = protocol_out
