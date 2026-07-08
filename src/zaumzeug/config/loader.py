"""YAML config loaders with pathlib path resolution and clear errors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from zaumzeug.config.schemas import CURRENT_SDK_PHASE, HarnessConfig, PHASE_GATED_FIELDS


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
