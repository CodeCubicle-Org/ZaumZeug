"""Deploy packager — doctor, eval gate, and bundle write (Architecture §6.4 / §10.2).

Eval gate is E5-S06 / E6-S03. Full bundle assembly (strip, pin, manifest, README,
target install scripts) is E5-S01. Copy-matrix resolve + required-path fail is
E5-S02 (``deploy.copy_rules``).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

import yaml

from zaumzeug.compile.export import find_artifact_manifest
from zaumzeug.config import (
    ConfigValidationError,
    EvalGateMode,
    HarnessConfig,
    load_harness,
)
from zaumzeug.config.harness_root import DEPLOY_MANIFEST, harness_dir as resolve_harness_dir
from zaumzeug.config.loader import _read_yaml_mapping
from zaumzeug.config.models import merge_model_registries
from zaumzeug.config.resolver import (
    AgentResolutionError,
    RuntimeSource,
    load_agent_yaml,
    resolve_agent_serve,
)
from zaumzeug.deploy.copy_rules import (
    CopyRulesError,
    assert_required_paths,
    resolve_deploy_copy_plan,
    strip_agent_yaml,
    strip_harness_yaml,
)
from zaumzeug.doctor.checks import workflow_agent_names
from zaumzeug.doctor.project import find_project_root
from zaumzeug.doctor.report import DoctorReport
from zaumzeug.doctor.runner import run_doctor
from zaumzeug.eval.runner import EvalError, EvalResult, format_eval_result, run_eval
from zaumzeug.runtime.tools.custom import CustomToolError, custom_tool_source_rel

__all__ = [
    "DEFAULT_EVAL_GATE",
    "DeployError",
    "EvalGateResult",
    "PackageResult",
    "TARGET_INSTALL_FILES",
    "apply_eval_gate",
    "discover_install_dir",
    "format_eval_gate_result",
    "package_harness",
    "resolve_eval_gate",
    "write_deploy_bundle",
]

DEFAULT_EVAL_GATE: EvalGateMode = "skip"

TARGET_INSTALL_FILES: tuple[str, ...] = (
    "target_install.py",
    "target-install.sh",
    "target-install.ps1",
)

EvalRunner = Callable[..., EvalResult]
BundleWriter = Callable[..., Path]
DoctorRunner = Callable[..., DoctorReport]


class DeployError(RuntimeError):
    """Deploy orchestration failed with an actionable message."""

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
class EvalGateResult:
    """Outcome of the deploy eval gate pre-step (Architecture §6.4)."""

    mode: EvalGateMode
    skipped: bool
    blocked: bool
    eval_result: EvalResult | None = None
    messages: list[str] = field(default_factory=list)

    @property
    def eval_ran(self) -> bool:
        return self.eval_result is not None


@dataclass(slots=True)
class PackageResult:
    """Outcome of ``zaumzeug deploy`` after the eval gate (and optional pack)."""

    harness_name: str
    harness_dir: Path
    eval_gate: EvalGateResult
    packaged: bool
    bundle_dir: Path | None = None

    @property
    def exit_code(self) -> int:
        return 1 if self.eval_gate.blocked else 0


def resolve_eval_gate(
    harness_config: HarnessConfig,
    *,
    override: str | None = None,
) -> EvalGateMode:
    """Resolve gate mode: CLI ``--eval-gate`` → ``deploy.eval_gate`` → ``skip``."""
    if override is not None:
        normalized = override.strip().lower()
        if normalized not in {"skip", "warn", "block"}:
            raise DeployError(
                f"Unknown eval gate {override!r} (expected 'skip', 'warn', or 'block')",
                harness_name=harness_config.name,
                suggestion="Use --eval-gate skip|warn|block",
            )
        return normalized  # type: ignore[return-value]
    deploy = harness_config.deploy
    if deploy is not None:
        return deploy.eval_gate
    return DEFAULT_EVAL_GATE


def apply_eval_gate(
    harness_name: str,
    harness_config: HarnessConfig,
    *,
    eval_gate_override: str | None = None,
    project_root: Path | str | None = None,
    run_eval_fn: EvalRunner | None = None,
    output: TextIO | None = None,
) -> EvalGateResult:
    """Apply Architecture §6.4 gate before packaging (single source of truth).

    * ``skip`` — do not run eval.
    * ``warn`` / ``block`` — run eval when ``eval:`` is configured; if ``eval:``
      is absent, both modes are a no-op.
    * ``warn`` — print failures and continue (``blocked=False``).
    * ``block`` — abort deploy on any eval failure (``blocked=True``).
    """
    mode = resolve_eval_gate(harness_config, override=eval_gate_override)
    stream = output

    def _emit(message: str) -> None:
        if stream is not None:
            print(message, file=stream)

    if mode == "skip":
        msg = f"Eval gate: skip (deploy.eval_gate={mode})"
        _emit(msg)
        return EvalGateResult(mode=mode, skipped=True, blocked=False, messages=[msg])

    if harness_config.eval is None:
        msg = (
            f"Eval gate: {mode} — no `eval:` section; gate is a no-op "
            "(nothing to run)"
        )
        _emit(msg)
        return EvalGateResult(mode=mode, skipped=True, blocked=False, messages=[msg])

    runner = run_eval_fn or run_eval
    root = Path(project_root) if project_root is not None else None
    try:
        eval_result = runner(harness_name, project_root=root)
    except EvalError as exc:
        raise DeployError(
            f"Eval gate ({mode}) failed to run eval: {exc}",
            path=exc.path,
            harness_name=harness_name,
            suggestion=exc.suggestion or "Fix eval config or use --eval-gate skip",
        ) from exc

    summary = format_eval_result(eval_result)
    messages = [f"Eval gate: {mode}", summary]
    _emit(messages[0])
    _emit(summary)

    if eval_result.failed == 0:
        ok = f"Eval gate ({mode}): all checks passed"
        messages.append(ok)
        _emit(ok)
        return EvalGateResult(
            mode=mode,
            skipped=False,
            blocked=False,
            eval_result=eval_result,
            messages=messages,
        )

    if mode == "warn":
        warn = (
            f"Eval gate (warn): {eval_result.failed} failure(s); "
            "continuing deploy"
        )
        messages.append(warn)
        _emit(warn)
        return EvalGateResult(
            mode=mode,
            skipped=False,
            blocked=False,
            eval_result=eval_result,
            messages=messages,
        )

    block = (
        f"Eval gate (block): {eval_result.failed} failure(s); "
        "aborting deploy"
    )
    messages.append(block)
    _emit(block)
    return EvalGateResult(
        mode=mode,
        skipped=False,
        blocked=True,
        eval_result=eval_result,
        messages=messages,
    )


def format_eval_gate_result(result: EvalGateResult) -> str:
    """Human-readable gate summary for CLI / tests."""
    return "\n".join(result.messages)


def discover_install_dir() -> Path:
    """Locate SDK ``install/`` containing ``target_install.py``."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "install"
        if (candidate / "target_install.py").is_file():
            return candidate
    raise DeployError(
        "install/target_install.py not found. "
        "Run from a ZaumZeug repo checkout with editable install.",
        suggestion="Restore install/target_install.py (and wrappers) in the SDK tree",
    )


def discover_deploy_template_dir() -> Path:
    """Locate ``install/templates/deploy/`` (README.deploy.md template)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "install" / "templates" / "deploy"
        readme = candidate / "README.deploy.md"
        if readme.is_file():
            return candidate
    raise DeployError(
        "install/templates/deploy/README.deploy.md not found. "
        "Run from a ZaumZeug repo checkout with editable install.",
        suggestion="Restore install/templates/deploy/README.deploy.md",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _source_git_sha(project_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    sha = completed.stdout.strip()
    return sha or "unknown"


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _load_optional_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = _read_yaml_mapping(path)
    return data if isinstance(data, dict) else {}


def _artifact_run_id_for_dir(artifact_dir: Path) -> str:
    """Resolve immutable run id for a serve artifact directory."""
    if artifact_dir.name != "current":
        return artifact_dir.name
    if artifact_dir.is_symlink():
        try:
            target = Path(os.readlink(artifact_dir))
        except OSError:
            target = artifact_dir.resolve()
        if target.name and target.name != "current":
            return target.name
    manifest_path = find_artifact_manifest(artifact_dir)
    if manifest_path is not None:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            recorded = payload.get("run_id")
            if isinstance(recorded, str) and recorded.strip():
                return recorded.strip()
    raise DeployError(
        f"Cannot resolve run_id for artifact pin at {artifact_dir}",
        path=artifact_dir,
        suggestion="Pin agent.artifact to artifacts/<run_id> or fix artifacts/current",
    )


def _copy_tree(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=False)


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _pin_agent_artifact(
    *,
    harness_name: str,
    harness_dir: Path,
    agent_name: str,
    dest_agent_dir: Path,
) -> str | None:
    """Copy pinned artifact run into the bundle; return run_id or None."""
    try:
        resolution = resolve_agent_serve(
            harness_dir,
            harness_name=harness_name,
            agent_name=agent_name,
        )
    except AgentResolutionError as exc:
        raise DeployError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=exc.suggestion,
        ) from exc

    if resolution.source != RuntimeSource.ARTIFACT:
        return None

    run_id = _artifact_run_id_for_dir(resolution.path)
    # Prefer the immutable run directory when current is a symlink/copy.
    source_run = resolution.path
    if resolution.path.name == "current":
        candidate = harness_dir / "agents" / agent_name / "artifacts" / run_id
        if candidate.is_dir() and find_artifact_manifest(candidate) is not None:
            source_run = candidate

    dest_run = dest_agent_dir / "artifacts" / run_id
    _copy_tree(source_run, dest_run)
    if find_artifact_manifest(dest_run) is None:
        raise DeployError(
            f"Pinned artifact for agent '{agent_name}' missing artifact-manifest.json",
            path=dest_run,
            harness_name=harness_name,
            suggestion=f"Re-run `zaumzeug compile {harness_name} --agent {agent_name}`",
        )
    return run_id


def _copy_referenced_prompts(
    *,
    agent_data: dict[str, Any],
    src_agent_dir: Path,
    dest_agent_dir: Path,
) -> None:
    """Copy system_prompt (and nested agent.system_prompt) files when present."""
    refs: list[str] = []
    top = agent_data.get("system_prompt")
    if isinstance(top, str) and top.strip():
        refs.append(top.strip())
    nested = agent_data.get("agent")
    if isinstance(nested, dict):
        nested_prompt = nested.get("system_prompt")
        if isinstance(nested_prompt, str) and nested_prompt.strip():
            refs.append(nested_prompt.strip())

    for ref in dict.fromkeys(refs):
        src = Path(ref)
        if not src.is_absolute():
            src = (src_agent_dir / src).resolve()
        if not src.is_file():
            raise DeployError(
                f"Referenced prompt missing: {src}",
                path=src,
                suggestion=f"Create {src} or fix system_prompt in agent.yaml",
            )
        try:
            rel = src.relative_to(src_agent_dir.resolve())
        except ValueError:
            # Absolute path outside agent dir — place under prompts/ basename.
            rel = Path("prompts") / src.name
        _copy_file(src, dest_agent_dir / rel)


def _copy_runtime_tools_and_hooks(
    *,
    agent_data: dict[str, Any],
    src_agent_dir: Path,
    dest_agent_dir: Path,
) -> None:
    """Copy custom tools listed in agent.yaml and hooks.py when enabled."""
    tools = agent_data.get("tools")
    if isinstance(tools, dict):
        custom = tools.get("custom")
        if isinstance(custom, list):
            for entry in custom:
                if not isinstance(entry, str) or not entry.strip():
                    continue
                try:
                    rel = custom_tool_source_rel(entry.strip())
                except CustomToolError:
                    rel = entry.strip().replace("\\", "/")
                src = src_agent_dir / rel
                if not src.is_file():
                    raise DeployError(
                        f"Custom tool listed in agent.yaml is missing: {src}",
                        path=src,
                        suggestion="Add the tool file or remove it from tools.custom",
                    )
                _copy_file(src, dest_agent_dir / rel)

    hooks = agent_data.get("hooks")
    hooks_enabled = False
    if isinstance(hooks, dict) and hooks.get("enabled") is True:
        hooks_enabled = True
    hooks_py = src_agent_dir / "hooks.py"
    if hooks_enabled:
        if not hooks_py.is_file():
            raise DeployError(
                f"hooks.enabled is true but {hooks_py} is missing",
                path=hooks_py,
                suggestion="Add hooks.py or set hooks.enabled: false",
            )
        _copy_file(hooks_py, dest_agent_dir / "hooks.py")


def _copy_exposed_pipelines(
    *,
    harness_dir: Path,
    dest_dir: Path,
    harness_raw: dict[str, Any],
) -> None:
    """Copy pipelines listed under serve.expose (Phase 4+; no-op when absent)."""
    serve = harness_raw.get("serve")
    if not isinstance(serve, dict):
        return
    expose = serve.get("expose")
    if not isinstance(expose, list) or not expose:
        return
    for pipeline_id in expose:
        if not isinstance(pipeline_id, str) or not pipeline_id.strip():
            continue
        name = pipeline_id.strip()
        # Accept id with or without .yaml suffix.
        candidates = [
            harness_dir / "pipelines" / name,
            harness_dir / "pipelines" / f"{name}.yaml",
            harness_dir / "pipelines" / f"{name}.yml",
        ]
        src = next((path for path in candidates if path.is_file()), None)
        if src is None:
            raise DeployError(
                f"Pipeline '{name}' listed in serve.expose is missing under pipelines/",
                path=harness_dir / "pipelines",
                suggestion=f"Add pipelines/{name}.yaml or remove it from serve.expose",
            )
        _copy_file(src, dest_dir / "pipelines" / src.name)


def _render_readme_deploy(
    *,
    harness_name: str,
    created_at: str,
    build_id: str,
) -> str:
    template_dir = discover_deploy_template_dir()
    template = (template_dir / "README.deploy.md").read_text(encoding="utf-8")
    return (
        template.replace("{{harness_name}}", harness_name)
        .replace("{{created_at}}", created_at)
        .replace("{{build_id}}", build_id)
    )


def _copy_target_install_scripts(dest_dir: Path) -> None:
    install_dir = discover_install_dir()
    missing = [
        name for name in TARGET_INSTALL_FILES if not (install_dir / name).is_file()
    ]
    if missing:
        raise DeployError(
            "Missing target install script(s) in install/: " + ", ".join(missing),
            path=install_dir,
            suggestion="Restore install/target_install.py and wrappers",
        )
    for name in TARGET_INSTALL_FILES:
        _copy_file(install_dir / name, dest_dir / name)


def _load_agents_for_deploy(
    harness_dir: Path,
    *,
    harness_name: str,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Discover workflow agents and load raw agent.yaml mappings."""
    agent_names = workflow_agent_names(harness_dir)
    if not agent_names:
        raise DeployError(
            f"No agents found for harness '{harness_name}'",
            path=harness_dir / "agents",
            harness_name=harness_name,
            suggestion="Define workflow entry/stages or agents/<name>/agent.yaml",
        )

    agents_data: dict[str, dict[str, Any]] = {}
    for agent_name in agent_names:
        agent_yaml_path = harness_dir / "agents" / agent_name / "agent.yaml"
        if not agent_yaml_path.is_file():
            raise DeployError(
                f"Missing agent.yaml for '{agent_name}'",
                path=agent_yaml_path,
                harness_name=harness_name,
            )
        _, agent_data = load_agent_yaml(harness_dir, agent_name)
        agents_data[agent_name] = agent_data
    return agent_names, agents_data


def _validate_copy_matrix(
    harness_dir: Path,
    *,
    harness_name: str,
    harness_raw: dict[str, Any],
    agents_data: dict[str, dict[str, Any]],
) -> None:
    """Resolve §10.1 matrix and fail before writing when required paths miss."""
    copy_plan = resolve_deploy_copy_plan(
        harness_raw=harness_raw,
        agents=agents_data,
    )
    try:
        assert_required_paths(harness_dir, copy_plan)
    except CopyRulesError as exc:
        raise DeployError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=exc.suggestion,
        ) from exc


def write_deploy_bundle(
    harness_name: str,
    *,
    project_root: Path,
    harness_dir: Path,
    harness_config: HarnessConfig,
) -> Path:
    """Assemble ``deploy/<name>/`` per Architecture §10.2 (idempotent overwrite)."""
    del harness_config  # validated upstream; we re-read raw yaml for strip/copy

    harness_yaml_src = harness_dir / "harness.yaml"
    harness_raw = _read_yaml_mapping(harness_yaml_src)
    if not isinstance(harness_raw, dict):
        raise DeployError(
            f"harness.yaml must be a mapping: {harness_yaml_src}",
            path=harness_yaml_src,
            harness_name=harness_name,
        )

    agent_names, agents_data = _load_agents_for_deploy(
        harness_dir,
        harness_name=harness_name,
    )
    # E5-S02: validate include matrix before wiping/writing deploy/<name>/.
    _validate_copy_matrix(
        harness_dir,
        harness_name=harness_name,
        harness_raw=harness_raw,
        agents_data=agents_data,
    )

    dest = project_root / "deploy" / harness_name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    stripped_harness = strip_harness_yaml(harness_raw)
    # Keep models: as a relative bundle path when declared.
    if "models" in stripped_harness:
        stripped_harness["models"] = "models.yaml"
        global_models = _load_optional_yaml(project_root / "config" / "models.yaml")
        harness_models_ref = harness_raw.get("models")
        harness_models_path: Path | None = None
        if isinstance(harness_models_ref, str) and harness_models_ref.strip():
            hm = Path(harness_models_ref.strip())
            harness_models_path = (
                hm if hm.is_absolute() else (harness_dir / hm).resolve()
            )
        harness_models = (
            _load_optional_yaml(harness_models_path)
            if harness_models_path is not None
            else {}
        )
        merged = merge_model_registries(global_models, harness_models)
        _write_yaml(dest / "models.yaml", merged)

    _write_yaml(dest / "harness.yaml", stripped_harness)
    _copy_file(harness_dir / "workflow.yaml", dest / "workflow.yaml")
    _copy_file(
        harness_dir / "docs" / "workflow-diagram.md",
        dest / "docs" / "workflow-diagram.md",
    )
    _copy_exposed_pipelines(
        harness_dir=harness_dir,
        dest_dir=dest,
        harness_raw=harness_raw,
    )

    artifact_run_ids: dict[str, str] = {}
    for agent_name in agent_names:
        src_agent_dir = harness_dir / "agents" / agent_name
        dest_agent_dir = dest / "agents" / agent_name
        agent_data = agents_data[agent_name]
        _copy_file(
            src_agent_dir / "agents-models.yaml",
            dest_agent_dir / "agents-models.yaml",
        )

        run_id = _pin_agent_artifact(
            harness_name=harness_name,
            harness_dir=harness_dir,
            agent_name=agent_name,
            dest_agent_dir=dest_agent_dir,
        )
        stripped_agent = strip_agent_yaml(agent_data)
        if run_id is not None:
            artifact_run_ids[agent_name] = run_id
            agent_section = stripped_agent.get("agent")
            if not isinstance(agent_section, dict):
                agent_section = {}
            else:
                agent_section = dict(agent_section)
            agent_section["artifact"] = f"artifacts/{run_id}"
            # Prefer pinned artifact over system_prompt in the bundle.
            agent_section.pop("system_prompt", None)
            stripped_agent["agent"] = agent_section
            stripped_agent.pop("system_prompt", None)
        else:
            _copy_referenced_prompts(
                agent_data=agent_data,
                src_agent_dir=src_agent_dir,
                dest_agent_dir=dest_agent_dir,
            )

        _copy_runtime_tools_and_hooks(
            agent_data=agent_data,
            src_agent_dir=src_agent_dir,
            dest_agent_dir=dest_agent_dir,
        )
        _write_yaml(dest_agent_dir / "agent.yaml", stripped_agent)

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    build_id = str(uuid.uuid4())
    harness_yaml_hash = _sha256_file(harness_yaml_src)
    # Prefer per-agent map; empty map when all agents use system_prompt only.
    artifact_run_id: dict[str, str] | str = artifact_run_ids
    if len(artifact_run_ids) == 1:
        # Architecture example uses a string when a single pin is natural;
        # doctor accepts both. Keep map for multi-agent clarity.
        pass

    manifest = {
        "build_id": build_id,
        "source_git_sha": _source_git_sha(project_root),
        "harness_yaml_hash": harness_yaml_hash,
        "artifact_run_id": artifact_run_id,
        "created_at": created_at,
    }
    (dest / DEPLOY_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    readme = _render_readme_deploy(
        harness_name=harness_name,
        created_at=created_at,
        build_id=build_id,
    )
    (dest / "README.deploy.md").write_text(readme, encoding="utf-8")
    _copy_target_install_scripts(dest)
    return dest


def _run_doctor_preflight(
    harness_name: str,
    *,
    project_root: Path,
    run_doctor_fn: DoctorRunner | None = None,
    output: TextIO | None = None,
) -> None:
    """Architecture §10.2 step 1 — abort deploy on doctor failures."""
    runner = run_doctor_fn or run_doctor
    report = runner(
        harness_name=harness_name,
        project_root=project_root,
        deploy=False,
    )
    if output is not None:
        print(report.format(verbose=False), file=output)
    if report.exit_code != 0:
        failures = [
            f"{check.name}: {check.message}"
            for check in report.checks
            if check.severity == "fail"
        ]
        detail = "; ".join(failures) if failures else "doctor reported failures"
        raise DeployError(
            f"Doctor preflight failed for '{harness_name}': {detail}",
            harness_name=harness_name,
            suggestion=f"Fix issues from `zaumzeug doctor {harness_name}` then re-deploy",
        )


def package_harness(
    harness_name: str,
    *,
    eval_gate: str | None = None,
    project_root: Path | str | None = None,
    run_eval_fn: EvalRunner | None = None,
    run_doctor_fn: DoctorRunner | None = None,
    write_bundle: BundleWriter | None = None,
    output: TextIO | None = None,
) -> PackageResult:
    """Run deploy packager: doctor → eval gate (§6.4) → bundle write (E5-S01).

    *eval_gate* is the CLI ``--eval-gate`` override. Inject *run_eval_fn* /
    *run_doctor_fn* / *write_bundle* in unit tests.
    """
    root = Path(project_root) if project_root is not None else find_project_root()
    harness_path = resolve_harness_dir(root, harness_name, deploy=False)
    harness_yaml = harness_path / "harness.yaml"
    if not harness_yaml.is_file():
        raise DeployError(
            f"Harness '{harness_name}' not found at {harness_path} (missing harness.yaml)",
            path=harness_path,
            harness_name=harness_name,
            suggestion=f"Create the harness with `zaumzeug init {harness_name}`",
        )

    try:
        harness_config = load_harness(harness_yaml)
    except ConfigValidationError as exc:
        raise DeployError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=f"Fix harness.yaml at {harness_yaml}",
        ) from exc

    _run_doctor_preflight(
        harness_name,
        project_root=root,
        run_doctor_fn=run_doctor_fn,
        output=output,
    )

    gate = apply_eval_gate(
        harness_name,
        harness_config,
        eval_gate_override=eval_gate,
        project_root=root,
        run_eval_fn=run_eval_fn,
        output=output,
    )
    if gate.blocked:
        return PackageResult(
            harness_name=harness_name,
            harness_dir=harness_path,
            eval_gate=gate,
            packaged=False,
            bundle_dir=None,
        )

    writer = write_bundle or write_deploy_bundle
    bundle_dir = writer(
        harness_name,
        project_root=root,
        harness_dir=harness_path,
        harness_config=harness_config,
    )
    return PackageResult(
        harness_name=harness_name,
        harness_dir=harness_path,
        eval_gate=gate,
        packaged=True,
        bundle_dir=Path(bundle_dir),
    )
