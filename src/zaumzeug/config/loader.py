"""YAML config loaders with pathlib path resolution and clear errors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from zaumzeug.config.schemas import (
    CURRENT_SDK_PHASE,
    AgentConfig,
    HarnessConfig,
    PHASE_GATED_FIELDS,
    WorkflowConfig,
)


class ConfigValidationError(ValueError):
    """Config failed to load or validate; includes file path and field names."""

    def __init__(
        self,
        path: Path,
        message: str,
        *,
        field: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.path = Path(path)
        self.field = field
        self.errors = errors or []
        super().__init__(message)

    @classmethod
    def from_validation_error(
        cls,
        path: Path,
        exc: ValidationError,
    ) -> ConfigValidationError:
        path = Path(path)
        lines: list[str] = [f"Invalid config in {path}:"]
        first_field: str | None = None
        formatted_errors: list[dict[str, Any]] = []

        for err in exc.errors():
            loc = err.get("loc", ())
            field = ".".join(str(part) for part in loc) if loc else "<root>"
            if first_field is None:
                first_field = field
            msg = err.get("msg", "validation failed")
            lines.append(f"  {field}: {msg}")
            formatted_errors.append(
                {
                    "field": field,
                    "msg": msg,
                    "type": err.get("type"),
                    "loc": loc,
                }
            )

        return cls(
            path,
            "\n".join(lines),
            field=first_field,
            errors=formatted_errors,
        )


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigValidationError(
            path,
            f"Cannot read config file {path}: {exc}",
        ) from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigValidationError(
            path,
            f"Invalid YAML in {path}: {exc}",
        ) from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigValidationError(
            path,
            f"Invalid config in {path}:\n  <root>: expected a mapping, got {type(data).__name__}",
            field="<root>",
        )
    return data


def strip_eval_for_doctor_validation(data: dict[str, Any]) -> dict[str, Any]:
    """Remove ``eval`` for Phase 1 doctor validation when it only warrants a warn."""
    stripped = dict(data)
    if PHASE_GATED_FIELDS.get(("eval",), 0) > CURRENT_SDK_PHASE:
        stripped.pop("eval", None)
    return stripped


def strip_phase_gated_agent_tools(data: dict[str, Any]) -> dict[str, Any]:
    """Identity helper — ``tools.mcp`` (E7-S01) and ``tools.custom`` (E7-S02) are allowed.

    Kept so workflow cross-validation has a stable hook if a later tool section
    is phase-gated again.
    """
    return dict(data)


def load_harness_for_doctor(path: Path | str) -> HarnessConfig:
    """Load ``harness.yaml`` for doctor, tolerating warned phase-gated keys."""
    path = Path(path)
    data = strip_eval_for_doctor_validation(_read_yaml_mapping(path))

    try:
        config = HarnessConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigValidationError.from_validation_error(path, exc) from exc

    if config.models is not None:
        models_path = Path(config.models)
        if not models_path.is_absolute():
            resolved = (path.parent / models_path).resolve()
            config = config.model_copy(update={"models": str(resolved)})

    return config


def _agent_yaml_path(harness_dir: Path, agent_name: str) -> Path:
    return harness_dir / "agents" / agent_name / "agent.yaml"


def _validate_harness_agent_names(harness_dir: Path) -> list[str]:
    """Return agent-name consistency errors (AC-4)."""
    agents_dir = harness_dir / "agents"
    if not agents_dir.is_dir():
        return []

    errors: list[str] = []
    seen_yaml_names: dict[str, str] = {}

    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        agent_yaml = agent_dir / "agent.yaml"
        if not agent_yaml.is_file():
            continue

        folder_name = agent_dir.name
        try:
            data = _read_yaml_mapping(agent_yaml)
        except ConfigValidationError as exc:
            errors.append(f"agents/{folder_name}/agent.yaml: {exc}")
            continue

        yaml_name = data.get("name")
        if not isinstance(yaml_name, str) or not yaml_name.strip():
            errors.append(
                f"agents/{folder_name}/agent.yaml: missing required `name` field"
            )
            continue

        try:
            AgentConfig.model_validate(strip_phase_gated_agent_tools(data))
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(part) for part in err.get("loc", ()))
                field = loc or "<root>"
                errors.append(
                    f"agents/{folder_name}/agent.yaml: {field}: {err.get('msg', 'validation failed')}"
                )
            continue

        if yaml_name != folder_name:
            errors.append(
                f"agents/{folder_name}/agent.yaml: `name` is '{yaml_name}' "
                f"but folder is '{folder_name}'"
            )

        if yaml_name in seen_yaml_names:
            prior = seen_yaml_names[yaml_name]
            errors.append(
                f"duplicate agent name '{yaml_name}' in agents/{prior} "
                f"and agents/{folder_name}"
            )
        else:
            seen_yaml_names[yaml_name] = folder_name

    return errors


def _validate_workflow_agent_refs(
    harness_dir: Path,
    workflow: WorkflowConfig,
) -> list[str]:
    """Return unknown agent reference errors (AC-3)."""
    errors: list[str] = []
    refs: list[str] = [workflow.entry]
    for stage in workflow.stages:
        if stage.agent:
            refs.append(stage.agent)

    for agent_name in dict.fromkeys(refs):
        agent_yaml = _agent_yaml_path(harness_dir, agent_name)
        if not agent_yaml.is_file():
            errors.append(
                f"unknown agent ref '{agent_name}': expected {agent_yaml}"
            )
    return errors


def load_workflow(harness_dir: Path | str) -> WorkflowConfig:
    """Load and validate ``workflow.yaml`` with agent cross-checks (PRD E2.7)."""
    harness_dir = Path(harness_dir)
    path = harness_dir / "workflow.yaml"
    data = _read_yaml_mapping(path)

    try:
        workflow = WorkflowConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigValidationError.from_validation_error(path, exc) from exc

    cross_errors = (
        _validate_harness_agent_names(harness_dir)
        + _validate_workflow_agent_refs(harness_dir, workflow)
    )
    if cross_errors:
        lines = [f"Invalid config in {path}:"]
        for message in cross_errors:
            lines.append(f"  {message}")
        raise ConfigValidationError(
            path,
            "\n".join(lines),
            field=cross_errors[0].split(":", 1)[0],
        )

    return workflow


def load_workflow_yaml(harness_dir: Path | str) -> dict[str, Any]:
    """Load validated ``workflow.yaml`` as a plain mapping."""
    workflow = load_workflow(harness_dir)
    return workflow.model_dump(exclude_none=True)


def load_agent_config(path: Path | str) -> AgentConfig:
    """Load and validate ``agents/<name>/agent.yaml``."""
    path = Path(path)
    data = _read_yaml_mapping(path)

    try:
        return AgentConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigValidationError.from_validation_error(path, exc) from exc


def load_harness(path: Path | str) -> HarnessConfig:
    """Load and validate ``harness.yaml`` into :class:`HarnessConfig`.

    Relative ``models`` paths are resolved against the config file's parent
    directory (stored as absolute strings when present).
    """
    path = Path(path)
    data = _read_yaml_mapping(path)

    try:
        config = HarnessConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigValidationError.from_validation_error(path, exc) from exc

    if config.models is not None:
        models_path = Path(config.models)
        if not models_path.is_absolute():
            resolved = (path.parent / models_path).resolve()
            config = config.model_copy(update={"models": str(resolved)})

    return config
