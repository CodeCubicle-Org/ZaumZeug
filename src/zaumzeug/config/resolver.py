"""Runtime vs compile agent resolution (Architecture §5.2, PRD E2.3)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from zaumzeug.config.loader import ConfigValidationError, _read_yaml_mapping, load_workflow

ARTIFACT_MANIFEST = "artifact-manifest.json"


class RuntimeSource(str, Enum):
    """How serve/run loads an agent's prompts."""

    ARTIFACT = "artifact"
    SYSTEM_PROMPT = "system_prompt"


class AgentResolutionError(ValueError):
    """Agent runtime or compile resolution failed with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        harness_name: str | None = None,
        agent_name: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.harness_name = harness_name
        self.agent_name = agent_name
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ServeResolution:
    """Result of serve/run resolution for one agent."""

    harness_name: str
    agent_name: str
    source: RuntimeSource
    path: Path
    agent_yaml_path: Path


@dataclass(frozen=True, slots=True)
class CompileResolution:
    """Result of compile resolution for one agent."""

    harness_name: str
    agent_name: str
    compile_module: str
    agent_yaml_path: Path


def _agent_dir(harness_dir: Path, agent_name: str) -> Path:
    return harness_dir / "agents" / agent_name


def _agent_yaml_path(harness_dir: Path, agent_name: str) -> Path:
    return _agent_dir(harness_dir, agent_name) / "agent.yaml"


def _artifact_ref(data: dict[str, Any]) -> str | None:
    value = data.get("artifact")
    if value is None:
        agent = data.get("agent")
        if isinstance(agent, dict):
            value = agent.get("artifact")
    if value is None or value == "":
        return None
    return str(value)


def _system_prompt_ref(data: dict[str, Any]) -> str | None:
    value = data.get("system_prompt")
    if value is None:
        agent = data.get("agent")
        if isinstance(agent, dict):
            value = agent.get("system_prompt")
    if value is None or value == "":
        return None
    return str(value)


def _compile_module_ref(data: dict[str, Any]) -> str | None:
    compile_section = data.get("compile")
    if not isinstance(compile_section, dict):
        return None
    value = compile_section.get("module")
    if value is None or value == "":
        return None
    return str(value)


def _resolve_relative(agent_dir: Path, ref: str) -> Path:
    path = Path(ref)
    if not path.is_absolute():
        path = (agent_dir / path).resolve()
    return path


def load_agent_yaml(harness_dir: Path | str, agent_name: str) -> tuple[Path, dict[str, Any]]:
    """Load ``agents/<agent_name>/agent.yaml``."""
    harness_dir = Path(harness_dir)
    path = _agent_yaml_path(harness_dir, agent_name)
    try:
        return path, _read_yaml_mapping(path)
    except ConfigValidationError as exc:
        raise AgentResolutionError(
            str(exc),
            path=path,
            agent_name=agent_name,
        ) from exc


def resolve_agent_serve(
    harness_dir: Path | str,
    *,
    harness_name: str,
    agent_name: str,
) -> ServeResolution:
    """Resolve serve/run path: ``artifact`` > ``system_prompt`` > error."""
    harness_dir = Path(harness_dir)
    agent_yaml_path, data = load_agent_yaml(harness_dir, agent_name)
    agent_dir = agent_yaml_path.parent

    artifact_ref = _artifact_ref(data)
    if artifact_ref is not None:
        artifact_path = _resolve_relative(agent_dir, artifact_ref)
        manifest_path = artifact_path / ARTIFACT_MANIFEST
        if artifact_path.is_dir() and manifest_path.is_file():
            return ServeResolution(
                harness_name=harness_name,
                agent_name=agent_name,
                source=RuntimeSource.ARTIFACT,
                path=artifact_path,
                agent_yaml_path=agent_yaml_path,
            )
        raise AgentResolutionError(
            _missing_artifact_message(
                harness_name=harness_name,
                agent_name=agent_name,
                artifact_path=artifact_path,
                agent_yaml_path=agent_yaml_path,
            ),
            path=manifest_path if artifact_path.is_dir() else artifact_path,
            harness_name=harness_name,
            agent_name=agent_name,
            suggestion=(
                f"Run `zaumzeug compile {harness_name} --agent {agent_name}` "
                f"or fix `artifact` in {agent_yaml_path}"
            ),
        )

    prompt_ref = _system_prompt_ref(data)
    if prompt_ref is not None:
        prompt_path = _resolve_relative(agent_dir, prompt_ref)
        if prompt_path.is_file():
            return ServeResolution(
                harness_name=harness_name,
                agent_name=agent_name,
                source=RuntimeSource.SYSTEM_PROMPT,
                path=prompt_path,
                agent_yaml_path=agent_yaml_path,
            )
        raise AgentResolutionError(
            _missing_system_prompt_message(
                harness_name=harness_name,
                agent_name=agent_name,
                prompt_path=prompt_path,
                agent_yaml_path=agent_yaml_path,
            ),
            path=prompt_path,
            harness_name=harness_name,
            agent_name=agent_name,
            suggestion=f"Create {prompt_path} or set `agent.artifact` in {agent_yaml_path}",
        )

    raise AgentResolutionError(
        _no_runtime_path_message(
            harness_name=harness_name,
            agent_name=agent_name,
            agent_yaml_path=agent_yaml_path,
        ),
        path=agent_yaml_path,
        harness_name=harness_name,
        agent_name=agent_name,
        suggestion=(
            f"Run `zaumzeug compile {harness_name} --agent {agent_name}` "
            f"or add `agent.system_prompt` in {agent_yaml_path}"
        ),
    )


def resolve_agent_compile(
    harness_dir: Path | str,
    *,
    harness_name: str,
    agent_name: str,
) -> CompileResolution:
    """Resolve compile path: requires ``compile.module`` in ``agent.yaml``."""
    harness_dir = Path(harness_dir)
    agent_yaml_path, data = load_agent_yaml(harness_dir, agent_name)
    compile_module = _compile_module_ref(data)
    if compile_module is None:
        raise AgentResolutionError(
            _missing_compile_module_message(
                harness_name=harness_name,
                agent_name=agent_name,
                agent_yaml_path=agent_yaml_path,
            ),
            path=agent_yaml_path,
            harness_name=harness_name,
            agent_name=agent_name,
            suggestion=(
                f"Add `compile.module` (DSPy Module import path) to {agent_yaml_path}"
            ),
        )
    return CompileResolution(
        harness_name=harness_name,
        agent_name=agent_name,
        compile_module=compile_module,
        agent_yaml_path=agent_yaml_path,
    )


def resolve_serve_entry(
    harness_dir: Path | str,
    *,
    harness_name: str,
) -> ServeResolution:
    """Resolve the workflow ``entry`` agent for interactive ``zaumzeug serve``."""
    harness_dir = Path(harness_dir)
    workflow_path = harness_dir / "workflow.yaml"
    try:
        workflow = load_workflow(harness_dir)
    except ConfigValidationError as exc:
        raise AgentResolutionError(
            str(exc),
            path=workflow_path,
            harness_name=harness_name,
            suggestion=f"Fix `entry` and `stages` in {workflow_path}",
        ) from exc
    return resolve_agent_serve(
        harness_dir,
        harness_name=harness_name,
        agent_name=workflow.entry,
    )


def _missing_artifact_message(
    *,
    harness_name: str,
    agent_name: str,
    artifact_path: Path,
    agent_yaml_path: Path,
) -> str:
    manifest = artifact_path / ARTIFACT_MANIFEST
    return (
        f"Harness '{harness_name}' agent '{agent_name}': artifact at {artifact_path} "
        f"is missing {ARTIFACT_MANIFEST} ({manifest}). "
        f"Run `zaumzeug compile {harness_name} --agent {agent_name}` "
        f"or fix `artifact` in {agent_yaml_path}."
    )


def _missing_system_prompt_message(
    *,
    harness_name: str,
    agent_name: str,
    prompt_path: Path,
    agent_yaml_path: Path,
) -> str:
    return (
        f"Harness '{harness_name}' agent '{agent_name}': system_prompt file "
        f"{prompt_path} not found. Create the file or set `agent.artifact` "
        f"in {agent_yaml_path}."
    )


def _no_runtime_path_message(
    *,
    harness_name: str,
    agent_name: str,
    agent_yaml_path: Path,
) -> str:
    return (
        f"Harness '{harness_name}' agent '{agent_name}' has no runtime path in "
        f"{agent_yaml_path}: set `agent.artifact` with a valid "
        f"{ARTIFACT_MANIFEST} or `agent.system_prompt`."
    )


def _missing_compile_module_message(
    *,
    harness_name: str,
    agent_name: str,
    agent_yaml_path: Path,
) -> str:
    return (
        f"Harness '{harness_name}' agent '{agent_name}' requires `compile.module` "
        f"in {agent_yaml_path} (DSPy Module import path)."
    )
