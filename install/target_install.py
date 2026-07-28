#!/usr/bin/env python3
"""Target runtime install for a ZaumZeug deploy bundle (Architecture §10.7 / E5-S09a).

Prepares a production host after ops copies ``deploy/<name>/``:

1. Preflight ``harness.yaml`` + ``manifest.json``
2. Require Python 3.11+ (does **not** install Python)
3. Optional ``.venv`` beside the bundle (unless ``--skip-venv``)
4. ``pip install zaumzeug`` — runtime only (no ``[dev]``, ``[eval]``, DSPy, GEPA, DeepEval)
5. Seed ``.env`` from ``.env.example`` when missing (never overwrite)

``--verify`` (doctor ``--deploy`` + serve ``--deploy --dry-run``) lands in E5-S09c.
Shell wrappers: ``target-install.sh`` / ``target-install.ps1`` (E5-S09b).

Usage (from the deploy bundle directory)::

    python target_install.py
    python target_install.py --deploy-dir /path/to/deploy/my_agent
    python target_install.py --skip-venv
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

MIN_PYTHON = (3, 11)
VENV_DIRNAME = ".venv"
RUNTIME_PIP_SPEC = "zaumzeug"

__all__ = [
    "TargetInstallError",
    "main",
    "parse_args",
    "preflight_bundle",
    "run_install",
]


class TargetInstallError(Exception):
    """Fatal target-install failure with an actionable message."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="target_install",
        description=(
            "Prepare a ZaumZeug deploy bundle on the target host: "
            "optional .venv, pip install zaumzeug (runtime only), seed .env."
        ),
    )
    parser.add_argument(
        "--deploy-dir",
        type=Path,
        default=None,
        help="Deploy bundle directory (default: current working directory)",
    )
    parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="do not create .venv; use the current Python for pip (CI / existing env)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Reserved for E5-S09c (doctor --deploy + serve --deploy --dry-run)",
    )
    return parser.parse_args(argv)


def preflight_bundle(deploy_dir: Path) -> list[str]:
    """Return human-readable errors if the bundle is incomplete."""
    errors: list[str] = []
    if not (deploy_dir / "harness.yaml").is_file():
        errors.append(f"Missing harness.yaml in {deploy_dir}")
    if not (deploy_dir / "manifest.json").is_file():
        errors.append(f"Missing manifest.json in {deploy_dir}")
    return errors


def require_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        major, minor = MIN_PYTHON
        current = f"{sys.version_info.major}.{sys.version_info.minor}"
        raise TargetInstallError(
            f"Python {major}.{minor}+ is required; found {current}. "
            f"Install Python {major}.{minor} or newer on the target and re-run "
            "(target_install does not install Python)."
        )


def is_windows() -> bool:
    return platform.system() == "Windows"


def venv_scripts_dir(venv_dir: Path) -> Path:
    """Return the venv scripts/bin directory for the current OS."""
    if is_windows():
        return venv_dir / "Scripts"
    return venv_dir / "bin"


def venv_python(venv_dir: Path) -> Path:
    """Return the Python executable inside ``venv_dir``."""
    scripts = venv_scripts_dir(venv_dir)
    if is_windows():
        return scripts / "python.exe"
    return scripts / "python"


def activation_hint(venv_dir: Path) -> str:
    """Human-readable activation command for the current OS."""
    scripts = venv_scripts_dir(venv_dir)
    if is_windows():
        activate = scripts / "Activate.ps1"
        return f"  {activate}"
    activate = scripts / "activate"
    return f"  source {activate}"


def ensure_venv(venv_dir: Path) -> bool:
    """Create ``venv_dir`` when missing. Returns True if created."""
    if venv_dir.exists():
        return False
    print(f"Creating virtual environment at {venv_dir} …")
    builder = venv.EnvBuilder(with_pip=True, clear=False, upgrade=False)
    builder.create(venv_dir)
    return True


def run_command(
    cmd: list[str],
    *,
    cwd: Path,
    what: str,
) -> None:
    """Run a subprocess; raise TargetInstallError on failure."""
    print(f"$ {' '.join(cmd)}")
    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise TargetInstallError(
            f"{what} failed to start: {exc}. "
            "Check that Python and pip are available."
        ) from exc

    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(
            completed.stderr,
            end="" if completed.stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )
    if completed.returncode != 0:
        raise TargetInstallError(
            f"{what} failed with exit code {completed.returncode}. "
            f"Command: {' '.join(cmd)}"
        )


def resolve_install_python(
    deploy_dir: Path,
    *,
    skip_venv: bool,
) -> Path:
    """Return the Python used for pip; create ``.venv`` beside the bundle unless skipped."""
    if skip_venv:
        print("Skipping .venv creation (--skip-venv); using current Python.")
        return Path(sys.executable)

    venv_dir = deploy_dir / VENV_DIRNAME
    created = ensure_venv(venv_dir)
    python = venv_python(venv_dir)
    if not python.is_file():
        raise TargetInstallError(
            f"Expected venv Python at {python} after "
            f"{'creating' if created else 'locating'} {venv_dir}."
        )
    return python


def runtime_pip_install(python: Path, *, cwd: Path) -> None:
    """Run ``python -m pip install zaumzeug`` (runtime only — no extras)."""
    run_command(
        [str(python), "-m", "pip", "install", RUNTIME_PIP_SPEC],
        cwd=cwd,
        what=f"Runtime install (pip install {RUNTIME_PIP_SPEC})",
    )


def check_zaumzeug_version(python: Path, *, cwd: Path) -> None:
    """Confirm the installed CLI is importable via ``zaumzeug --version``."""
    run_command(
        [str(python), "-m", "zaumzeug", "--version"],
        cwd=cwd,
        what="zaumzeug --version",
    )


def resolve_project_root(deploy_dir: Path) -> Path:
    """Return the project root that contains ``deploy/<name>/`` when applicable.

    Standard layout: ``<project>/deploy/<name>/`` → project root is two levels up.
    Standalone copy of the bundle alone → project root is the bundle's parent
    (or the bundle itself when there is no useful parent).
    """
    parent = deploy_dir.parent
    if parent.name == "deploy":
        return parent.parent
    return parent


def resolve_env_example(deploy_dir: Path) -> Path | None:
    """Locate ``.env.example`` beside the bundle or at the project root."""
    project_root = resolve_project_root(deploy_dir)
    candidates = (
        deploy_dir / ".env.example",
        deploy_dir.parent / ".env.example",
        project_root / ".env.example",
    )
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if path.is_file():
            return path
    return None


def seed_dotenv(deploy_dir: Path) -> str:
    """Copy ``.env.example`` → ``.env`` when missing; never overwrite.

    Writes ``.env`` next to the discovered ``.env.example`` (bundle or project
    root). Returns a short status token for logging.
    """
    example = resolve_env_example(deploy_dir)
    if example is None:
        return "missing_example"

    env_path = example.parent / ".env"
    if env_path.exists():
        return "preserved"

    shutil.copy2(example, env_path)
    return "created"


def print_next_steps(
    deploy_dir: Path,
    *,
    skip_venv: bool,
    verify_reserved: bool,
) -> None:
    harness_name = deploy_dir.name
    project_root = resolve_project_root(deploy_dir)
    print()
    print("Next steps:")
    if not skip_venv:
        print("Activate the virtual environment with:")
        print(activation_hint(deploy_dir / VENV_DIRNAME))
    print(
        f"  # From project root ({project_root}) — parent of deploy/<name>/:"
    )
    print(f"  zaumzeug doctor {harness_name} --deploy")
    print(f"  zaumzeug serve {harness_name} --deploy")
    print(
        "  # containers / systemd: HARNESS_ROOT=deploy "
        f"zaumzeug serve {harness_name}"
    )
    if verify_reserved:
        print()
        print(
            "Note: --verify (doctor --deploy + serve --deploy --dry-run) "
            "lands in E5-S09c."
        )


def run_install(
    deploy_dir: Path,
    *,
    skip_venv: bool = False,
    verify: bool = False,
) -> int:
    """Execute the target install workflow. Returns process exit code."""
    require_python_version()

    deploy_dir = deploy_dir.resolve()
    errors = preflight_bundle(deploy_dir)
    if errors:
        for message in errors:
            print(f"error: {message}", file=sys.stderr)
        print(
            "Suggestion: run this script from deploy/<name>/ "
            "(must contain harness.yaml and manifest.json)",
            file=sys.stderr,
        )
        return 1

    print(f"Deploy bundle: {deploy_dir}")
    print(f"Platform: {platform.system()} ({platform.machine()})")
    print(
        "Runtime install: pip install zaumzeug "
        "(no [dev], [eval]; no DSPy, GEPA, or DeepEval)"
    )

    python = resolve_install_python(deploy_dir, skip_venv=skip_venv)
    print(f"Using Python: {python}")

    runtime_pip_install(python, cwd=deploy_dir)
    check_zaumzeug_version(python, cwd=deploy_dir)

    env_status = seed_dotenv(deploy_dir)
    if env_status == "created":
        print(".env: created from .env.example (never overwrites an existing .env)")
    elif env_status == "preserved":
        print(".env: already present (left unchanged)")
    else:
        print(
            ".env.example: not found beside the bundle or project root — "
            "create .env manually with provider API keys (never ship secrets "
            "inside the bundle)"
        )

    print_next_steps(deploy_dir, skip_venv=skip_venv, verify_reserved=verify)
    print("Target install completed successfully.")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        deploy_dir = (args.deploy_dir or Path.cwd()).resolve()
        return run_install(
            deploy_dir,
            skip_venv=args.skip_venv,
            verify=args.verify,
        )
    except TargetInstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
