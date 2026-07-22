"""Shared serve validation — used by dry-run and the real serve runner (E3-S02)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from zaumzeug.config import (
    AgentModelsConfig,
    AgentResolutionError,
    ConfigValidationError,
    HarnessConfig,
    ServeResolution,
    load_harness,
    load_merged_agent_models,
    load_workflow,
    resolve_serve_entry,
)
from zaumzeug.config.harness_root import harness_dir as resolve_harness_dir
from zaumzeug.config.harness_root import is_deploy_mode
from zaumzeug.doctor.checks import (
    check_deploy_manifest,
    check_model_registry,
    check_runtime_paths,
)
from zaumzeug.doctor.project import find_project_root
from zaumzeug.doctor.report import CheckResult


def _extract_tools(agent_data: dict[str, Any]) -> list[str]:
    tools: list[str] = []
    raw = agent_data.get("tools")
    if not isinstance(raw, dict):
        return tools
    builtin = raw.get("builtin")
    if isinstance(builtin, list):
        tools.extend(str(item) for item in builtin)
    mcp = raw.get("mcp")
    if isinstance(mcp, list):
        for item in mcp:
            if isinstance(item, dict) and item.get("name"):
                tools.append(str(item["name"]))
    return tools


def _serve_port(harness_config: HarnessConfig) -> int:
    if harness_config.serve and harness_config.serve.hayhooks:
        return harness_config.serve.hayhooks.port
    return 1416


@dataclass(slots=True)
class ServeValidationResult:
    """Outcome of validating a harness for ``zaumzeug serve``."""

    harness_name: str
    harness_dir: Path
    checks: list[CheckResult]
    harness_config: HarnessConfig | None = None
    entry: ServeResolution | None = None
    merged_models: AgentModelsConfig | None = None
    model_id: str | None = None
    tools: list[str] | None = None
    port: int | None = None

    @property
    def ok(self) -> bool:
        return not any(check.severity == "fail" for check in self.checks)

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1


def _resolved_serve_port(
    harness_config: HarnessConfig | None,
    port_override: int | None,
) -> int | None:
    """Return CLI ``--port`` override when set, else harness ``serve.hayhooks.port``."""
    if port_override is not None:
        return port_override
    if harness_config is None:
        return None
    return _serve_port(harness_config)


def validate_serve(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
    port: int | None = None,
) -> ServeValidationResult:
    """Validate harness config and resolved serve paths (no server bind, no LLM).

    Optional ``port`` overrides ``serve.hayhooks.port`` from harness.yaml (CI smoke).
    """
    root = Path(project_root) if project_root is not None else find_project_root()
    deploy_mode = is_deploy_mode(deploy_flag=deploy)
    harness_path = resolve_harness_dir(root, harness_name, deploy=deploy_mode)
    checks: list[CheckResult] = []

    harness_yaml = harness_path / "harness.yaml"
    if not harness_yaml.is_file():
        checks.append(
            CheckResult(
                name="harness_discovery",
                severity="fail",
                message=f"Harness '{harness_name}' not found at {harness_path}",
                harness=harness_name,
            )
        )
        return ServeValidationResult(
            harness_name=harness_name,
            harness_dir=harness_path,
            checks=checks,
        )

    harness_config: HarnessConfig | None = None
    try:
        harness_config = load_harness(harness_yaml)
    except ConfigValidationError as exc:
        checks.append(
            CheckResult(
                name="harness_config",
                severity="fail",
                message=str(exc),
                harness=harness_name,
            )
        )
        return ServeValidationResult(
            harness_name=harness_name,
            harness_dir=harness_path,
            checks=checks,
        )

    try:
        load_workflow(harness_path)
    except ConfigValidationError as exc:
        checks.append(
            CheckResult(
                name="workflow_config",
                severity="fail",
                message=str(exc),
                harness=harness_name,
            )
        )
        return ServeValidationResult(
            harness_name=harness_name,
            harness_dir=harness_path,
            checks=checks,
            harness_config=harness_config,
            port=_resolved_serve_port(harness_config, port),
        )

    if deploy_mode:
        checks.extend(check_deploy_manifest(harness_name, harness_path))

    entry: ServeResolution | None = None
    try:
        entry = resolve_serve_entry(
            harness_path,
            harness_name=harness_name,
        )
    except AgentResolutionError as exc:
        checks.append(
            CheckResult(
                name="runtime_path",
                severity="fail",
                message=str(exc),
                harness=harness_name,
            )
        )
        return ServeValidationResult(
            harness_name=harness_name,
            harness_dir=harness_path,
            checks=checks,
            harness_config=harness_config,
            port=_resolved_serve_port(harness_config, port),
        )

    agent_yaml_path = entry.agent_yaml_path
    agent_data: dict[str, Any] = {}
    if agent_yaml_path.is_file():
        loaded = yaml.safe_load(agent_yaml_path.read_text(encoding="utf-8"))
        agent_data = loaded if isinstance(loaded, dict) else {}

    model_checks, merged_registries = check_model_registry(
        harness_name,
        root,
        harness_path,
        agent_names=[entry.agent_name],
        harness_models_path=harness_config.models,
    )
    checks.extend(model_checks)
    checks.extend(
        check_runtime_paths(
            harness_name,
            harness_path,
            agent_names=[entry.agent_name],
        )
    )

    merged_models = merged_registries[0] if merged_registries else None
    model_id = merged_models.default_model_id if merged_models is not None else None
    tools = _extract_tools(agent_data)
    resolved_port = _resolved_serve_port(harness_config, port)

    return ServeValidationResult(
        harness_name=harness_name,
        harness_dir=harness_path,
        checks=checks,
        harness_config=harness_config,
        entry=entry,
        merged_models=merged_models,
        model_id=model_id,
        tools=tools,
        port=resolved_port,
    )
