"""Shared Mermaid label helpers for workflow diagram and paths (E4-S08 / E4-S09)."""

from __future__ import annotations

from pathlib import Path

from zaumzeug.config import ConfigValidationError, load_merged_agent_models
from zaumzeug.config.resolver import AgentResolutionError, load_agent_yaml
from zaumzeug.config.schemas import WorkflowStage

__all__ = [
    "escape_mermaid_label",
    "resolve_agent_model_label",
    "resolve_harness_models_path",
    "stage_label",
]


def stage_label(
    stage: WorkflowStage,
    *,
    harness_dir: Path,
    project_root: Path,
    harness_models_path: Path | None,
) -> str:
    if stage.pipeline:
        return stage.pipeline.strip()

    agent_name = (stage.agent or "").strip()
    model_id, provider = resolve_agent_model_label(
        agent_name,
        harness_dir=harness_dir,
        project_root=project_root,
        harness_models_path=harness_models_path,
    )
    if model_id and provider:
        return f"{agent_name}\n{model_id} ({provider})"
    if model_id:
        return f"{agent_name}\n{model_id}"
    return agent_name


def resolve_agent_model_label(
    agent_name: str,
    *,
    harness_dir: Path,
    project_root: Path,
    harness_models_path: Path | None,
) -> tuple[str | None, str | None]:
    """Return ``(default_model_id, provider)`` for an agent when resolvable."""
    agent_default: str | None = None
    try:
        _path, data = load_agent_yaml(harness_dir, agent_name)
    except AgentResolutionError:
        data = {}
    raw = data.get("default_model_id")
    if isinstance(raw, str) and raw.strip():
        agent_default = raw.strip()

    try:
        registry = load_merged_agent_models(
            project_root=project_root,
            harness_dir=harness_dir,
            harness_models_path=harness_models_path,
            agent_name=agent_name,
        )
    except ConfigValidationError:
        return agent_default, None

    model_id = agent_default or registry.default_model_id
    entry = registry.models.get(model_id)
    provider = entry.provider if entry is not None else None
    return model_id, provider


def resolve_harness_models_path(
    harness_dir: Path,
    models_ref: str | None,
) -> Path | None:
    if models_ref is None or not str(models_ref).strip():
        return None
    path = Path(models_ref)
    if not path.is_absolute():
        path = harness_dir / path
    return path


def escape_mermaid_label(label: str) -> str:
    """Escape characters that break Mermaid flowchart node labels."""
    return (
        label.replace("\\", "\\\\")
        .replace('"', "#quot;")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )
