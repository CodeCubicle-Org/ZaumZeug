"""Doctor orchestration — run environment and harness checks."""

from __future__ import annotations

from pathlib import Path

from zaumzeug.config import load_harness
from zaumzeug.doctor.checks import (
    _live_providers,
    check_env_for_live_models,
    check_harness_config,
    check_model_registry,
    check_package_import,
    check_port_conflict,
    check_python_version,
    check_runtime_paths,
    workflow_agent_names,
)
from zaumzeug.doctor.project import discover_harnesses, find_project_root, list_agent_names
from zaumzeug.doctor.report import CheckResult, DoctorReport


def run_doctor(
    *,
    harness_name: str | None = None,
    project_root: Path | str | None = None,
) -> DoctorReport:
    """Run doctor checks for one harness or all harnesses under the project."""
    root = Path(project_root) if project_root is not None else find_project_root()
    checks: list[CheckResult] = [
        check_python_version(),
        check_package_import(),
    ]

    if harness_name is not None:
        harness_dir = root / "usr-harnesses" / harness_name
        if not (harness_dir / "harness.yaml").is_file():
            checks.append(
                CheckResult(
                    name="harness_discovery",
                    severity="fail",
                    message=f"Harness '{harness_name}' not found at {harness_dir}",
                )
            )
            return DoctorReport(checks=checks)
        targets = [(harness_name, harness_dir)]
    else:
        targets = discover_harnesses(root)
        if not targets:
            checks.append(
                CheckResult(
                    name="harness_discovery",
                    severity="warn",
                    message=f"No harnesses found under {root / 'usr-harnesses'}",
                )
            )
            return DoctorReport(checks=checks)
        checks.append(
            CheckResult(
                name="harness_discovery",
                severity="pass",
                message=f"Scanning {len(targets)} harness(es) under usr-harnesses/",
            )
        )

    all_merged: list[object] = []
    for name, harness_dir in targets:
        checks.extend(check_harness_config(name, harness_dir))
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
            harness_models_path = load_harness(harness_yaml).models

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

        port = 1416
        if harness_yaml.is_file():
            harness_cfg = load_harness(harness_yaml)
            if harness_cfg.serve and harness_cfg.serve.hayhooks:
                port = harness_cfg.serve.hayhooks.port
        checks.append(check_port_conflict(name, port=port))

    checks.extend(check_env_for_live_models(root, live_providers=_live_providers(all_merged)))
    return DoctorReport(checks=checks)
