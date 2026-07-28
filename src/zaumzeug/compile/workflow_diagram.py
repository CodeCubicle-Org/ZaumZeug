"""Generate harness ``docs/workflow-diagram.md`` at compile time (E4-S08 / E4.7).

Architecture §5.4: every ``zaumzeug compile`` regenerates a Mermaid flowchart from
``workflow.yaml`` + resolved agent ``default_model_id`` values. Use
``--workflow-diagram-only`` to refresh without GEPA or LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from zaumzeug.config import (
    ConfigValidationError,
    load_harness,
    load_merged_agent_models,
    load_workflow,
)
from zaumzeug.config.harness_root import harness_dir as resolve_harness_dir
from zaumzeug.config.resolver import AgentResolutionError, load_agent_yaml
from zaumzeug.config.schemas import WorkflowConfig, WorkflowStage
from zaumzeug.doctor.project import find_project_root

__all__ = [
    "WORKFLOW_DIAGRAM_REL",
    "WorkflowDiagramError",
    "WorkflowDiagramResult",
    "format_workflow_diagram_result",
    "render_workflow_diagram",
    "write_workflow_diagram",
]

WORKFLOW_DIAGRAM_REL = Path("docs") / "workflow-diagram.md"


class WorkflowDiagramError(RuntimeError):
    """Workflow diagram generation failed with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        harness_name: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.harness_name = harness_name
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(slots=True)
class WorkflowDiagramResult:
    """Outcome of writing ``docs/workflow-diagram.md``."""

    harness_name: str
    harness_dir: Path
    diagram_path: Path
    markdown: str


def write_workflow_diagram(
    harness_name: str,
    *,
    project_root: Path | str | None = None,
    deploy: bool = False,
    generated_on: date | None = None,
) -> WorkflowDiagramResult:
    """Render and write ``docs/workflow-diagram.md`` under the harness."""
    root = Path(project_root) if project_root is not None else find_project_root()
    harness_path = resolve_harness_dir(root, harness_name, deploy=deploy)
    harness_yaml = harness_path / "harness.yaml"
    if not harness_yaml.is_file():
        raise WorkflowDiagramError(
            f"Harness '{harness_name}' not found at {harness_path} (missing harness.yaml)",
            path=harness_path,
            harness_name=harness_name,
            suggestion=f"Create the harness with `zaumzeug init {harness_name}`",
        )

    try:
        harness_config = load_harness(harness_yaml)
    except ConfigValidationError as exc:
        raise WorkflowDiagramError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=f"Fix harness.yaml at {harness_yaml}",
        ) from exc

    try:
        workflow = load_workflow(harness_path)
    except ConfigValidationError as exc:
        raise WorkflowDiagramError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=f"Fix workflow.yaml under {harness_path}",
        ) from exc

    harness_models = _resolve_harness_models_path(harness_path, harness_config.models)
    markdown = render_workflow_diagram(
        harness_name=harness_name,
        workflow=workflow,
        harness_dir=harness_path,
        project_root=root,
        harness_models_path=harness_models,
        generated_on=generated_on or date.today(),
    )

    diagram_path = harness_path / WORKFLOW_DIAGRAM_REL
    diagram_path.parent.mkdir(parents=True, exist_ok=True)
    diagram_path.write_text(markdown, encoding="utf-8", newline="\n")
    return WorkflowDiagramResult(
        harness_name=harness_name,
        harness_dir=harness_path,
        diagram_path=diagram_path,
        markdown=markdown,
    )


def render_workflow_diagram(
    *,
    harness_name: str,
    workflow: WorkflowConfig,
    harness_dir: Path,
    project_root: Path,
    harness_models_path: Path | None = None,
    generated_on: date | None = None,
) -> str:
    """Return Markdown + Mermaid for a serial workflow diagram."""
    when = generated_on or date.today()
    mermaid_lines = ["flowchart LR"]
    node_ids: list[str] = []

    for index, stage in enumerate(workflow.stages):
        node_id = f"s{index}"
        node_ids.append(node_id)
        label = _stage_label(
            stage,
            harness_dir=harness_dir,
            project_root=project_root,
            harness_models_path=harness_models_path,
        )
        mermaid_lines.append(f'  {node_id}["{_escape_mermaid_label(label)}"]')

    for left, right in zip(node_ids, node_ids[1:], strict=False):
        mermaid_lines.append(f"  {left} --> {right}")

    stage_count = len(workflow.stages)
    stage_word = "stage" if stage_count == 1 else "stages"
    mermaid_block = "\n".join(mermaid_lines)
    return (
        f"# Workflow diagram — {harness_name}\n"
        f"\n"
        f"> Auto-generated by `zaumzeug compile {harness_name}`. Do not edit by hand.\n"
        f"\n"
        f"```mermaid\n"
        f"{mermaid_block}\n"
        f"```\n"
        f"\n"
        f"**Stages:** {stage_count} serial {stage_word} · "
        f"**Entry:** `{workflow.entry}` · "
        f"**Generated:** {when.isoformat()}\n"
    )


def format_workflow_diagram_result(result: WorkflowDiagramResult) -> str:
    """Human-readable summary for ``--workflow-diagram-only``."""
    return (
        f"Workflow diagram refreshed for harness '{result.harness_name}'.\n"
        f"  wrote: {result.diagram_path}"
    )


def _stage_label(
    stage: WorkflowStage,
    *,
    harness_dir: Path,
    project_root: Path,
    harness_models_path: Path | None,
) -> str:
    if stage.pipeline:
        return stage.pipeline.strip()

    agent_name = (stage.agent or "").strip()
    model_id, provider = _resolve_agent_model_label(
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


def _resolve_agent_model_label(
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


def _escape_mermaid_label(label: str) -> str:
    """Escape characters that break Mermaid flowchart node labels."""
    return (
        label.replace("\\", "\\\\")
        .replace('"', "#quot;")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )
