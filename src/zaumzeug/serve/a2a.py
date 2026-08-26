"""Hayhooks A2A server boot — canonical entry for ``zaumzeug a2a`` (E8-S04).

Optional agent-to-agent hosting. Requires ``serve.a2a: true`` (or
``serve.a2a.enabled: true``) and ``pip install "hayhooks[a2a]"``. One process
serves one harness (NG1 multi-tenant remains out of scope).
"""

from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from haystack.components.agents import Agent
from hayhooks.settings import settings as hayhooks_settings
import uvicorn

from zaumzeug.config.harness_root import harness_root_segment, is_deploy_mode
from zaumzeug.config.schemas import A2aConfig, HarnessConfig
from zaumzeug.doctor.project import find_project_root
from zaumzeug.runtime.factory import build_agent_bundle
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.serve.a2a_extra import A2aMissingError, require_a2a
from zaumzeug.serve.dry_run import format_dry_run
from zaumzeug.serve.runner import (
    DEFAULT_BIND_HOST,
    ServePrepareError,
    _enforce_localhost_bind,
    _register_agent_pipeline,
)
from zaumzeug.serve.validate import ServeValidationResult, validate_serve

DEFAULT_A2A_PORT = 1418

A2A_DISABLED_MESSAGE = (
    "Error: serve.a2a is not enabled for this harness.\n"
    "Set `serve.a2a: true` (or `serve.a2a.enabled: true`) in harness.yaml, "
    "then run `zaumzeug a2a <name>`.\n"
    "See user-docs/guides/a2a.md."
)


class A2aDisabledError(RuntimeError):
    """Raised when ``zaumzeug a2a`` runs without ``serve.a2a`` enabled."""

    def __init__(self, message: str = A2A_DISABLED_MESSAGE) -> None:
        super().__init__(message)


@dataclass(slots=True)
class A2aPrepared:
    """Validated harness plus a ready-to-bind Hayhooks A2A Starlette app."""

    harness_name: str
    harness_dir: Path
    agent_name: str
    host: str
    port: int
    app: Any
    agent: Agent
    router: ModelRouter
    validation: ServeValidationResult
    agent_card_path: str


def _a2a_config(harness_config: HarnessConfig | None) -> A2aConfig | None:
    if harness_config is None or harness_config.serve is None:
        return None
    return harness_config.serve.a2a


def a2a_enabled(harness_config: HarnessConfig | None) -> bool:
    """Return True when ``serve.a2a`` is enabled (boolean or ``enabled: true``)."""
    cfg = _a2a_config(harness_config)
    return bool(cfg is not None and cfg.enabled)


def _a2a_port(validation: ServeValidationResult, port_override: int | None) -> int:
    if port_override is not None:
        return port_override
    cfg = _a2a_config(validation.harness_config)
    if cfg is not None:
        return cfg.port
    return DEFAULT_A2A_PORT


def _a2a_card_metadata(harness_config: HarnessConfig | None, harness_name: str) -> dict[str, Any]:
    description = None
    if harness_config is not None and harness_config.description:
        description = harness_config.description.strip() or None
    return {
        "name": harness_name,
        "description": description
        or f"ZaumZeug harness '{harness_name}' (A2A agent card)",
        "version": "1.0.0",
        "skills": [
            {
                "id": harness_name,
                "name": harness_name,
                "description": description
                or f"Delegate tasks to the ZaumZeug harness '{harness_name}'",
                "tags": ["zaumzeug", "haystack", "a2a"],
            }
        ],
    }


def _configure_hayhooks_a2a(*, host: str, port: int, pipelines_dir: Path) -> None:
    hayhooks_settings.a2a_host = host
    hayhooks_settings.a2a_port = port
    hayhooks_settings.pipelines_dir = str(pipelines_dir)
    # Advertise loopback URL clients can reach (Phase 1 localhost bind).
    hayhooks_settings.a2a_external_url = f"http://{host}:{port}"


def prepare_a2a(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
    host: str = DEFAULT_BIND_HOST,
    port: int | None = None,
) -> A2aPrepared:
    """Validate config, build the entry agent, and create the Hayhooks A2A app.

    Does not bind a socket. Requires ``serve.a2a: true`` and ``hayhooks[a2a]``.
    Optional ``port`` overrides ``serve.a2a.port`` (default 1418).
    When ``deploy`` is true (or ``HARNESS_ROOT=deploy``), loads only
    ``deploy/<name>/`` and requires a valid deploy ``manifest.json``.
    """
    require_a2a()

    bind_host = _enforce_localhost_bind(host)
    root = Path(project_root) if project_root is not None else find_project_root()
    validation = validate_serve(
        harness_name,
        project_root=root,
        deploy=deploy,
    )
    if not validation.ok:
        raise ServePrepareError(validation)

    if not a2a_enabled(validation.harness_config):
        raise A2aDisabledError()

    assert validation.entry is not None
    assert validation.merged_models is not None

    a2a_port = _a2a_port(validation, port)
    router = ModelRouter(validation.merged_models, project_root=root)
    built = build_agent_bundle(
        validation.harness_dir,
        harness_name=validation.harness_name,
        agent_name=validation.entry.agent_name,
        router=router,
    )

    pipelines_dir = Path(tempfile.mkdtemp(prefix="zaumzeug-hayhooks-a2a-pipelines-"))
    _configure_hayhooks_a2a(
        host=bind_host,
        port=a2a_port,
        pipelines_dir=pipelines_dir,
    )

    # Registry is shared with Hayhooks A2A; register the entry agent with A2A on.
    fastapi_app = FastAPI()
    _register_agent_pipeline(
        fastapi_app,
        pipeline_name=validation.harness_name,
        agent=built.agent,
        router=router,
        input_rewrite_template=built.input_rewrite_template,
        skip_mcp=True,
        skip_a2a=False,
        a2a_card=_a2a_card_metadata(validation.harness_config, validation.harness_name),
    )

    from hayhooks.server.utils.a2a_utils import create_a2a_app

    app = create_a2a_app(debug=False)
    card_path = f"/{validation.harness_name}/.well-known/agent-card.json"

    return A2aPrepared(
        harness_name=validation.harness_name,
        harness_dir=validation.harness_dir,
        agent_name=validation.entry.agent_name,
        host=bind_host,
        port=a2a_port,
        app=app,
        agent=built.agent,
        router=router,
        validation=validation,
        agent_card_path=card_path,
    )


def run_a2a(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
    host: str = DEFAULT_BIND_HOST,
    port: int | None = None,
) -> int:
    """Validate, build agent, and start the A2A server (blocking). Returns exit code."""
    try:
        prepared = prepare_a2a(
            harness_name,
            project_root=project_root,
            deploy=deploy,
            host=host,
            port=port,
        )
    except ServePrepareError as exc:
        print(format_dry_run(exc.validation), file=sys.stderr)
        return exc.validation.exit_code
    except (A2aMissingError, A2aDisabledError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    base = f"http://{prepared.host}:{prepared.port}"
    root_label = harness_root_segment(deploy=is_deploy_mode(deploy_flag=deploy))
    print(
        f"A2A hosting harness '{prepared.harness_name}' from {root_label}/ "
        f"(entry agent: {prepared.agent_name}) at {base}"
    )
    print(f"  GET  {base}{prepared.agent_card_path}")
    print(f"  POST {base}/{prepared.harness_name}/")
    print(f"  GET  {base}/status")
    uvicorn.run(
        prepared.app,
        host=prepared.host,
        port=prepared.port,
        log_config=None,
    )
    return 0
