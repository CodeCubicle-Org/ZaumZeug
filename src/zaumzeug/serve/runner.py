"""Hayhooks serve runner — canonical entry for ``zaumzeug serve`` (E3-S02)."""

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

from zaumzeug.doctor.project import find_project_root
from zaumzeug.runtime.factory import build_agent
from zaumzeug.runtime.model_router import ModelRouter
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

    def __init__(self, agent: Agent, *, router: ModelRouter) -> None:
        super().__init__()
        self._agent = agent
        self._router = router

    def setup(self) -> None:
        self.pipeline = self._agent

    def run_api(self, question: str) -> str:
        """Handle ``POST /{pipeline}/run``."""
        result = self._agent.run(messages=[ChatMessage.from_user(question)])
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
        """
        del model
        chat_messages = [
            ChatMessage.from_openai_dict_format(message) for message in messages
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
) -> AgentPipelineWrapper:
    """Register a factory-built agent as a Hayhooks pipeline (OpenAI + /run)."""
    if registry.get(pipeline_name) is not None:
        registry.remove(pipeline_name)

    wrapper = AgentPipelineWrapper(agent, router=router)
    wrapper.setup()
    wrapper._is_run_api_implemented = True
    wrapper._is_run_chat_completion_implemented = True

    registry.add(
        pipeline_name,
        wrapper,
        metadata={
            "description": f"ZaumZeug harness entry agent ({pipeline_name})",
            "request_model": None,
            "skip_mcp": True,
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
) -> ServePrepared:
    """Validate config, build the entry agent via factory, and create Hayhooks app.

    Does not bind a socket. Call :func:`run_app` (or :func:`run_serve`) to listen.
    """
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
    assert validation.port is not None

    router = ModelRouter(validation.merged_models, project_root=root)
    agent = build_agent(
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
        agent=agent,
        router=router,
    )

    return ServePrepared(
        harness_name=validation.harness_name,
        harness_dir=validation.harness_dir,
        agent_name=validation.entry.agent_name,
        host=bind_host,
        port=validation.port,
        app=app,
        agent=agent,
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
) -> int:
    """Validate, build agent, and start Hayhooks (blocking). Returns process exit code."""
    try:
        prepared = prepare_serve(
            harness_name,
            project_root=project_root,
            deploy=deploy,
            host=host,
        )
    except ServePrepareError as exc:
        print(format_dry_run(exc.validation), file=sys.stderr)
        return exc.validation.exit_code

    base = f"http://{prepared.host}:{prepared.port}"
    print(
        f"Serving harness '{prepared.harness_name}' "
        f"(entry agent: {prepared.agent_name}) at {base}/v1"
    )
    print(f"  POST {base}/v1/chat/completions")
    print(f"  GET  {base}/v1/models")
    run_app(prepared.app, host=prepared.host, port=prepared.port)
    return 0
