"""Pydantic config schemas for harness YAML (Phase 1+).

Phase-gated keys raise field-level errors with a phase hint so authors can
fix without reading SDK source (PRD E2.1 / Architecture §6.2, §6.6).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError

from zaumzeug.config.constants import CURRENT_SDK_PHASE

# Absolute key paths from ``harness.yaml`` root → minimum delivery phase.
# Nested models look up with their section prefix; error ``loc`` stays relative
# so pydantic nests parent field names correctly.
PHASE_GATED_FIELDS: dict[tuple[str, ...], int] = {
    ("compile",): 2,
    ("eval",): 2,
    ("deploy",): 2,
    ("parallelism",): 2,
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


class WorkflowStage(BaseModel):
    """One serial stage in ``workflow.yaml`` — exactly ``agent`` or ``pipeline``."""

    model_config = ConfigDict(extra="forbid")

    agent: str | None = None
    pipeline: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _phase_gate(cls, data: Any) -> Any:
        return _reject_phase_gated_keys(
            data,
            path_prefix=(),
            model_name=cls.__name__,
        )

    @model_validator(mode="after")
    def _exactly_one_ref(self) -> WorkflowStage:
        has_agent = bool(self.agent and self.agent.strip())
        has_pipeline = bool(self.pipeline and self.pipeline.strip())
        if has_agent == has_pipeline:
            raise ValueError(
                "each stage must have exactly one of `agent` or `pipeline`"
            )
        return self


class WorkflowConfig(BaseModel):
    """Root schema for ``workflow.yaml`` (Architecture §6.6 Phase 1)."""

    model_config = ConfigDict(extra="forbid")

    entry: str
    stages: list[WorkflowStage] = Field(min_length=1)

    @field_validator("entry")
    @classmethod
    def _entry_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("`entry` must be a non-empty agent name")
        return value


class AgentSectionConfig(BaseModel):
    """Nested ``agent`` block in ``agent.yaml`` (Phase 1+)."""

    model_config = ConfigDict(extra="forbid")

    system_prompt: str | None = None
    artifact: str | None = None


class AgentToolsConfig(BaseModel):
    """``tools`` block in ``agent.yaml`` (Architecture §6.5)."""

    model_config = ConfigDict(extra="forbid")

    builtin: list[str] = Field(default_factory=list)
    mcp: list[dict[str, Any]] | None = None
    custom: list[str] | None = None

    @field_validator("builtin")
    @classmethod
    def _validate_builtin_ids(cls, value: list[str]) -> list[str]:
        from zaumzeug.config.builtins import validate_builtin_tool_ids

        validate_builtin_tool_ids(value)
        return value

    @model_validator(mode="after")
    def _phase_gate_tool_sections(self) -> AgentToolsConfig:
        if CURRENT_SDK_PHASE < 3:
            if self.mcp:
                raise ValueError("`mcp` is Phase 3")
            if self.custom:
                raise ValueError("`custom` is Phase 3")
        return self


class CompileConfig(BaseModel):
    """Phase 2 ``compile`` section in ``agents/<name>/agent.yaml`` (Architecture §6.2).

    **Pattern A (default):** ``optimizer: dspy.GEPA`` requires ``module``.
    **Pattern B (E4-S04):** ``optimizer: optimize_anything`` requires ``mode`` +
    ``seed_artifact`` (no DSPy module path).

    GEPA budget uses exactly one of ``auto`` / ``max_metric_calls`` / ``max_full_evals``.
    Ideation ``budget:`` is accepted as an alias for ``auto``.
    """

    model_config = ConfigDict(extra="forbid")

    module: str | None = None
    enabled: bool = True
    optimizer: str = "dspy.GEPA"
    mode: Literal["single-task", "multi-task", "generalization"] | None = None
    seed_artifact: str | None = None
    trainset: str | None = None
    valset: str | None = None
    task_model_id: str | None = None
    reflection_model_id: str | None = None
    auto: Literal["light", "medium", "heavy"] | None = None
    max_metric_calls: int | None = None
    max_full_evals: int | None = None
    budget: Literal["light", "medium", "heavy"] | None = None

    @field_validator("module")
    @classmethod
    def _module_non_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("`compile.module` must be a non-empty DSPy Module import path")
        return value.strip()

    @field_validator("seed_artifact")
    @classmethod
    def _seed_artifact_non_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError(
                "`compile.seed_artifact` must be a non-empty path "
                "(prompt / pipeline YAML relative to the agent folder)"
            )
        return value.strip()

    @model_validator(mode="after")
    def _normalize_budget_and_pattern(self) -> CompileConfig:
        auto = self.auto
        if auto is None and self.budget is not None:
            auto = self.budget

        budget_flags = (
            (auto is not None)
            + (self.max_metric_calls is not None)
            + (self.max_full_evals is not None)
        )
        if budget_flags > 1:
            raise ValueError(
                "compile budget: set exactly one of `auto` (or `budget`), "
                "`max_metric_calls`, or `max_full_evals`"
            )

        updates: dict[str, Any] = {}
        if auto is not None and self.auto != auto:
            updates["auto"] = auto

        pattern_b = self.optimizer.strip() in {
            "optimize_anything",
            "gepa.optimize_anything",
        }
        if pattern_b:
            if self.mode is None:
                raise ValueError(
                    "compile.mode is required for optimize_anything "
                    "(single-task | multi-task | generalization)"
                )
            if self.seed_artifact is None:
                raise ValueError(
                    "compile.seed_artifact is required for optimize_anything "
                    "(path to seed prompt / pipeline YAML under the agent folder)"
                )
            if self.mode == "multi-task" and not self.trainset:
                raise ValueError(
                    "compile.trainset is required when compile.mode is multi-task"
                )
            if self.mode == "generalization" and (
                not self.trainset or not self.valset
            ):
                raise ValueError(
                    "compile.trainset and compile.valset are required when "
                    "compile.mode is generalization"
                )
            if self.mode == "single-task" and self.valset:
                raise ValueError(
                    "compile.valset must be omitted when compile.mode is single-task"
                )
            if self.mode == "multi-task" and self.valset:
                raise ValueError(
                    "compile.valset must be omitted when compile.mode is multi-task "
                    "(use generalization for train/val)"
                )
        else:
            if self.module is None:
                raise ValueError(
                    "`compile.module` is required for Pattern A (dspy.GEPA); "
                    "or set optimizer: optimize_anything with mode + seed_artifact"
                )
            if self.mode is not None:
                raise ValueError(
                    "compile.mode is only valid with optimizer: optimize_anything "
                    "(Pattern B)"
                )
            if self.seed_artifact is not None:
                raise ValueError(
                    "compile.seed_artifact is only valid with optimizer: "
                    "optimize_anything (Pattern B)"
                )

        if updates:
            return self.model_copy(update=updates)
        return self


class AgentConfig(BaseModel):
    """Root schema for ``agents/<name>/agent.yaml`` (Phase 1+)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    default_model_id: str | None = None
    agent: AgentSectionConfig | None = None
    tools: AgentToolsConfig | None = None
    compile: CompileConfig | None = None

    @field_validator("name")
    @classmethod
    def _name_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("`name` must be a non-empty agent name")
        return value


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
