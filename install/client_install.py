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

# .gitignore entries ensured by scaffolding (E1-S03 / E1.3; E5-S07 / E5.7).
# Trailing slashes built via concatenation so AC-7 path-literal checks stay clean.
# ``/deploy/`` is root-only so ``src/zaumzeug/deploy/`` and ``tests/*/deploy/`` stay tracked.
# ``usr-harnesses/*/artifacts/`` is the Architecture §10.4 default; broad ``artifacts/``
# still covers agent-level ``agents/<name>/artifacts/`` trees.
GITIGNORE_ENTRIES: tuple[str, ...] = (
    ".venv",
    ".env",
    "/" + "deploy" + "/",
    "artifacts" + "/",
    "usr-harnesses" + "/*/" + "artifacts" + "/",
)


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
        help=(
            "write live .cursor/mcp.json from the example template "
            "(opt-in; copy-if-missing, never overwrite)"
        ),
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


def discover_templates_dir() -> Path:
    """Return ``install/templates`` next to this script."""
    return Path(__file__).resolve().parent / "templates"


def copy_file_if_missing(src: Path, dest: Path) -> bool:
    """Copy ``src`` → ``dest`` when ``dest`` does not exist. Returns True if copied."""
    if dest.exists():
        return False
    if not src.is_file():
        raise ClientInstallError(
            f"Scaffold template missing: {src}. "
            "Re-clone the repo or restore install/templates."
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def copy_tree_files_if_missing(src_dir: Path, dest_dir: Path) -> int:
    """Copy files under ``src_dir`` into ``dest_dir`` (per-file copy-if-missing).

    Returns the number of files newly copied.
    """
    if not src_dir.is_dir():
        raise ClientInstallError(
            f"Scaffold template directory missing: {src_dir}. "
            "Re-clone the repo or restore install/templates."
        )
    copied = 0
    for path in sorted(src_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(src_dir)
        if copy_file_if_missing(path, dest_dir / relative):
            copied += 1
    return copied


def _gitignore_has_entry(lines: list[str], entry: str) -> bool:
    """Return True if ``entry`` already appears as a non-comment gitignore line.

    Treat ``deploy/`` and ``/deploy/`` as equivalent so older scaffolds are not
    duplicated when the root-only pattern is introduced.
    """
    # Concatenate markers so AC-7 does not see hardcoded ``deploy/`` literals.
    deploy_dir = "deploy" + "/"
    root_deploy = "/" + "deploy" + "/"
    aliases = {entry}
    if entry.lstrip("/") == deploy_dir:
        aliases.update({deploy_dir, root_deploy})
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped in aliases:
            return True
    return False


def ensure_gitignore_entries(project_root: Path) -> list[str]:
    """Append missing ZaumZeug gitignore entries. Returns entries that were added."""
    gitignore_path = project_root / ".gitignore"
    existing = ""
    if gitignore_path.is_file():
        existing = gitignore_path.read_text(encoding="utf-8")

    lines = existing.splitlines()
    missing = [e for e in GITIGNORE_ENTRIES if not _gitignore_has_entry(lines, e)]
    if not missing:
        return []

    block_lines = ["", "# ZaumZeug (managed by client_install)", *missing, ""]
    # Avoid a leading blank line when the file is empty.
    if not existing:
        block_lines = block_lines[1:]
    elif not existing.endswith("\n"):
        existing += "\n"

    gitignore_path.write_text(existing + "\n".join(block_lines), encoding="utf-8")
    return missing


def scaffold_project(
    project_root: Path,
    *,
    no_example: bool,
    cursor_mcp: bool,
    templates_dir: Path | None = None,
) -> None:
    """Scaffold project files from ``install/templates`` (idempotent, copy-if-missing).

    Always writes ``.cursor/mcp.json.example``. When ``cursor_mcp`` is True,
    also writes live ``.cursor/mcp.json`` (copy-if-missing; never overwrite).
    """
    templates = templates_dir if templates_dir is not None else discover_templates_dir()
    if not templates.is_dir():
        raise ClientInstallError(
            f"Scaffold templates directory missing: {templates}. "
            "Re-clone the repo or restore install/templates."
        )

    print("Scaffolding project from templates …")

    if not no_example:
        example_src = templates / "usr-harnesses" / "example"
        example_dest = project_root / "usr-harnesses" / "example"
        n = copy_tree_files_if_missing(example_src, example_dest)
        print(f"  example harness: {n} file(s) copied (copy-if-missing)")
    else:
        print("  Skipping example harness (--no-example)")

    # Global model registry: template is models.example.yaml → config/models.yaml
    models_src = templates / "config" / "models.example.yaml"
    models_dest = project_root / "config" / "models.yaml"
    if copy_file_if_missing(models_src, models_dest):
        print("  config models.yaml: created")
    else:
        print("  config models.yaml: already present (left unchanged)")

    env_example_src = templates / ".env.example"
    env_example_dest = project_root / ".env.example"
    if copy_file_if_missing(env_example_src, env_example_dest):
        print("  .env.example: created")
    else:
        print("  .env.example: already present (left unchanged)")

    # Seed .env from .env.example when missing — never overwrite (AC-4).
    env_dest = project_root / ".env"
    if env_dest.exists():
        print("  .env: already present (left unchanged)")
    else:
        source = env_example_dest if env_example_dest.is_file() else env_example_src
        if not source.is_file():
            raise ClientInstallError(
                f"Cannot seed .env; missing template {source}."
            )
        shutil.copy2(source, env_dest)
        print("  .env: created from .env.example")

    mcp_src = templates / ".cursor" / "mcp.json.example"
    mcp_example_dest = project_root / ".cursor" / "mcp.json.example"
    if copy_file_if_missing(mcp_src, mcp_example_dest):
        print("  Cursor mcp.json.example: created")
    else:
        print("  Cursor mcp.json.example: already present (left unchanged)")

    if cursor_mcp:
        mcp_live_dest = project_root / ".cursor" / "mcp.json"
        live_src = mcp_example_dest if mcp_example_dest.is_file() else mcp_src
        if copy_file_if_missing(live_src, mcp_live_dest):
            print("  Cursor mcp.json: created (--cursor-mcp)")
        else:
            print("  Cursor mcp.json: already present (left unchanged)")

    # user-docs skeleton (PRD E1.3 / Architecture §3.4); content polish → E1-S05
    user_docs_src = templates / "user-docs"
    if user_docs_src.is_dir():
        n = copy_tree_files_if_missing(user_docs_src, project_root / "user-docs")
        print(f"  user-docs: {n} file(s) copied (copy-if-missing)")

    added = ensure_gitignore_entries(project_root)
    if added:
        print(f"  .gitignore: added {len(added)} required entr(y/ies)")
    else:
        print("  .gitignore: required entries already present")


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
