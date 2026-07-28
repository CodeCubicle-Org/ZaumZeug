"""``zaumzeug compile`` orchestration — validate, load modules, run GEPA.

E4-S02a: schema + module load + LM preflight.
E4-S02b: invoke GEPA and write ``artifacts/<run_id>/`` + ``current``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zaumzeug.compile.gepa_runner import (
    CompileLmPlan,
    GepaPreflightError,
    GepaRunError,
    GepaRunResult,
    invoke_gepa,
    preflight_compile_lms,
)
from zaumzeug.compile.module_loader import ModuleLoaderError, load_dspy_module_from_resolution
from zaumzeug.config import (
    AgentResolutionError,
    ConfigValidationError,
    load_harness,
    load_merged_agent_models,
    load_workflow,
    resolve_agent_compile,
)
from zaumzeug.config.harness_root import harness_dir as resolve_harness_dir
from zaumzeug.doctor.project import find_project_root, list_agent_names

__all__ = [
    "CompileError",
    "CompileAgentResult",
    "CompileResult",
    "run_compile",
]


class CompileError(RuntimeError):
    """Compile orchestration failed with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        harness_name: str | None = None,
        agent_name: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.harness_name = harness_name
        self.agent_name = agent_name
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(slots=True)
class CompileAgentResult:
    """Per-agent compile outcome including GEPA artifacts (E4-S02b)."""

    agent_name: str
    module_ref: str
    lm_plan: CompileLmPlan
    module_instance: Any
    gepa_invoked: bool = False
    run_id: str | None = None
    artifact_dir: Path | None = None
    gepa_result: GepaRunResult | None = None


@dataclass(slots=True)
class CompileResult:
    """Outcome of ``zaumzeug compile`` for one harness."""

    harness_name: str
    harness_dir: Path
    agents: list[CompileAgentResult] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 0


def run_compile(
    harness_name: str,
    *,
    agent_name: str | None = None,
    project_root: Path | str | None = None,
    deploy: bool = False,
    gepa_cls: Any | None = None,
    stub_gepa: bool | None = None,
) -> CompileResult:
    """Validate Phase 2 compile config, load DSPy modules, run GEPA, write artifacts.

    Failures raise :class:`CompileError` before or during the optimizer call.
    Pass *gepa_cls* (or ``stub_gepa=True``) to inject a CI stub without live API keys.
    """
    root = Path(project_root) if project_root is not None else find_project_root()
    harness_path = resolve_harness_dir(root, harness_name, deploy=deploy)
    harness_yaml = harness_path / "harness.yaml"
    if not harness_yaml.is_file():
        raise CompileError(
            f"Harness '{harness_name}' not found at {harness_path} (missing harness.yaml)",
            path=harness_path,
            harness_name=harness_name,
            suggestion=f"Create the harness with `zaumzeug init {harness_name}`",
        )

    try:
        harness_config = load_harness(harness_yaml)
    except ConfigValidationError as exc:
        raise CompileError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=f"Fix harness.yaml at {harness_yaml}",
        ) from exc

    try:
        load_workflow(harness_path)
    except ConfigValidationError as exc:
        raise CompileError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=f"Fix workflow.yaml under {harness_path}",
        ) from exc

    targets = _compile_agent_targets(harness_path, harness_name=harness_name, agent_name=agent_name)
    harness_models = harness_config.models

    results: list[CompileAgentResult] = []
    for name in targets:
        try:
            resolution = resolve_agent_compile(
                harness_path,
                harness_name=harness_name,
                agent_name=name,
            )
        except AgentResolutionError as exc:
            raise CompileError(
                str(exc),
                path=exc.path,
                harness_name=exc.harness_name or harness_name,
                agent_name=exc.agent_name or name,
                suggestion=exc.suggestion,
            ) from exc

        try:
            module_instance = load_dspy_module_from_resolution(resolution)
        except ModuleLoaderError as exc:
            raise CompileError(
                str(exc),
                path=exc.path,
                harness_name=exc.harness_name or harness_name,
                agent_name=exc.agent_name or name,
                suggestion=exc.suggestion,
            ) from exc

        try:
            registry = load_merged_agent_models(
                project_root=root,
                harness_dir=harness_path,
                harness_models_path=harness_models,
                agent_name=name,
            )
        except ConfigValidationError as exc:
            raise CompileError(
                str(exc),
                path=exc.path,
                harness_name=harness_name,
                agent_name=name,
                suggestion=(
                    f"Fix agents/{name}/agents-models.yaml (or merged registry tiers)"
                ),
            ) from exc

        try:
            lm_plan = preflight_compile_lms(
                resolution,
                registry=registry,
                project_root=root,
            )
        except GepaPreflightError as exc:
            raise CompileError(
                str(exc),
                path=exc.path,
                harness_name=exc.harness_name or harness_name,
                agent_name=exc.agent_name or name,
                suggestion=exc.suggestion,
            ) from exc

        agent_dir = resolution.agent_yaml_path.parent
        try:
            gepa_result = invoke_gepa(
                module=module_instance,
                resolution=resolution,
                lm_plan=lm_plan,
                agent_dir=agent_dir,
                gepa_cls=gepa_cls,
                stub=stub_gepa,
            )
        except GepaRunError as exc:
            raise CompileError(
                str(exc),
                path=exc.path,
                harness_name=exc.harness_name or harness_name,
                agent_name=exc.agent_name or name,
                suggestion=exc.suggestion,
            ) from exc

        results.append(
            CompileAgentResult(
                agent_name=name,
                module_ref=resolution.compile_module,
                lm_plan=lm_plan,
                module_instance=gepa_result.optimized_module,
                gepa_invoked=True,
                run_id=gepa_result.run_id,
                artifact_dir=gepa_result.artifact_dir,
                gepa_result=gepa_result,
            )
        )

    return CompileResult(
        harness_name=harness_name,
        harness_dir=harness_path,
        agents=results,
    )


def _compile_agent_targets(
    harness_dir: Path,
    *,
    harness_name: str,
    agent_name: str | None,
) -> list[str]:
    if agent_name is not None:
        agent_yaml = harness_dir / "agents" / agent_name / "agent.yaml"
        if not agent_yaml.is_file():
            raise CompileError(
                (
                    f"Harness '{harness_name}': agent '{agent_name}' not found "
                    f"(expected {agent_yaml})"
                ),
                path=agent_yaml,
                harness_name=harness_name,
                agent_name=agent_name,
                suggestion=f"Pass a valid --agent name under {harness_dir / 'agents'}",
            )
        return [agent_name]

    # All agents that declare a compile section (module required by schema).
    targets: list[str] = []
    for name in list_agent_names(harness_dir):
        try:
            resolve_agent_compile(
                harness_dir,
                harness_name=harness_name,
                agent_name=name,
            )
        except AgentResolutionError:
            continue
        targets.append(name)

    if not targets:
        raise CompileError(
            (
                f"Harness '{harness_name}' has no agents with `compile.module`. "
                f"Add a Phase 2 `compile:` block to an agent.yaml or pass --agent."
            ),
            path=harness_dir,
            harness_name=harness_name,
            suggestion=(
                "Add `compile.module: modules.<name>:<Class>` under "
                f"{harness_dir / 'agents'}/<name>/agent.yaml"
            ),
        )
    return targets


def format_compile_result(result: CompileResult) -> str:
    """Human-readable compile summary for the CLI."""
    lines = [
        f"Compile OK for harness '{result.harness_name}' "
        f"({len(result.agents)} agent(s)).",
    ]
    for agent in result.agents:
        stub = ""
        if agent.gepa_result is not None and agent.gepa_result.stubbed:
            stub = " (stub GEPA)"
        artifact = (
            str(agent.artifact_dir)
            if agent.artifact_dir is not None
            else "(no artifact)"
        )
        lines.append(
            f"  - {agent.agent_name}: module={agent.module_ref} "
            f"task={agent.lm_plan.task_model_id} "
            f"reflection={agent.lm_plan.reflection_model_id} "
            f"run_id={agent.run_id}{stub}"
        )
        lines.append(f"    artifacts: {artifact}")
    return "\n".join(lines)
