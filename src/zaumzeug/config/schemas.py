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
    # ``eval`` unblocked by E6-S02 (``zaumzeug eval``); still Phase 2 in the PRD.
    # ``deploy`` unblocked by E6-S03 / E5-S06 (``deploy.eval_gate``); still Phase 2 in the PRD.
    ("parallelism",): 2,
    ("serve", "acp"): 3,
    ("serve", "a2a"): 4,
    ("serve", "expose"): 4,
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
    """Hayhooks bind settings under ``serve.hayhooks`` (Phase 1+)."""

    model_config = ConfigDict(extra="forbid")

    port: int = 1416
    mcp_port: int = 1417

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


class McpServerConfig(BaseModel):
    """One ``tools.mcp`` entry — stdio (``command``) or HTTP (``url``) (E7-S01)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    timeout_s: float = Field(default=30.0, gt=0)
    tool_names: list[str] | None = None
    env: dict[str, str] | None = None

    @field_validator("name")
    @classmethod
    def _name_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("`name` must be a non-empty MCP server name")
        return value.strip()

    @field_validator("command", "url")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _exactly_one_transport(self) -> McpServerConfig:
        has_command = bool(self.command)
        has_url = bool(self.url)
        if has_command == has_url:
            raise ValueError(
                "each tools.mcp entry must have exactly one of `command` (stdio) or `url` (HTTP)"
            )
        return self


class AgentToolsConfig(BaseModel):
    """``tools`` block in ``agent.yaml`` (Architecture §6.5)."""

    model_config = ConfigDict(extra="forbid")

    builtin: list[str] = Field(default_factory=list)
    mcp: list[McpServerConfig] | None = None
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


class AgentOutputConfig(BaseModel):
    """Optional ``output`` block in ``agent.yaml`` (E8-S07 / E8.7).

    ``format: json`` validates stage assistant text as JSON after
    ``zaumzeug run`` (stdlib parse + markdown fence strip). JSON Schema
    (``output.schema``) is deferred.
    """

    model_config = ConfigDict(extra="forbid")

    format: Literal["json"]


class AgentConfig(BaseModel):
    """Root schema for ``agents/<name>/agent.yaml`` (Phase 1+)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    default_model_id: str | None = None
    agent: AgentSectionConfig | None = None
    tools: AgentToolsConfig | None = None
    compile: CompileConfig | None = None
    output: AgentOutputConfig | None = None

    @field_validator("name")
    @classmethod
    def _name_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("`name` must be a non-empty agent name")
        return value


class EvalMetricConfig(BaseModel):
    """One DeepEval metric entry under ``eval.metrics`` (Architecture §6.3)."""

    model_config = ConfigDict(extra="forbid")

    type: str
    threshold: float = 0.5

    @field_validator("type")
    @classmethod
    def _type_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("`type` must be a non-empty DeepEval metric class name")
        return value.strip()


class EvalConfidentAiConfig(BaseModel):
    """Optional Confident AI sync settings under ``eval.confident_ai``."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    sync_test_results: bool = True


class EvalConfig(BaseModel):
    """Optional ``eval`` section of ``harness.yaml`` (Architecture §6.3 / E6-S02).

    When ``framework`` is omitted, the runner defaults to ``deepeval``.

    Optional ``base_url`` enables Mode C (HTTP black-box against a running
    ``zaumzeug serve``) — staging/debug only (E6-S06). Empty string uses
    ``http://127.0.0.1:<serve.hayhooks.port>``.
    """

    model_config = ConfigDict(extra="forbid")

    framework: Literal["deepeval", "builtin"] | None = None
    valset: str
    metrics: list[EvalMetricConfig] = Field(default_factory=list)
    judge_model_id: str | None = None
    confident_ai: EvalConfidentAiConfig | None = None
    base_url: str | None = None

    @field_validator("valset")
    @classmethod
    def _valset_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("`valset` must be a non-empty path to a JSONL file")
        return value.strip()

    @field_validator("base_url")
    @classmethod
    def _base_url_strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


EvalGateMode = Literal["skip", "warn", "block"]


class DeployConfig(BaseModel):
    """Optional ``deploy`` section of ``harness.yaml`` (Architecture §6.4 / E5-S06).

    Controls whether ``zaumzeug deploy`` runs eval first. Default gate is ``skip``.
    """

    model_config = ConfigDict(extra="forbid")

    eval_gate: EvalGateMode = "skip"


class RuntimeRetryConfig(BaseModel):
    """Harness-level retry policy for ``zaumzeug run`` stages (E8-S07 / E8.7).

    Applied per stage after a successful agent build: retries ``Agent.run`` and
    optional JSON output validation. Default ``max_attempts: 1`` preserves
    one-shot behavior. Schema rejects ``max_attempts < 1``.
    """

    model_config = ConfigDict(extra="forbid")

    max_attempts: int = Field(default=1, ge=1)
    initial_delay_s: float = Field(default=1.0, ge=0.0)
    backoff: float = Field(default=2.0, ge=0.0)


class HarnessRuntimeConfig(BaseModel):
    """Optional ``runtime`` section of ``harness.yaml`` (E8-S07 / E8.7).

    Currently used by ``run_workflow`` / ``zaumzeug run`` only — serve/HTTP
    does not yet share this reliability layer.
    """

    model_config = ConfigDict(extra="forbid")

    retry: RuntimeRetryConfig = Field(default_factory=RuntimeRetryConfig)


class HarnessConfig(BaseModel):
    """Root schema for ``harness.yaml`` (Architecture §6.6 Phase 1+)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    models: str | None = None
    serve: ServeConfig | None = None
    eval: EvalConfig | None = None
    deploy: DeployConfig | None = None
    runtime: HarnessRuntimeConfig | None = None

    @model_validator(mode="before")
    @classmethod
    def _phase_gate(cls, data: Any) -> Any:
        return _reject_phase_gated_keys(
            data,
            path_prefix=(),
            model_name=cls.__name__,
        )
