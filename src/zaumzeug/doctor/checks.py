"""Individual doctor checks (pass / warn / fail)."""

from __future__ import annotations

import importlib
import os
import socket
import sys
from pathlib import Path
from typing import Any, Iterable

from zaumzeug.config import (
    AgentResolutionError,
    ConfigValidationError,
    load_harness,
    load_merged_agent_models,
    resolve_agent_serve,
)
from zaumzeug.config.resolver import load_workflow_yaml
from zaumzeug.doctor.project import list_agent_names
from zaumzeug.doctor.report import CheckResult

MIN_PYTHON = (3, 11)

# Provider → env vars that must be set when the provider is configured (non-mock).
_PROVIDER_ENV_KEYS: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "azure": ("AZURE_API_KEY", "AZURE_OPENAI_API_KEY"),
    "cohere": ("COHERE_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}


def check_python_version() -> CheckResult:
    """AC-1: Python 3.11+ required."""
    version = sys.version_info[:3]
    if version[:2] >= MIN_PYTHON:
        return CheckResult(
            name="python_version",
            severity="pass",
            message=f"Python {version[0]}.{version[1]}.{version[2]}",
        )
    return CheckResult(
        name="python_version",
        severity="fail",
        message=(
            f"Python {version[0]}.{version[1]}.{version[2]} is unsupported; "
            f"requires {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+"
        ),
    )


def check_package_import() -> CheckResult:
    """AC-2: Core package imports cleanly."""
    try:
        importlib.import_module("zaumzeug")
        importlib.import_module("zaumzeug.config")
    except ImportError as exc:
        return CheckResult(
            name="package_import",
            severity="fail",
            message=f"Cannot import zaumzeug: {exc}",
        )
    return CheckResult(
        name="package_import",
        severity="pass",
        message="zaumzeug package importable",
    )


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].strip()
        if "=" not in stripped:
            continue
        key, _, raw = stripped.partition("=")
        key = key.strip()
        value = raw.strip().strip("'\"")
        if key:
            values[key] = value
    return values


def _env_lookup(name: str, dotenv: dict[str, str]) -> str | None:
    if name in os.environ and os.environ[name]:
        return os.environ[name]
    if name in dotenv and dotenv[name]:
        return dotenv[name]
    return None


def _collect_model_id_refs(data: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(data, dict):
        for key, value in data.items():
            if key in {"default_model_id", "model_id"} and isinstance(value, str) and value:
                refs.add(value)
            refs.update(_collect_model_id_refs(value))
    elif isinstance(data, list):
        for item in data:
            refs.update(_collect_model_id_refs(item))
    return refs


def _live_providers(merged_models: Iterable[Any]) -> set[str]:
    providers: set[str] = set()
    for registry in merged_models:
        for entry in registry.models.values():
            if entry.provider != "mock":
                providers.add(entry.provider)
    return providers


def check_env_for_live_models(
    project_root: Path,
    *,
    live_providers: set[str],
) -> list[CheckResult]:
    """AC-3: Warn when live providers are configured but keys are missing."""
    if not live_providers:
        return [
            CheckResult(
                name="env_keys",
                severity="pass",
                message="Only mock providers configured; API keys not required",
            )
        ]

    dotenv_path = project_root / ".env"
    dotenv = _parse_dotenv(dotenv_path)
    checks: list[CheckResult] = []

    if not dotenv_path.is_file():
        checks.append(
            CheckResult(
                name="env_file",
                severity="warn",
                message=(
                    f"No .env at {dotenv_path}; live model providers configured "
                    f"({', '.join(sorted(live_providers))})"
                ),
            )
        )

    missing_keys: list[str] = []
    for provider in sorted(live_providers):
        for env_name in _PROVIDER_ENV_KEYS.get(provider, (f"{provider.upper()}_API_KEY",)):
            if _env_lookup(env_name, dotenv) is None:
                missing_keys.append(f"{env_name} (for {provider})")

    if missing_keys:
        checks.append(
            CheckResult(
                name="env_keys",
                severity="warn",
                message=f"Missing API keys for live models: {', '.join(missing_keys)}",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="env_keys",
                severity="pass",
                message="API keys present for configured live providers",
            )
        )
    return checks


def check_runtime_paths(
    harness_name: str,
    harness_dir: Path,
    *,
    agent_names: Iterable[str],
) -> list[CheckResult]:
    """AC-5: Validate serve runtime paths via the shared resolver."""
    checks: list[CheckResult] = []
    for agent_name in agent_names:
        try:
            resolution = resolve_agent_serve(
                harness_dir,
                harness_name=harness_name,
                agent_name=agent_name,
            )
            checks.append(
                CheckResult(
                    name="runtime_path",
                    severity="pass",
                    message=(
                        f"agent '{agent_name}' resolves via {resolution.source.value} "
                        f"at {resolution.path}"
                    ),
                    harness=harness_name,
                )
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
    return checks


def check_model_registry(
    harness_name: str,
    project_root: Path,
    harness_dir: Path,
    *,
    agent_names: Iterable[str],
    harness_models_path: str | None,
) -> tuple[list[CheckResult], list[Any]]:
    """AC-6: Validate merged model registries and referenced model ids."""
    checks: list[CheckResult] = []
    merged_registries: list[Any] = []

    for agent_name in agent_names:
        agent_yaml_path = harness_dir / "agents" / agent_name / "agent.yaml"
        try:
            merged = load_merged_agent_models(
                project_root=project_root,
                harness_dir=harness_dir,
                harness_models_path=harness_models_path,
                agent_name=agent_name,
            )
            merged_registries.append(merged)
        except ConfigValidationError as exc:
            checks.append(
                CheckResult(
                    name="model_registry",
                    severity="fail",
                    message=f"agent '{agent_name}': {exc}",
                    harness=harness_name,
                )
            )
            continue

        if agent_yaml_path.is_file():
            import yaml

            agent_data = yaml.safe_load(agent_yaml_path.read_text(encoding="utf-8")) or {}
            for model_id in sorted(_collect_model_id_refs(agent_data)):
                if model_id not in merged.models:
                    checks.append(
                        CheckResult(
                            name="model_registry",
                            severity="fail",
                            message=(
                                f"agent '{agent_name}' references unknown model_id "
                                f"'{model_id}'"
                            ),
                            harness=harness_name,
                        )
                    )
        checks.append(
            CheckResult(
                name="model_registry",
                severity="pass",
                message=(
                    f"agent '{agent_name}' model registry valid "
                    f"(default_model_id={merged.default_model_id})"
                ),
                harness=harness_name,
            )
        )
    return checks, merged_registries


def check_port_conflict(
    harness_name: str,
    *,
    port: int,
    host: str = "127.0.0.1",
) -> CheckResult:
    """AC-7: Warn when the configured serve port appears to be in use."""
    in_use = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        in_use = sock.connect_ex((host, port)) == 0

    if in_use:
        return CheckResult(
            name="port_conflict",
            severity="warn",
            message=f"Port {port} on {host} appears to be in use",
            harness=harness_name,
        )
    return CheckResult(
        name="port_conflict",
        severity="pass",
        message=f"Port {port} on {host} is available",
        harness=harness_name,
    )


def check_harness_config(harness_name: str, harness_dir: Path) -> list[CheckResult]:
    """Load and validate harness.yaml."""
    harness_yaml = harness_dir / "harness.yaml"
    try:
        load_harness(harness_yaml)
    except ConfigValidationError as exc:
        return [
            CheckResult(
                name="harness_config",
                severity="fail",
                message=str(exc),
                harness=harness_name,
            )
        ]
    return [
        CheckResult(
            name="harness_config",
            severity="pass",
            message=f"harness.yaml valid at {harness_yaml}",
            harness=harness_name,
        )
    ]


def workflow_agent_names(harness_dir: Path) -> list[str]:
    """Collect agent names from workflow entry and stages."""
    try:
        workflow = load_workflow_yaml(harness_dir)
    except AgentResolutionError:
        return list_agent_names(harness_dir)

    names: list[str] = []
    entry = workflow.get("entry")
    if isinstance(entry, str) and entry:
        names.append(entry)
    stages = workflow.get("stages")
    if isinstance(stages, list):
        for stage in stages:
            if isinstance(stage, dict):
                agent = stage.get("agent")
                if isinstance(agent, str) and agent:
                    names.append(agent)
    if names:
        return list(dict.fromkeys(names))
    return list_agent_names(harness_dir)
