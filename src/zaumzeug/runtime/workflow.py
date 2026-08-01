"""Serial workflow executor for ``zaumzeug run`` (E3-S08 / E3.6, E8-S07 / E8.7)."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from haystack.dataclasses import ChatMessage

from zaumzeug.config import (
    AgentResolutionError,
    ConfigValidationError,
    load_agent_config,
    load_harness,
    load_merged_agent_models,
    load_workflow,
)
from zaumzeug.config.harness_root import resolve_harness_path
from zaumzeug.config.schemas import (
    RuntimeRetryConfig,
    WorkflowConfig,
    WorkflowStage,
)
from zaumzeug.doctor.project import find_project_root
from zaumzeug.logging import get_logger, log_request
from zaumzeug.runtime.factory import RuntimeFactoryError, build_agent_bundle
from zaumzeug.runtime.model_router import ModelRouter, ModelRouterError
from zaumzeug.runtime.preprocess import preprocess_openai_messages

_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$",
    re.DOTALL | re.IGNORECASE,
)

_logger = get_logger("runtime.workflow")


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


def strip_markdown_json_fence(text: str) -> str:
    """Strip a single optional markdown code fence wrapping JSON text."""
    match = _FENCE_RE.match(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def validate_json_stage_output(text: str) -> None:
    """Validate stage assistant text as JSON (stdlib parse after fence strip).

    Empty text fails. Raises :class:`ValueError` on invalid output (retryable).
    """
    if not text or not text.strip():
        raise ValueError("empty assistant text is not valid JSON")
    candidate = strip_markdown_json_fence(text)
    if not candidate:
        raise ValueError("empty assistant text is not valid JSON")
    try:
        json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"stage output is not valid JSON: {exc}") from exc


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


def _retry_config(harness_config: Any) -> RuntimeRetryConfig:
    runtime = getattr(harness_config, "runtime", None)
    if runtime is None:
        return RuntimeRetryConfig()
    return runtime.retry


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

    Reliability (E8-S07): live ``Agent.run`` / JSON-output failures are typed
    ``WorkflowError``s, optionally retried per ``runtime.retry``, with INFO
    stage lifecycle logs via ``log_request(..., stage=...)``. Build and message
    prep run once per stage (not retried).
    """
    root = Path(project_root) if project_root is not None else find_project_root()
    harness_path = resolve_harness_path(root, harness_name, deploy_flag=deploy)

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
    retry = _retry_config(harness_config)

    result = WorkflowRunResult(harness_name=harness_name)
    prior_output: str | None = None

    for stage in stages:
        sid = stage_id(stage)
        if stage.pipeline:
            _run_pipeline_stage_stub(harness_name=harness_name, pipeline_id=sid)

        agent_name = stage.agent
        assert agent_name is not None
        agent_name = agent_name.strip()
        model_id: str | None = None

        # --- build + message prep once (not retryable) ---
        try:
            agent_config = load_agent_config(
                harness_path / "agents" / agent_name / "agent.yaml"
            )
            merged = load_merged_agent_models(
                project_root=root,
                harness_dir=harness_path,
                harness_models_path=harness_models,
                agent_name=agent_name,
            )
            model_id = merged.default_model_id
            router = ModelRouter(merged, project_root=root)
            built = build_agent_bundle(
                harness_path,
                harness_name=harness_name,
                agent_name=agent_name,
                router=router,
            )
            openai_messages = preprocess_openai_messages(
                built.input_rewrite_template,
                build_stage_messages(
                    user_input,
                    prior_output=prior_output,
                ),
            )
            chat_messages = [
                ChatMessage.from_openai_dict_format(message)
                for message in openai_messages
            ]
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
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError(
                f"Harness '{harness_name}' agent '{agent_name}': {exc}",
                harness_name=harness_name,
                agent_name=agent_name,
                stage=sid,
            ) from exc

        require_json = (
            agent_config.output is not None and agent_config.output.format == "json"
        )
        log_request(
            _logger,
            "workflow stage start",
            harness=harness_name,
            agent=agent_name,
            model_id=model_id,
            stage=sid,
            level=logging.INFO,
        )

        # --- attempt loop: agent.run + optional JSON check ---
        output = ""
        last_error: BaseException | None = None
        for attempt in range(1, retry.max_attempts + 1):
            try:
                run_result = built.agent.run(messages=chat_messages)
                output = _assistant_text(run_result)
                if require_json:
                    validate_json_stage_output(output)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < retry.max_attempts:
                    delay = retry.initial_delay_s * (retry.backoff ** (attempt - 1))
                    log_request(
                        _logger,
                        (
                            f"workflow stage retry "
                            f"(attempt {attempt}/{retry.max_attempts}): {exc}"
                        ),
                        harness=harness_name,
                        agent=agent_name,
                        model_id=model_id,
                        stage=sid,
                        level=logging.INFO,
                    )
                    if delay > 0:
                        time.sleep(delay)
                    continue
                break

        if last_error is not None:
            log_request(
                _logger,
                (
                    f"workflow stage failure "
                    f"after {retry.max_attempts} attempt(s): {last_error}"
                ),
                harness=harness_name,
                agent=agent_name,
                model_id=model_id,
                stage=sid,
                level=logging.INFO,
            )
            raise WorkflowError(
                (
                    f"Harness '{harness_name}' agent '{agent_name}' stage "
                    f"{sid!r}: live generation failed after "
                    f"{retry.max_attempts} attempt(s): {last_error}"
                ),
                harness_name=harness_name,
                agent_name=agent_name,
                stage=sid,
            ) from last_error

        log_request(
            _logger,
            "workflow stage success",
            harness=harness_name,
            agent=agent_name,
            model_id=model_id,
            stage=sid,
            level=logging.INFO,
        )

        result.stages.append(
            StageResult(
                stage_id=sid,
                kind="agent",
                output=output,
                model_id=model_id,
            )
        )
        prior_output = output

    if result.stages:
        result.final_output = result.stages[-1].output
    return result
