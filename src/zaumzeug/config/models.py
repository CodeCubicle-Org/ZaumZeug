"""Model registry loading and three-tier deep merge (Architecture §6.1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError

from zaumzeug.config.loader import ConfigValidationError, _read_yaml_mapping

# YAML keys that must never hold secrets — credentials belong in ``.env`` only.
_FORBIDDEN_SECRET_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "secret_key",
        "token",
        "password",
        "access_token",
    }
)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* onto *base*.

  - Nested dicts merge recursively; child keys win.
  - An explicit empty dict in *override* replaces the parent value.
  - Lists in *override* replace parent lists entirely (no append).
  - Scalar values in *override* replace parent scalars.
    """
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict):
            if not val:
                out[key] = {}
            elif isinstance(out.get(key), dict):
                out[key] = deep_merge(out[key], val)
            else:
                out[key] = dict(val)
        else:
            out[key] = val
    return out


def merge_model_registries(*layers: dict[str, Any] | None) -> dict[str, Any]:
    """Deep-merge model registry layers: global → harness → agent."""
    merged: dict[str, Any] = {}
    for layer in layers:
        if layer:
            merged = deep_merge(merged, layer)
    return merged


def _collect_secret_violations(
    data: Any,
    *,
    path: tuple[str, ...] = (),
) -> list[str]:
    violations: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            key_path = (*path, key)
            if key.lower() in _FORBIDDEN_SECRET_KEYS:
                violations.append(".".join(key_path))
            violations.extend(_collect_secret_violations(value, path=key_path))
    elif isinstance(data, list):
        for index, item in enumerate(data):
            violations.extend(
                _collect_secret_violations(item, path=(*path, str(index)))
            )
    return violations


class ModelEntryConfig(BaseModel):
    """Single entry under ``models`` in a registry file."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    api_base_url: str | None = None
    generation_kwargs: dict[str, Any] | None = None


class AgentModelsConfig(BaseModel):
    """Merged per-agent model registry after three-tier merge."""

    model_config = ConfigDict(extra="forbid")

    default_model_id: str
    models: dict[str, ModelEntryConfig] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _reject_secrets(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        violations = _collect_secret_violations(data)
        if violations:
            joined = ", ".join(violations)
            raise ValueError(
                f"Secrets must not appear in YAML (use .env instead): {joined}"
            )
        return data

    @model_validator(mode="after")
    def _default_model_exists(self) -> AgentModelsConfig:
        if self.default_model_id not in self.models:
            raise ValidationError.from_exception_data(
                "AgentModelsConfig",
                [
                    InitErrorDetails(
                        type=PydanticCustomError(
                            "model_id_not_found",
                            "default_model_id '{model_id}' is not defined in models",
                            {"model_id": self.default_model_id},
                        ),
                        loc=("default_model_id",),
                        input=self.default_model_id,
                    )
                ],
            )
        return self


def _load_optional_models(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        return {}
    return _read_yaml_mapping(path)


def load_merged_agent_models(
    *,
    project_root: Path | str,
    harness_dir: Path | str,
    harness_models_path: Path | str | None,
    agent_name: str,
) -> AgentModelsConfig:
    """Load and merge global, harness, and per-agent model registries.

    Merge order (Architecture §6.1):

    1. ``config/models.yaml`` under *project_root* when present.
    2. Harness ``models.yaml`` when *harness_models_path* is set (from
       ``harness.yaml`` ``models:`` reference).
    3. ``agents/<agent_name>/agents-models.yaml`` (required).
    """
    project_root = Path(project_root)
    harness_dir = Path(harness_dir)

    global_path = project_root / "config" / "models.yaml"
    agent_path = harness_dir / "agents" / agent_name / "agents-models.yaml"

    try:
        merged = merge_model_registries(
            _load_optional_models(global_path),
            _load_optional_models(Path(harness_models_path))
            if harness_models_path is not None
            else None,
            _read_yaml_mapping(agent_path),
        )
        return AgentModelsConfig.model_validate(merged)
    except ConfigValidationError:
        raise
    except ValidationError as exc:
        raise ConfigValidationError.from_validation_error(agent_path, exc) from exc
