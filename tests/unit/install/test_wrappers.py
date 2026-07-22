# Story: E1-S02 / E1.2
"""E1-S02 — Install shell wrappers (unit)."""

from __future__ import annotations

import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_DIR = REPO_ROOT / "install"
SH_WRAPPER = INSTALL_DIR / "client-install.sh"
PS1_WRAPPER = INSTALL_DIR / "client-install.ps1"
CLIENT_INSTALL = INSTALL_DIR / "client_install.py"

# Flags from E1-S01 / Architecture §3.4 — must pass through wrappers unchanged.
E1_S01_FLAGS = ("--verify", "--no-example", "--skip-venv", "--cursor-mcp")

# Patterns that would mean install logic was duplicated into a wrapper.
FORBIDDEN_INSTALL_LOGIC = (
    "pip install",
    "venv.create",
    "EnvBuilder",
    "virtualenv",
    "zaumzeug doctor",
    "run_install",
    "editable",
    ".[dev]",
)

_GIT_BASH_CANDIDATES = (
    Path(r"C:\Program Files\Git\bin\bash.exe"),
    Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
)


def _resolve_bash() -> str | None:
    """Prefer Git Bash on Windows; skip WSL ``bash.exe`` (cannot use Win paths)."""
    for candidate in _GIT_BASH_CANDIDATES:
        if candidate.is_file():
            return str(candidate)
    which = shutil.which("bash")
    if which is None:
        return None
    # WSL interop bash under System32 cannot open native Windows paths.
    normalized = which.replace("/", "\\").lower()
    if normalized.endswith(r"system32\bash.exe"):
        return None
    return which


def _stub_client_install(target: Path) -> None:
    """Write a stub that records argv and exits 0."""
    target.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json, sys",
                "from pathlib import Path",
                "out = Path(__file__).resolve().parent / '_wrapper_argv.json'",
                "out.write_text(json.dumps(sys.argv[1:]), encoding='utf-8')",
                "raise SystemExit(0)",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _sandbox_wrappers(tmp_path: Path) -> Path:
    """Copy wrappers into a temp tree with a stub ``client_install.py``."""
    install = tmp_path / "install"
    install.mkdir()
    shutil.copy2(SH_WRAPPER, install / "client-install.sh")
    shutil.copy2(PS1_WRAPPER, install / "client-install.ps1")
    _stub_client_install(install / "client_install.py")
    sh = install / "client-install.sh"
    sh.chmod(sh.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return install


def test_e1_s02_ac1_sh_delegates_to_python(tmp_path: Path) -> None:
    """AC-1: ``install/client-install.sh`` delegates to ``client_install.py`` with forwarded args."""
    assert SH_WRAPPER.is_file(), f"missing wrapper: {SH_WRAPPER}"
    text = SH_WRAPPER.read_text(encoding="utf-8")
    assert "client_install.py" in text
    assert '"$@"' in text, 'bash wrapper must forward all args via "$@"'
    assert "exec" in text
    assert "pip install" not in text.lower()

    bash = _resolve_bash()
    if bash is None:
        pytest.skip("usable bash not on PATH; structural checks above cover AC-1")

    install = _sandbox_wrappers(tmp_path)
    result = subprocess.run(
        [bash, str(install / "client-install.sh"), "--verify", "--skip-venv"],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, f"stderr={result.stderr!r} stdout={result.stdout!r}"
    recorded = (install / "_wrapper_argv.json").read_text(encoding="utf-8")
    assert "--verify" in recorded
    assert "--skip-venv" in recorded


def test_e1_s02_ac2_ps1_delegates_to_python(tmp_path: Path) -> None:
    """AC-2: ``install/client-install.ps1`` delegates to ``client_install.py`` with forwarded args."""
    assert PS1_WRAPPER.is_file(), f"missing wrapper: {PS1_WRAPPER}"
    text = PS1_WRAPPER.read_text(encoding="utf-8")
    assert "client_install.py" in text
    assert "@args" in text, "PowerShell wrapper must forward all args via @args"
    assert "Get-Command" in text
    assert "pip install" not in text.lower()

    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell not on PATH; structural checks above cover AC-2")

    install = _sandbox_wrappers(tmp_path)
    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(install / "client-install.ps1"),
            "--verify",
            "--skip-venv",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, f"stderr={result.stderr!r} stdout={result.stdout!r}"
    recorded = (install / "_wrapper_argv.json").read_text(encoding="utf-8")
    assert "--verify" in recorded
    assert "--skip-venv" in recorded


def test_e1_s02_ac3_flags_forwarded(tmp_path: Path) -> None:
    """AC-3: All flags from E1-S01 pass through wrappers unchanged."""
    sh_text = SH_WRAPPER.read_text(encoding="utf-8")
    ps1_text = PS1_WRAPPER.read_text(encoding="utf-8")
    assert '"$@"' in sh_text
    assert "@args" in ps1_text
    # Wrappers must not filter or rename any known E1-S01 flag.
    for flag in E1_S01_FLAGS:
        assert flag not in sh_text, f"wrapper must not hardcode flag {flag}"
        assert flag not in ps1_text, f"wrapper must not hardcode flag {flag}"

    install = _sandbox_wrappers(tmp_path)
    ran = False

    bash = _resolve_bash()
    if bash is not None:
        result = subprocess.run(
            [bash, str(install / "client-install.sh"), *E1_S01_FLAGS],
            check=False,
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        argv = (install / "_wrapper_argv.json").read_text(encoding="utf-8")
        for flag in E1_S01_FLAGS:
            assert flag in argv
        ran = True
        (install / "_wrapper_argv.json").unlink(missing_ok=True)

    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is not None:
        result = subprocess.run(
            [
                shell,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(install / "client-install.ps1"),
                *E1_S01_FLAGS,
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        argv = (install / "_wrapper_argv.json").read_text(encoding="utf-8")
        for flag in E1_S01_FLAGS:
            assert flag in argv
        ran = True

    if not ran:
        pytest.skip("neither bash nor PowerShell available for flag-forward runtime check")

    # Python entrypoint still accepts the same flags (E1-S01 contract).
    help_result = subprocess.run(
        [sys.executable, str(CLIENT_INSTALL), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert help_result.returncode == 0
    help_text = help_result.stdout + help_result.stderr
    for flag in E1_S01_FLAGS:
        assert flag in help_text


def test_e1_s02_ac4_no_duplicated_install_logic() -> None:
    """AC-4: Wrappers contain no duplicated install logic."""
    for path in (SH_WRAPPER, PS1_WRAPPER):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for needle in FORBIDDEN_INSTALL_LOGIC:
            assert needle.lower() not in lower, (
                f"{path.name} must not contain install logic {needle!r}; "
                "delegate to client_install.py only"
            )
        assert text.count("client_install.py") >= 1
        non_comment_lines = [
            line
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert len(non_comment_lines) <= 25, (
            f"{path.name} looks too large for a thin wrapper "
            f"({len(non_comment_lines)} non-comment lines)"
        )
