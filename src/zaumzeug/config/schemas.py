"""Pydantic config schemas for harness YAML (Phase 1+).

Phase-gated keys raise field-level errors with a phase hint so authors can
fix without reading SDK source (PRD E2.1 / Architecture §6.2, §6.6).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError

# SDK delivery phase used for allowlists (Architecture §6.2).
CURRENT_SDK_PHASE = 1

# Absolute key paths from ``harness.yaml`` root → minimum delivery phase.
# Nested models look up with their section prefix; error ``loc`` stays relative
# so pydantic nests parent field names correctly.
PHASE_GATED_FIELDS: dict[tuple[str, ...], int] = {
    ("compile",): 2,
    ("eval",): 2,
    ("deploy",): 2,
    ("serve", "acp"): 3,
    ("serve", "a2a"): 4,
    ("serve", "expose"): 4,
    ("serve", "hayhooks", "mcp_port"): 3,
    ("serve", "hayhooks", "chainlit"): 3,
}


def _reject_phase_gated_keys(
    data: Any,
    *,
    path_prefix: tuple[str, ...],
    model_name: str,
) -> Any:
    """Reject immediate keys that are not available in ``CURRENT_SDK_PHASE``."""
    if not isinstance(data, dict):
        return data

    errors: list[InitErrorDetails] = []
    for key, value in data.items():
        full_path = (*path_prefix, key)
        min_phase = PHASE_GATED_FIELDS.get(full_path)
        if min_phase is not None and min_phase > CURRENT_SDK_PHASE:
            errors.append(
                {
                    "type": PydanticCustomError(
                        "phase_gated_field",
                        "`{field}` is Phase {phase}",
                        {"field": key, "phase": min_phase},
                    ),
                    "loc": (key,),
                    "input": value,
                }
            )

    if errors:
        raise ValidationError.from_exception_data(model_name, errors)
    return data


class HayhooksConfig(BaseModel):
    """Hayhooks bind settings under ``serve.hayhooks`` (Phase 1)."""

    model_config = ConfigDict(extra="forbid")

    port: int = 1416

    @model_validator(mode="before")
    @classmethod
    def _phase_gate(cls, data: Any) -> Any:
        return _reject_phase_gated_keys(
            data,
            path_prefix=("serve", "hayhooks"),
            model_name=cls.__name__,
        )


class ServeConfig(BaseModel):
    """Serve section of ``harness.yaml`` (Phase 1+)."""

    model_config = ConfigDict(extra="forbid")

    hayhooks: HayhooksConfig | None = None

    @model_validator(mode="before")
    @classmethod
    def _phase_gate(cls, data: Any) -> Any:
        return _reject_phase_gated_keys(
            data,
            path_prefix=("serve",),
            model_name=cls.__name__,
        )


class HarnessConfig(BaseModel):
    """Root schema for ``harness.yaml`` (Architecture §6.6 Phase 1)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    models: str | None = None
    serve: ServeConfig | None = None

    @model_validator(mode="before")
    @classmethod
    def _phase_gate(cls, data: Any) -> Any:
        return _reject_phase_gated_keys(
            data,
            path_prefix=(),
            model_name=cls.__name__,
        )
