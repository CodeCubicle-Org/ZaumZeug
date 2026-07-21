"""Serial workflow executor for ``zaumzeug run`` (E3-S08 / E3.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from haystack.dataclasses import ChatMessage

from zaumzeug.config import (
    AgentResolutionError,
    ConfigValidationError,
    load_harness,
    load_merged_agent_models,
    load_workflow,
)
from zaumzeug.config.harness_root import harness_dir as resolve_harness_dir
from zaumzeug.config.harness_root import is_deploy_mode
from zaumzeug.config.schemas import WorkflowConfig, WorkflowStage
from zaumzeug.doctor.project import find_project_root
from zaumzeug.runtime.factory import RuntimeFactoryError, build_agent
from zaumzeug.runtime.model_router import ModelRouter, ModelRouterError


class WorkflowError(RuntimeError):
    """Raised when serial workflow execution fails with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        harness_name: str | None = None,
        agent_name: str | None = None,
        stage: str | None = None,
    ) -> None:
        self.harness_name = harness_name
        self.agent_name = agent_name
        self.stage = stage
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class StageResult:
    """Outcome of one executed workflow stage."""

    stage_id: str
    kind: str  # "agent" | "pipeline"
    output: str
    model_id: str | None = None


@dataclass(slots=True)
class WorkflowRunResult:
    """Full serial workflow run outcome."""

    harness_name: str
    stages: list[StageResult] = field(default_factory=list)
    final_output: str = ""


def stage_id(stage: WorkflowStage) -> str:
    """Return the agent or pipeline id for a workflow stage."""
    if stage.agent and stage.agent.strip():
        return stage.agent.strip()
    assert stage.pipeline is not None
    return stage.pipeline.strip()


def build_stage_messages(
    user_input: str,
    *,
    prior_output: str | None = None,
) -> list[dict[str, str]]:
    """Build OpenAI-shaped messages for one workflow stage (AC-3).

    Prior stage assistant text is prepended as a user message before the
    workflow input so the next agent receives both as context.
    """
    messages: list[dict[str, str]] = [{"role": "user", "content": user_input}]
    if prior_output:
        messages.insert(0, {"role": "user", "content": prior_output})
    return messages


def _assistant_text(result: dict[str, Any]) -> str:
    last = result.get("last_message")
    text = getattr(last, "text", None) if last is not None else None
    if text:
        return str(text)
    messages = result.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            role = getattr(message, "role", None)
            role_value = getattr(role, "value", role)
            if str(role_value) == "assistant":
                text = getattr(message, "text", None)
                if text:
                    return str(text)
    return ""


def _select_stages(
    workflow: WorkflowConfig,
    *,
    from_stage: str | None,
    harness_name: str,
) -> list[WorkflowStage]:
    stages = list(workflow.stages)
    if from_stage is None or not from_stage.strip():
        return stages
    needle = from_stage.strip()
    for index, stage in enumerate(stages):
        if stage_id(stage) == needle:
            return stages[index:]
    known = ", ".join(stage_id(s) for s in stages)
    raise WorkflowError(
        f"Harness '{harness_name}': workflow stage {needle!r} not found "
        f"(known stages: {known})",
        harness_name=harness_name,
        stage=needle,
    )


def _resolve_harness_models_path(
    harness_dir: Path,
    models_ref: str | None,
) -> Path | None:
    if models_ref is None or not str(models_ref).strip():
        return None
    path = Path(models_ref)
    if not path.is_absolute():
        path = harness_dir / path
    return path


def _run_pipeline_stage_stub(
    *,
    harness_name: str,
    pipeline_id: str,
) -> None:
    """Phase 1 stub for pipeline stages (AC-4 — full invoke is Phase 4 / E8-S01)."""
    raise WorkflowError(
        f"Harness '{harness_name}': pipeline stage {pipeline_id!r} is not "
        "executable in Phase 1 (pipeline exposure ships in Phase 4). "
        "Use agent stages only, or remove this stage from workflow.yaml.",
        harness_name=harness_name,
        stage=pipeline_id,
    )


def run_workflow(
    harness_name: str,
    *,
    user_input: str = "",
    from_stage: str | None = None,
    project_root: Path | str | None = None,
    deploy: bool = False,
) -> WorkflowRunResult:
    """Execute ``workflow.yaml`` stages serially with stage-scoped ModelRouters.

    Each agent stage loads ``agents/<name>/`` config and that agent's merged
    ``agents-models.yaml``, builds a Haystack Agent via the runtime factory,
    and forwards prior stage output as context to the next stage.
    """
    root = Path(project_root) if project_root is not None else find_project_root()
    deploy_mode = is_deploy_mode(deploy_flag=deploy)
    harness_path = resolve_harness_dir(root, harness_name, deploy=deploy_mode)

    harness_yaml = harness_path / "harness.yaml"
    if not harness_yaml.is_file():
        raise WorkflowError(
            f"Harness '{harness_name}' not found at {harness_path}",
            harness_name=harness_name,
        )

    try:
        harness_config = load_harness(harness_yaml)
        workflow = load_workflow(harness_path)
    except ConfigValidationError as exc:
        raise WorkflowError(str(exc), harness_name=harness_name) from exc

    stages = _select_stages(
        workflow,
        from_stage=from_stage,
        harness_name=harness_name,
    )
    harness_models = _resolve_harness_models_path(harness_path, harness_config.models)

    result = WorkflowRunResult(harness_name=harness_name)
    prior_output: str | None = None

    for stage in stages:
        sid = stage_id(stage)
        if stage.pipeline:
            _run_pipeline_stage_stub(harness_name=harness_name, pipeline_id=sid)

        agent_name = stage.agent
        assert agent_name is not None
        agent_name = agent_name.strip()

        try:
            merged = load_merged_agent_models(
                project_root=root,
                harness_dir=harness_path,
                harness_models_path=harness_models,
                agent_name=agent_name,
            )
            router = ModelRouter(merged, project_root=root)
            agent = build_agent(
                harness_path,
                harness_name=harness_name,
                agent_name=agent_name,
                router=router,
            )
            openai_messages = build_stage_messages(
                user_input,
                prior_output=prior_output,
            )
            chat_messages = [
                ChatMessage.from_openai_dict_format(message)
                for message in openai_messages
            ]
            run_result = agent.run(messages=chat_messages)
            output = _assistant_text(run_result)
        except AgentResolutionError as exc:
            raise WorkflowError(
                str(exc),
                harness_name=exc.harness_name or harness_name,
                agent_name=exc.agent_name or agent_name,
                stage=sid,
            ) from exc
        except (RuntimeFactoryError, ModelRouterError, ConfigValidationError) as exc:
            raise WorkflowError(
                f"Harness '{harness_name}' agent '{agent_name}': {exc}",
                harness_name=harness_name,
                agent_name=agent_name,
                stage=sid,
            ) from exc

        result.stages.append(
            StageResult(
                stage_id=sid,
                kind="agent",
                output=output,
                model_id=merged.default_model_id,
            )
        )
        prior_output = output

    if result.stages:
        result.final_output = result.stages[-1].output
    return result
