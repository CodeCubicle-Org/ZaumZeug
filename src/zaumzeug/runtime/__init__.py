"""Agent factory, ModelRouter, tool registry, and workflow runner."""

from zaumzeug.runtime.factory import (
    BuiltAgent,
    RuntimeFactoryError,
    build_agent,
    build_agent_bundle,
    build_agent_tools,
    load_input_rewrite,
    load_system_prompt,
)
from zaumzeug.runtime.model_router import ModelRouter, ModelRouterError, PROVIDERS
from zaumzeug.runtime.preprocess import (
    PreprocessError,
    apply_input_rewrite,
    load_input_rewrite_template,
    preprocess_openai_messages,
    preprocess_user_text,
)
from zaumzeug.runtime.workflow import (
    StageResult,
    WorkflowError,
    WorkflowRunResult,
    build_stage_messages,
    run_workflow,
    stage_id,
)

__all__ = [
    "BuiltAgent",
    "ModelRouter",
    "ModelRouterError",
    "PROVIDERS",
    "PreprocessError",
    "RuntimeFactoryError",
    "StageResult",
    "WorkflowError",
    "WorkflowRunResult",
    "apply_input_rewrite",
    "build_agent",
    "build_agent_bundle",
    "build_agent_tools",
    "build_stage_messages",
    "load_input_rewrite",
    "load_input_rewrite_template",
    "load_system_prompt",
    "preprocess_openai_messages",
    "preprocess_user_text",
    "run_workflow",
    "stage_id",
]
