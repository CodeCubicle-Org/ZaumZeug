"""Doctor orchestration — run environment and harness checks."""

from __future__ import annotations

from pathlib import Path

from zaumzeug.config.harness_root import harness_dir as resolve_harness_dir
from zaumzeug.config.harness_root import harness_root_segment, is_deploy_mode
from zaumzeug.config import load_harness_for_doctor
from zaumzeug.doctor.checks import (
    _live_providers,
    check_artifact_module_staleness,
    check_deploy_manifest,
    check_env_for_live_models,
    check_harness_config,
    check_mcp_uv_presence,
    check_model_registry,
    check_package_import,
    check_port_conflict,
    check_python_version,
    check_runtime_paths,
    check_workflow_config,
    check_workflow_diagram_staleness,
    workflow_agent_names,
)
from zaumzeug.doctor.project import discover_harnesses, find_project_root, list_agent_names
from zaumzeug.doctor.report import CheckResult, DoctorReport


def run_doctor(
    *,
    harness_name: str | None = None,
    project_root: Path | str | None = None,
    deploy: bool = False,
) -> DoctorReport:
    """Run doctor checks for one harness or all harnesses under the project."""
    root = Path(project_root) if project_root is not None else find_project_root()
    deploy_mode = is_deploy_mode(deploy_flag=deploy)
    root_segment = harness_root_segment(deploy=deploy_mode)
    checks: list[CheckResult] = [
        check_python_version(),
        check_package_import(),
    ]

    if harness_name is not None:
        harness_path = resolve_harness_dir(root, harness_name, deploy=deploy_mode)
        if not (harness_path / "harness.yaml").is_file():
            checks.append(
                CheckResult(
                    name="harness_discovery",
                    severity="fail",
                    message=(
                        f"Harness '{harness_name}' not found at {harness_path} "
                        f"({root_segment}/)"
                    ),
                )
            )
            return DoctorReport(checks=checks)
        targets = [(harness_name, harness_path)]
    else:
        targets = discover_harnesses(root, deploy=deploy_mode)
        if not targets:
            checks.append(
                CheckResult(
                    name="harness_discovery",
                    severity="warn",
                    message=f"No harnesses found under {root / root_segment}",
                )
            )
            return DoctorReport(checks=checks)
        checks.append(
            CheckResult(
                name="harness_discovery",
                severity="pass",
                message=f"Scanning {len(targets)} harness(es) under {root_segment}/",
            )
        )

    all_merged: list[object] = []
    for name, harness_dir in targets:
        if deploy_mode:
            checks.extend(check_deploy_manifest(name, harness_dir))
        checks.extend(check_harness_config(name, harness_dir))
        checks.extend(check_workflow_config(name, harness_dir))
        agent_names = workflow_agent_names(harness_dir)
        if not agent_names:
            checks.append(
                CheckResult(
                    name="agents",
                    severity="warn",
                    message="No agents found under agents/",
                    harness=name,
                )
            )
            continue

        harness_models_path: str | None = None
        harness_yaml = harness_dir / "harness.yaml"
        if harness_yaml.is_file():
            harness_models_path = load_harness_for_doctor(harness_yaml).models

        model_checks, merged_registries = check_model_registry(
            name,
            root,
            harness_dir,
            agent_names=agent_names,
            harness_models_path=harness_models_path,
        )
        checks.extend(model_checks)
        all_merged.extend(merged_registries)

        runtime_targets = agent_names or list_agent_names(harness_dir)
        checks.extend(
            check_runtime_paths(name, harness_dir, agent_names=runtime_targets)
        )
        if not deploy_mode:
            checks.extend(
                check_artifact_module_staleness(
                    name, harness_dir, agent_names=runtime_targets
                )
            )

        port = 1416
        if harness_yaml.is_file():
            harness_cfg = load_harness_for_doctor(harness_yaml)
            if harness_cfg.serve and harness_cfg.serve.hayhooks:
                port = harness_cfg.serve.hayhooks.port
        checks.append(check_port_conflict(name, port=port))
        if not deploy_mode:
            checks.append(check_mcp_uv_presence(name, harness_dir))
            checks.append(check_workflow_diagram_staleness(name, harness_dir))

    checks.extend(check_env_for_live_models(root, live_providers=_live_providers(all_merged)))
    return DoctorReport(checks=checks)
