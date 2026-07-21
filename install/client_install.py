#!/usr/bin/env python3
"""Cross-platform client install for ZaumZeug (E1-S01 / E1.1).

Creates a project ``.venv`` (unless ``--skip-venv``), runs an editable
``[dev]`` pip install, optionally scaffolds (E1-S03), and can run
``zaumzeug doctor`` via ``--verify``.
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
EDITABLE_DEV_SPEC = ".[dev]"


class ClientInstallError(Exception):
    """Fatal install failure with an actionable message."""


def discover_project_root() -> Path:
    """Return the repository root (parent of the ``install`` package dir)."""
    return Path(__file__).resolve().parent.parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="client_install.py",
        description=(
            "Create a project .venv (unless --skip-venv), install "
            'zaumzeug editable with "[dev]", and optionally verify.'
        ),
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="run `zaumzeug doctor` after a successful install",
    )
    parser.add_argument(
        "--no-example",
        action="store_true",
        help="skip copying the example harness during scaffolding (E1-S03)",
    )
    parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="do not create .venv; use the current Python for pip and doctor (CI)",
    )
    parser.add_argument(
        "--cursor-mcp",
        action="store_true",
        help="opt-in write of Cursor MCP config (E7-S03; accepted here)",
    )
    return parser.parse_args(argv)


def require_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        major, minor = MIN_PYTHON
        current = f"{sys.version_info.major}.{sys.version_info.minor}"
        raise ClientInstallError(
            f"Python {major}.{minor}+ is required; found {current}. "
            f"Install Python {major}.{minor} or newer and re-run."
        )


def warn_if_git_missing(*, stream=sys.stderr) -> None:
    """Non-blocking warning when ``git`` is not on PATH."""
    if shutil.which("git") is None:
        print(
            "warning: git was not found on PATH. "
            "Clone and update workflows and some doctor checks may be limited.",
            file=stream,
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
    """Run a subprocess; raise ClientInstallError on failure."""
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
        raise ClientInstallError(
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
        raise ClientInstallError(
            f"{what} failed with exit code {completed.returncode}. "
            f"Command: {' '.join(cmd)}"
        )


def editable_dev_install(project_root: Path, python: Path) -> None:
    """Run ``python -m pip install -e ".[dev]"`` in ``project_root``."""
    pyproject = project_root / "pyproject.toml"
    if not pyproject.is_file():
        raise ClientInstallError(
            f"Missing {pyproject}. Run this script from a ZaumZeug repo clone."
        )
    run_command(
        [str(python), "-m", "pip", "install", "-e", EDITABLE_DEV_SPEC],
        cwd=project_root,
        what='Editable install (pip install -e ".[dev]")',
    )


def run_doctor(project_root: Path, python: Path) -> int:
    """Invoke ``zaumzeug doctor`` via the install Python. Returns exit code."""
    cmd = [str(python), "-m", "zaumzeug", "doctor"]
    print(f"$ {' '.join(cmd)}")
    try:
        completed = subprocess.run(
            cmd,
            cwd=project_root,
            check=False,
        )
    except OSError as exc:
        raise ClientInstallError(
            f"zaumzeug doctor failed to start: {exc}. "
            "Confirm the editable install succeeded."
        ) from exc
    return int(completed.returncode)


def scaffold_project(
    project_root: Path,
    *,
    no_example: bool,
    cursor_mcp: bool,
) -> None:
    """Scaffold project files (idempotent).

    Full copy rules land in E1-S03; ``--cursor-mcp`` live write in E7-S03.
    E1-S01 accepts the flags and provides this extension point so re-runs
    remain safe when scaffolding is wired later.
    """
    _ = (project_root, no_example, cursor_mcp)


def resolve_install_python(
    project_root: Path,
    *,
    skip_venv: bool,
) -> Path:
    """Return the Python used for pip/doctor; create ``.venv`` unless skipped."""
    if skip_venv:
        print("Skipping .venv creation (--skip-venv); using current Python.")
        return Path(sys.executable)

    venv_dir = project_root / VENV_DIRNAME
    created = ensure_venv(venv_dir)
    python = venv_python(venv_dir)
    if not python.is_file():
        raise ClientInstallError(
            f"Expected venv Python at {python} after "
            f"{'creating' if created else 'locating'} {venv_dir}."
        )
    return python


def run_install(
    project_root: Path,
    *,
    skip_venv: bool = False,
    verify: bool = False,
    no_example: bool = False,
    cursor_mcp: bool = False,
) -> int:
    """Execute the client install workflow. Returns process exit code."""
    require_python_version()
    warn_if_git_missing()

    project_root = project_root.resolve()
    print(f"Project root: {project_root}")
    print(f"Platform: {platform.system()} ({platform.machine()})")

    python = resolve_install_python(project_root, skip_venv=skip_venv)
    print(f"Using Python: {python}")

    editable_dev_install(project_root, python)
    scaffold_project(
        project_root,
        no_example=no_example,
        cursor_mcp=cursor_mcp,
    )

    if not skip_venv:
        venv_dir = project_root / VENV_DIRNAME
        print("Activate the virtual environment with:")
        print(activation_hint(venv_dir))

    if verify:
        print("Running zaumzeug doctor (--verify) …")
        doctor_code = run_doctor(project_root, python)
        if doctor_code != 0:
            print(
                f"zaumzeug doctor exited with code {doctor_code}.",
                file=sys.stderr,
            )
            return doctor_code

    print("Client install completed successfully.")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        return run_install(
            discover_project_root(),
            skip_venv=args.skip_venv,
            verify=args.verify,
            no_example=args.no_example,
            cursor_mcp=args.cursor_mcp,
        )
    except ClientInstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
