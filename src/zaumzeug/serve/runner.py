"""Hayhooks serve runner — canonical entry for ``zaumzeug serve`` (E3-S02 / E5-S03)."""

from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from haystack.components.agents import Agent
from haystack.dataclasses import ChatMessage
from hayhooks import BasePipelineWrapper, create_app, run_app
from hayhooks.server.pipelines.registry import registry
from hayhooks.server.utils.deploy_utils import add_pipeline_api_route
from hayhooks.settings import settings as hayhooks_settings

from zaumzeug.config.harness_root import harness_root_segment, is_deploy_mode
from zaumzeug.doctor.project import find_project_root
from zaumzeug.runtime.factory import build_agent_bundle
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.runtime.preprocess import preprocess_openai_messages, preprocess_user_text
from zaumzeug.serve.dry_run import format_dry_run
from zaumzeug.serve.validate import ServeValidationResult, validate_serve

# Phase 1 security: localhost only (Architecture §14). No 0.0.0.0 without future config.
DEFAULT_BIND_HOST = "127.0.0.1"
_ALLOWED_BIND_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _enforce_localhost_bind(host: str) -> str:
    """Reject non-loopback binds in Phase 1 (Architecture §14)."""
    normalized = host.strip().lower()
    if normalized not in _ALLOWED_BIND_HOSTS:
        raise ValueError(
            f"Phase 1 serve binds localhost only (got {host!r}). "
            "Wide-open binds (e.g. 0.0.0.0) require a future explicit config."
        )
    return host.strip()


def _request_model_id(body: dict[str, Any] | None) -> str | None:
    """Extract optional ZaumZeug ``model_id`` override from an OpenAI request body."""
    if not isinstance(body, dict):
        return None
    raw = body.get("model_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


class AgentPipelineWrapper(BasePipelineWrapper):
    """Hayhooks wrapper around a factory-built Haystack ``Agent``."""

    def __init__(
        self,
        agent: Agent,
        *,
        router: ModelRouter,
        input_rewrite_template: str | None = None,
    ) -> None:
        super().__init__()
        self._agent = agent
        self._router = router
        self._input_rewrite_template = input_rewrite_template

    def setup(self) -> None:
        self.pipeline = self._agent

    def run_api(self, question: str) -> str:
        """Run the harness entry agent with a user question.

        Exposed as an MCP tool when serving via ``zaumzeug mcp``.
        """
        text = preprocess_user_text(self._input_rewrite_template, question)
        result = self._agent.run(messages=[ChatMessage.from_user(text)])
        return _assistant_text(result)

    def run_chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        body: dict[str, Any],
    ) -> str:
        """Handle OpenAI-compatible ``POST /v1/chat/completions``.

        OpenAI ``model`` is the harness/pipeline identity. Optional request
        ``model_id`` selects the LLM from the stage-scoped ModelRouter registry.
        Applies optional artifact ``input_rewrite`` before ``Agent.run`` (E4-S03b).
        """
        del model
        rewritten = preprocess_openai_messages(self._input_rewrite_template, messages)
        chat_messages = [
            ChatMessage.from_openai_dict_format(message) for message in rewritten
        ]
        override = _request_model_id(body)
        previous = self._agent.chat_generator
        if override is not None:
            self._agent.chat_generator = self._router.build_generator(override)
        try:
            result = self._agent.run(messages=chat_messages)
            return _assistant_text(result)
        finally:
            self._agent.chat_generator = previous


@dataclass(slots=True)
class ServePrepared:
    """Validated harness plus a ready-to-bind Hayhooks FastAPI app."""

    harness_name: str
    harness_dir: Path
    agent_name: str
    host: str
    port: int
    app: FastAPI
    agent: Agent
    router: ModelRouter
    validation: ServeValidationResult


def _assistant_text(result: dict[str, Any]) -> str:
    last = result.get("last_message")
    text = getattr(last, "text", None) if last is not None else None
    if text:
        return str(text)
    return ""


def _configure_hayhooks(*, host: str, port: int, pipelines_dir: Path) -> None:
    """Point Hayhooks at an empty pipelines dir and Phase-1 bind defaults."""
    hayhooks_settings.host = host
    hayhooks_settings.port = port
    hayhooks_settings.pipelines_dir = str(pipelines_dir)


def _register_agent_pipeline(
    app: FastAPI,
    *,
    pipeline_name: str,
    agent: Agent,
    router: ModelRouter,
    input_rewrite_template: str | None = None,
    skip_mcp: bool = True,
) -> AgentPipelineWrapper:
    """Register a factory-built agent as a Hayhooks pipeline (OpenAI + /run)."""
    if registry.get(pipeline_name) is not None:
        registry.remove(pipeline_name)

    wrapper = AgentPipelineWrapper(
        agent,
        router=router,
        input_rewrite_template=input_rewrite_template,
    )
    wrapper.setup()
    wrapper._is_run_api_implemented = True
    wrapper._is_run_chat_completion_implemented = True

    registry.add(
        pipeline_name,
        wrapper,
        metadata={
            "description": f"ZaumZeug harness entry agent ({pipeline_name})",
            "request_model": None,
            "skip_mcp": skip_mcp,
            "skip_a2a": True,
            "a2a_card": None,
        },
    )
    add_pipeline_api_route(app, pipeline_name, wrapper)
    return wrapper


def prepare_serve(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
    host: str = DEFAULT_BIND_HOST,
    port: int | None = None,
) -> ServePrepared:
    """Validate config, build the entry agent via factory, and create Hayhooks app.

    Does not bind a socket. Call :func:`run_app` (or :func:`run_serve`) to listen.
    Optional ``port`` overrides ``serve.hayhooks.port`` from harness.yaml.
    When ``deploy`` is true (or ``HARNESS_ROOT=deploy``), loads only
    ``deploy/<name>/`` and requires a valid deploy ``manifest.json`` (E5-S03).
    """
    bind_host = _enforce_localhost_bind(host)
    root = Path(project_root) if project_root is not None else find_project_root()
    validation = validate_serve(
        harness_name,
        project_root=root,
        deploy=deploy,
        port=port,
    )
    if not validation.ok:
        raise ServePrepareError(validation)

    assert validation.entry is not None
    assert validation.merged_models is not None
    assert validation.port is not None

    router = ModelRouter(validation.merged_models, project_root=root)
    built = build_agent_bundle(
        validation.harness_dir,
        harness_name=validation.harness_name,
        agent_name=validation.entry.agent_name,
        router=router,
    )

    pipelines_dir = Path(tempfile.mkdtemp(prefix="zaumzeug-hayhooks-pipelines-"))
    _configure_hayhooks(
        host=bind_host,
        port=validation.port,
        pipelines_dir=pipelines_dir,
    )
    app = create_app()
    _register_agent_pipeline(
        app,
        pipeline_name=validation.harness_name,
        agent=built.agent,
        router=router,
        input_rewrite_template=built.input_rewrite_template,
    )

    return ServePrepared(
        harness_name=validation.harness_name,
        harness_dir=validation.harness_dir,
        agent_name=validation.entry.agent_name,
        host=bind_host,
        port=validation.port,
        app=app,
        agent=built.agent,
        router=router,
        validation=validation,
    )


class ServePrepareError(RuntimeError):
    """Raised when serve validation fails before Hayhooks bind."""

    def __init__(self, validation: ServeValidationResult) -> None:
        self.validation = validation
        super().__init__(format_dry_run(validation))


def run_serve(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
    host: str = DEFAULT_BIND_HOST,
    port: int | None = None,
) -> int:
    """Validate, build agent, and start Hayhooks (blocking). Returns process exit code."""
    try:
        prepared = prepare_serve(
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
        f"Serving harness '{prepared.harness_name}' from {root_label}/ "
        f"(entry agent: {prepared.agent_name}) at {base}/v1"
    )
    print(f"  POST {base}/v1/chat/completions")
    print(f"  GET  {base}/v1/models")
    run_app(prepared.app, host=prepared.host, port=prepared.port)
    return 0
