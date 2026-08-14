"""Individual doctor checks (pass / warn / fail)."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import socket
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml

from pydantic import ValidationError

from zaumzeug.config import (
    AgentResolutionError,
    load_merged_agent_models,
    resolve_agent_serve,
)
from zaumzeug.config.harness_root import DEPLOY_MANIFEST
from zaumzeug.config.loader import ConfigValidationError, strip_eval_for_doctor_validation
from zaumzeug.config.loader import ConfigValidationError, load_workflow
from zaumzeug.config.resolver import ARTIFACT_MANIFEST
from zaumzeug.config.schemas import CURRENT_SDK_PHASE, HarnessConfig, PHASE_GATED_FIELDS
from zaumzeug.doctor.project import list_agent_names
from zaumzeug.doctor.report import CheckResult

MIN_PYTHON = (3, 11)

_DEPLOY_MANIFEST_REQUIRED_FIELDS = (
    "build_id",
    "source_git_sha",
    "harness_yaml_hash",
    "artifact_run_id",
    "created_at",
)

# Provider → env vars that must be set when the provider is configured (non-mock).
_PROVIDER_ENV_KEYS: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "openai_compatible": (),  # optional for localhost; placeholder key is enough
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


def _read_harness_yaml(harness_yaml: Path) -> dict[str, Any]:
    if not harness_yaml.is_file():
        return {}
    data = yaml.safe_load(harness_yaml.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def check_eval_section_phase_hint(harness_name: str, harness_dir: Path) -> CheckResult | None:
    """Warn when ``eval`` is present but still phase-gated (pre-E6-S02).

    After E6-S02, ``eval`` is removed from ``PHASE_GATED_FIELDS`` and this check
    returns ``None``.
    """
    min_phase = PHASE_GATED_FIELDS.get(("eval",))
    if min_phase is None or min_phase <= CURRENT_SDK_PHASE:
        return None

    harness_yaml = harness_dir / "harness.yaml"
    if "eval" not in _read_harness_yaml(harness_yaml):
        return None

    return CheckResult(
        name="eval_section",
        severity="warn",
        message=(
            f"`eval` in harness.yaml is Phase {min_phase}; "
            "ignored until zaumzeug eval is available"
        ),
        harness=harness_name,
    )


def _iter_agent_yaml_tools(
    harness_dir: Path,
) -> list[tuple[str, dict[str, Any]]]:
    """Return ``(agent_folder_name, tools_dict)`` for each agent with a tools block."""
    agents_dir = harness_dir / "agents"
    if not agents_dir.is_dir():
        return []
    found: list[tuple[str, dict[str, Any]]] = []
    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        agent_yaml = agent_dir / "agent.yaml"
        if not agent_yaml.is_file():
            continue
        data = yaml.safe_load(agent_yaml.read_text(encoding="utf-8")) or {}
        tools = data.get("tools")
        if isinstance(tools, dict):
            found.append((agent_dir.name, tools))
    return found


def check_phase_gated_agent_tools(
    harness_name: str,
    harness_dir: Path,
) -> CheckResult:
    """Pass when no remaining Phase-3+ tool sections are gated.

    ``tools.mcp`` is allowed (E7-S01). ``tools.custom`` is allowed (E7-S02).
    Kept as a stable check so a later gated section can fail here again.
    """
    return CheckResult(
        name="phase_gated_tools",
        severity="pass",
        message="No phase-gated agent tools (mcp/custom) blocking current phase",
        harness=harness_name,
    )


def check_custom_tools(harness_name: str, harness_dir: Path) -> list[CheckResult]:
    """AC-3 (E7-S02): Import ``tools.custom`` modules; fail with module path.

    Runs in default and ``--deploy`` modes so doctor matches serve/run.
    """
    from zaumzeug.runtime.tools.custom import CustomToolError, load_custom_tools

    results: list[CheckResult] = []
    found_any = False
    for agent_name, tools in _iter_agent_yaml_tools(harness_dir):
        custom = tools.get("custom")
        if not isinstance(custom, list) or not custom:
            continue
        found_any = True
        agent_dir = harness_dir / "agents" / agent_name
        try:
            loaded = load_custom_tools(custom, agent_dir=agent_dir)
        except CustomToolError as exc:
            results.append(
                CheckResult(
                    name="custom_tools",
                    severity="fail",
                    message=str(exc),
                    harness=harness_name,
                )
            )
            continue
        results.append(
            CheckResult(
                name="custom_tools",
                severity="pass",
                message=(
                    f"agents/{agent_name}: loaded {len(loaded)} custom tool(s)"
                ),
                harness=harness_name,
            )
        )

    if not found_any:
        return [
            CheckResult(
                name="custom_tools",
                severity="pass",
                message="No tools.custom entries",
                harness=harness_name,
            )
        ]
    return results


def check_mcp_uv_presence(harness_name: str, harness_dir: Path) -> CheckResult:
    """AC-3 (E7-S01) / AC-2 (E2-S04b): Warn when stdio MCP is configured but ``uv`` is missing.

    HTTP ``url`` entries do not require ``uv``. Non-blocking (exit 0).
    """
    stdio_configured = False
    http_only = False
    for _agent_name, tools in _iter_agent_yaml_tools(harness_dir):
        mcp = tools.get("mcp")
        if not isinstance(mcp, list) or not mcp:
            continue
        for item in mcp:
            if not isinstance(item, dict):
                continue
            if item.get("command"):
                stdio_configured = True
            elif item.get("url"):
                http_only = True

    if not stdio_configured:
        if http_only:
            return CheckResult(
                name="mcp_uv",
                severity="pass",
                message="HTTP MCP servers configured; `uv` is not required",
                harness=harness_name,
            )
        return CheckResult(
            name="mcp_uv",
            severity="pass",
            message="No MCP tools configured",
            harness=harness_name,
        )

    if shutil.which("uv"):
        return CheckResult(
            name="mcp_uv",
            severity="pass",
            message="MCP configured and `uv` is available on PATH",
            harness=harness_name,
        )

    return CheckResult(
        name="mcp_uv",
        severity="warn",
        message=(
            "MCP tools configured but `uv` was not found on PATH; "
            "stdio MCP servers are often launched via uv"
        ),
        harness=harness_name,
    )


def check_workflow_diagram_staleness(harness_name: str, harness_dir: Path) -> CheckResult:
    """AC-3 (E2-S04b): Warn when workflow.yaml is newer than the diagram."""
    workflow_yaml = harness_dir / "workflow.yaml"
    diagram_path = harness_dir / "docs" / "workflow-diagram.md"

    if not workflow_yaml.is_file():
        return CheckResult(
            name="workflow_diagram",
            severity="pass",
            message="No workflow.yaml to compare",
            harness=harness_name,
        )

    workflow_mtime = workflow_yaml.stat().st_mtime
    if not diagram_path.is_file():
        return CheckResult(
            name="workflow_diagram",
            severity="warn",
            message=(
                f"Missing {diagram_path.relative_to(harness_dir)}; "
                "run `zaumzeug compile <harness> --workflow-diagram-only`"
            ),
            harness=harness_name,
        )

    if workflow_mtime > diagram_path.stat().st_mtime:
        return CheckResult(
            name="workflow_diagram",
            severity="warn",
            message=(
                f"{workflow_yaml.name} is newer than "
                f"{diagram_path.relative_to(harness_dir)}; re-run compile to refresh"
            ),
            harness=harness_name,
        )

    return CheckResult(
        name="workflow_diagram",
        severity="pass",
        message="workflow-diagram.md is up to date with workflow.yaml",
        harness=harness_name,
    )


def check_pinned_artifact(
    harness_name: str,
    harness_dir: Path,
    *,
    agent_names: Iterable[str],
) -> list[CheckResult]:
    """AC-2 (E4-S07): Validate pinned ``agent.artifact`` has a valid manifest.

    Fail when the pin points at a directory without a readable
    ``artifact-manifest.json`` (legacy ``manifest.json`` accepted). Warn when
    the pin is an explicit ``artifacts/<run_id>/`` that differs from
    ``artifacts/current``.
    """
    from zaumzeug.compile.export import find_artifact_manifest
    from zaumzeug.config.resolver import RuntimeSource, load_agent_yaml

    checks: list[CheckResult] = []
    for agent_name in agent_names:
        try:
            _agent_yaml_path, data = load_agent_yaml(harness_dir, agent_name)
        except AgentResolutionError:
            continue

        artifact_ref = _agent_artifact_ref(data)
        if artifact_ref is None:
            continue

        try:
            resolution = resolve_agent_serve(
                harness_dir,
                harness_name=harness_name,
                agent_name=agent_name,
            )
        except AgentResolutionError as exc:
            checks.append(
                CheckResult(
                    name="pinned_artifact",
                    severity="fail",
                    message=str(exc),
                    harness=harness_name,
                )
            )
            continue

        if resolution.source is not RuntimeSource.ARTIFACT:
            continue

        agent_dir = resolution.agent_yaml_path.parent
        artifacts_root = agent_dir / "artifacts"
        pin_dir = resolution.path
        manifest_path = find_artifact_manifest(pin_dir)
        if manifest_path is None:
            checks.append(
                CheckResult(
                    name="pinned_artifact",
                    severity="fail",
                    message=(
                        f"agent '{agent_name}' pin '{artifact_ref}' is missing "
                        f"{ARTIFACT_MANIFEST} at {pin_dir}"
                    ),
                    harness=harness_name,
                )
            )
            continue

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            checks.append(
                CheckResult(
                    name="pinned_artifact",
                    severity="fail",
                    message=(
                        f"agent '{agent_name}' pin '{artifact_ref}' has invalid "
                        f"JSON in {manifest_path.name}: {exc}"
                    ),
                    harness=harness_name,
                )
            )
            continue

        if not isinstance(manifest, dict):
            checks.append(
                CheckResult(
                    name="pinned_artifact",
                    severity="fail",
                    message=(
                        f"agent '{agent_name}' pin '{artifact_ref}' "
                        f"{manifest_path.name} must be a JSON object"
                    ),
                    harness=harness_name,
                )
            )
            continue

        pin_run_id = _artifact_dir_run_id(pin_dir, manifest)
        current_run_id = _resolve_current_run_id(artifacts_root)
        pin_is_current = pin_dir.name == "current" or (
            current_run_id is not None and pin_run_id == current_run_id
        )

        if (
            current_run_id is not None
            and pin_run_id is not None
            and not pin_is_current
            and pin_dir.name != "current"
        ):
            checks.append(
                CheckResult(
                    name="pinned_artifact",
                    severity="warn",
                    message=(
                        f"agent '{agent_name}' pins run '{pin_run_id}' "
                        f"({artifact_ref}) while artifacts/current points to "
                        f"'{current_run_id}'; serve uses the pin — update "
                        f"`agent.artifact` or retarget current to roll forward"
                    ),
                    harness=harness_name,
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="pinned_artifact",
                    severity="pass",
                    message=(
                        f"agent '{agent_name}' pin '{artifact_ref}' has valid "
                        f"{manifest_path.name}"
                        + (
                            f" (run_id={pin_run_id})"
                            if isinstance(pin_run_id, str) and pin_run_id
                            else ""
                        )
                    ),
                    harness=harness_name,
                )
            )
    return checks


def _agent_artifact_ref(data: dict[str, Any]) -> str | None:
    value = data.get("artifact")
    if value is None:
        agent = data.get("agent")
        if isinstance(agent, dict):
            value = agent.get("artifact")
    if value is None or value == "":
        return None
    return str(value)


def _artifact_dir_run_id(artifact_dir: Path, manifest: dict[str, Any]) -> str | None:
    """Prefer directory name; fall back to manifest ``run_id`` for ``current`` copies."""
    if artifact_dir.name != "current":
        return artifact_dir.name
    recorded = manifest.get("run_id")
    return recorded if isinstance(recorded, str) and recorded else None


def _resolve_current_run_id(artifacts_root: Path) -> str | None:
    """Resolve which ``<run_id>`` ``artifacts/current`` points at, if any."""
    from zaumzeug.compile.export import find_artifact_manifest

    current = artifacts_root / "current"
    if not current.exists() and not current.is_symlink():
        return None
    if current.is_symlink():
        try:
            target = Path(os.readlink(current))
        except OSError:
            target = current.resolve()
        # Symlink is typically relative ``<run_id>``.
        name = target.name
        return name if name and name != "current" else None

    manifest_path = find_artifact_manifest(current)
    if manifest_path is None:
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(manifest, dict):
        return None
    recorded = manifest.get("run_id")
    return recorded if isinstance(recorded, str) and recorded else None


def check_artifact_module_staleness(
    harness_name: str,
    harness_dir: Path,
    *,
    agent_names: Iterable[str],
) -> list[CheckResult]:
    """AC-5 (E4-S05): Warn when artifact ``source_hash`` no longer matches compile.module.

    Compares the SHA-256 of the current ``compile.module`` ``.py`` file to
    ``source_hash`` recorded in ``artifact-manifest.json`` at compile time.
    Warn-only — exit code stays 0. Skips agents without a valid artifact or
    without a recorded ``source_hash``.
    """
    # Lazy import: export helpers are DSPy-free (hash / path only).
    from zaumzeug.compile.export import (
        compute_source_file_hash,
        find_artifact_manifest,
        resolve_module_source_path,
    )
    from zaumzeug.config.resolver import RuntimeSource, load_agent_yaml

    checks: list[CheckResult] = []
    for agent_name in agent_names:
        try:
            resolution = resolve_agent_serve(
                harness_dir,
                harness_name=harness_name,
                agent_name=agent_name,
            )
        except AgentResolutionError:
            continue

        if resolution.source is not RuntimeSource.ARTIFACT:
            continue

        try:
            _path, data = load_agent_yaml(harness_dir, agent_name)
        except AgentResolutionError:
            continue

        compile_section = data.get("compile")
        if not isinstance(compile_section, dict):
            continue
        module_ref = compile_section.get("module")
        if not isinstance(module_ref, str) or not module_ref.strip():
            continue

        agent_dir = resolution.agent_yaml_path.parent
        source_path = resolve_module_source_path(agent_dir, module_ref)
        if source_path is None:
            checks.append(
                CheckResult(
                    name="artifact_module",
                    severity="pass",
                    message=(
                        f"agent '{agent_name}' artifact present; "
                        "compile.module source file not found for hash compare"
                    ),
                    harness=harness_name,
                )
            )
            continue

        manifest_path = find_artifact_manifest(resolution.path)
        if manifest_path is None:
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(manifest, dict):
            continue

        recorded = manifest.get("source_hash")
        if not isinstance(recorded, str) or not recorded:
            checks.append(
                CheckResult(
                    name="artifact_module",
                    severity="pass",
                    message=(
                        f"agent '{agent_name}' artifact has no source_hash "
                        "(re-compile to enable staleness check)"
                    ),
                    harness=harness_name,
                )
            )
            continue

        current_hash = compute_source_file_hash(source_path)
        module_hash = manifest.get("module_hash")
        module_hash_note = (
            f" (module_hash={module_hash})"
            if isinstance(module_hash, str) and module_hash
            else ""
        )
        if current_hash != recorded:
            checks.append(
                CheckResult(
                    name="artifact_module",
                    severity="warn",
                    message=(
                        f"agent '{agent_name}' artifact is stale vs compile.module "
                        f"source at {source_path.name}{module_hash_note}; "
                        f"re-run `zaumzeug compile {harness_name} --agent {agent_name}`"
                    ),
                    harness=harness_name,
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="artifact_module",
                    severity="pass",
                    message=(
                        f"agent '{agent_name}' artifact source_hash matches "
                        f"compile.module{module_hash_note}"
                    ),
                    harness=harness_name,
                )
            )
    return checks


def check_deploy_manifest(harness_name: str, harness_dir: Path) -> list[CheckResult]:
    """AC-2 (E2-S04c): Validate deploy ``manifest.json`` and pinned artifact runs."""
    manifest_path = harness_dir / DEPLOY_MANIFEST
    checks: list[CheckResult] = []

    if not manifest_path.is_file():
        checks.append(
            CheckResult(
                name="deploy_manifest",
                severity="fail",
                message=f"Missing deploy manifest at {manifest_path}",
                harness=harness_name,
            )
        )
        return checks

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        checks.append(
            CheckResult(
                name="deploy_manifest",
                severity="fail",
                message=f"Invalid JSON in {manifest_path}: {exc}",
                harness=harness_name,
            )
        )
        return checks

    if not isinstance(raw, dict):
        checks.append(
            CheckResult(
                name="deploy_manifest",
                severity="fail",
                message=f"Deploy manifest must be a JSON object: {manifest_path}",
                harness=harness_name,
            )
        )
        return checks

    missing_fields = [
        field
        for field in _DEPLOY_MANIFEST_REQUIRED_FIELDS
        if field not in raw or raw[field] in (None, "")
    ]
    if missing_fields:
        checks.append(
            CheckResult(
                name="deploy_manifest",
                severity="fail",
                message=(
                    f"Deploy manifest missing required field(s): "
                    f"{', '.join(missing_fields)}"
                ),
                harness=harness_name,
            )
        )
        return checks

    checks.append(
        CheckResult(
            name="deploy_manifest",
            severity="pass",
            message=f"deploy manifest valid at {manifest_path}",
            harness=harness_name,
        )
    )

    artifact_run_id = raw["artifact_run_id"]
    if isinstance(artifact_run_id, dict):
        for agent_name, run_id in sorted(artifact_run_id.items()):
            if not isinstance(agent_name, str) or not isinstance(run_id, str):
                checks.append(
                    CheckResult(
                        name="deploy_artifact",
                        severity="fail",
                        message=(
                            "artifact_run_id map entries must be string agent name "
                            f"→ string run id (got {agent_name!r}: {run_id!r})"
                        ),
                        harness=harness_name,
                    )
                )
                continue
            artifact_dir = (
                harness_dir / "agents" / agent_name / "artifacts" / run_id
            )
            manifest = artifact_dir / ARTIFACT_MANIFEST
            if not manifest.is_file():
                checks.append(
                    CheckResult(
                        name="deploy_artifact",
                        severity="fail",
                        message=(
                            f"Pinned artifact for agent '{agent_name}' missing "
                            f"{ARTIFACT_MANIFEST} at {artifact_dir}"
                        ),
                        harness=harness_name,
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="deploy_artifact",
                        severity="pass",
                        message=(
                            f"agent '{agent_name}' pinned run '{run_id}' has "
                            f"{ARTIFACT_MANIFEST}"
                        ),
                        harness=harness_name,
                    )
                )

    return checks


def check_workflow_config(harness_name: str, harness_dir: Path) -> list[CheckResult]:
    """Load and validate ``workflow.yaml`` with agent cross-checks."""
    workflow_yaml = harness_dir / "workflow.yaml"
    if not workflow_yaml.is_file():
        return [
            CheckResult(
                name="workflow_config",
                severity="fail",
                message=f"Missing workflow.yaml at {workflow_yaml}",
                harness=harness_name,
            )
        ]

    try:
        workflow = load_workflow(harness_dir)
    except ConfigValidationError as exc:
        return [
            CheckResult(
                name="workflow_config",
                severity="fail",
                message=str(exc),
                harness=harness_name,
            )
        ]

    return [
        CheckResult(
            name="workflow_config",
            severity="pass",
            message=(
                f"workflow.yaml valid at {workflow_yaml} "
                f"(entry={workflow.entry}, stages={len(workflow.stages)})"
            ),
            harness=harness_name,
        )
    ]


def check_harness_config(harness_name: str, harness_dir: Path) -> list[CheckResult]:
    """Load and validate harness.yaml."""
    harness_yaml = harness_dir / "harness.yaml"
    checks: list[CheckResult] = []

    eval_hint = check_eval_section_phase_hint(harness_name, harness_dir)
    if eval_hint is not None:
        checks.append(eval_hint)

    raw = _read_harness_yaml(harness_yaml)
    validation_data = strip_eval_for_doctor_validation(raw)
    try:
        HarnessConfig.model_validate(validation_data)
    except ValidationError as exc:
        checks.append(
            CheckResult(
                name="harness_config",
                severity="fail",
                message=str(
                    ConfigValidationError.from_validation_error(harness_yaml, exc)
                ),
                harness=harness_name,
            )
        )
        return checks

    checks.append(
        CheckResult(
            name="harness_config",
            severity="pass",
            message=f"harness.yaml valid at {harness_yaml}",
            harness=harness_name,
        )
    )
    return checks


def workflow_agent_names(harness_dir: Path) -> list[str]:
    """Collect agent names from workflow entry and stages."""
    try:
        workflow = load_workflow(harness_dir)
    except ConfigValidationError:
        return list_agent_names(harness_dir)

    names: list[str] = [workflow.entry]
    for stage in workflow.stages:
        if stage.agent:
            names.append(stage.agent)
    return list(dict.fromkeys(names))
