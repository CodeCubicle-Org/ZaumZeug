# Story: E1-S01 / E1.1
# Story: E7-S03 / E7.3
"""E1-S01 — Cross-platform install script (unit); E7-S03 --cursor-mcp live write."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CLIENT_INSTALL_PATH = REPO_ROOT / "install" / "client_install.py"


def _load_client_install() -> ModuleType:
    """Load ``install/client_install.py`` without requiring ``install`` as a package."""
    spec = importlib.util.spec_from_file_location(
        "zaumzeug_client_install",
        CLIENT_INSTALL_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def client_install() -> ModuleType:
    return _load_client_install()


def _fake_completed(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> Any:
    class _Result:
        def __init__(self) -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    return _Result()


def test_e1_s01_ac2_creates_venv_when_missing(
    client_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: Creates project ``.venv`` when not present (unless ``--skip-venv``)."""
    created: list[Path] = []

    class FakeBuilder:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def create(self, env_dir: str | Path) -> None:
            path = Path(env_dir)
            created.append(path)
            scripts = path / ("Scripts" if client_install.is_windows() else "bin")
            scripts.mkdir(parents=True)
            python_name = "python.exe" if client_install.is_windows() else "python"
            (scripts / python_name).write_text("", encoding="utf-8")

    monkeypatch.setattr(client_install.venv, "EnvBuilder", FakeBuilder)
    monkeypatch.setattr(
        client_install.subprocess,
        "run",
        lambda *_a, **_k: _fake_completed(),
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='zaumzeug'\n", encoding="utf-8")

    code = client_install.run_install(tmp_path, skip_venv=False)
    assert code == 0
    assert created == [tmp_path / ".venv"]
    assert (tmp_path / ".venv").exists()

    # --skip-venv must not create .venv
    other = tmp_path / "skip"
    other.mkdir()
    (other / "pyproject.toml").write_text("[project]\nname='zaumzeug'\n", encoding="utf-8")
    created.clear()
    code = client_install.run_install(other, skip_venv=True)
    assert code == 0
    assert created == []
    assert not (other / ".venv").exists()


def test_e1_s01_ac3_editable_dev_install(
    client_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: Runs ``pip install -e ".[dev]"`` successfully."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        calls.append(list(cmd))
        return _fake_completed()

    monkeypatch.setattr(client_install.subprocess, "run", fake_run)
    monkeypatch.setattr(
        client_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='zaumzeug'\n", encoding="utf-8")

    code = client_install.run_install(tmp_path, skip_venv=True)
    assert code == 0
    assert calls, "expected at least one subprocess call"
    pip_cmd = calls[0]
    assert pip_cmd[-5:] == [
        "-m",
        "pip",
        "install",
        "-e",
        client_install.EDITABLE_DEV_SPEC,
    ]
    assert client_install.EDITABLE_DEV_SPEC == ".[dev]"


def test_e1_s01_ac4_idempotent_rerun(
    client_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: Re-running the script is idempotent (no broken state)."""
    create_count = {"n": 0}

    class FakeBuilder:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def create(self, env_dir: str | Path) -> None:
            create_count["n"] += 1
            path = Path(env_dir)
            scripts = path / ("Scripts" if client_install.is_windows() else "bin")
            scripts.mkdir(parents=True)
            python_name = "python.exe" if client_install.is_windows() else "python"
            (scripts / python_name).write_text("", encoding="utf-8")

    monkeypatch.setattr(client_install.venv, "EnvBuilder", FakeBuilder)
    monkeypatch.setattr(
        client_install.subprocess,
        "run",
        lambda *_a, **_k: _fake_completed(),
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='zaumzeug'\n", encoding="utf-8")

    assert client_install.run_install(tmp_path) == 0
    assert create_count["n"] == 1
    assert client_install.run_install(tmp_path) == 0
    assert create_count["n"] == 1  # existing .venv is reused


def test_e1_s01_ac5_cli_flags_parsed(client_install: ModuleType) -> None:
    """AC-5: Supports ``--verify``, ``--no-example``, ``--skip-venv``, ``--cursor-mcp``."""
    args = client_install.parse_args(
        ["--verify", "--no-example", "--skip-venv", "--cursor-mcp"]
    )
    assert args.verify is True
    assert args.no_example is True
    assert args.skip_venv is True
    assert args.cursor_mcp is True

    defaults = client_install.parse_args([])
    assert defaults.verify is False
    assert defaults.no_example is False
    assert defaults.skip_venv is False
    assert defaults.cursor_mcp is False


def test_e1_s01_ac6_verify_invokes_doctor(
    client_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-6: ``--verify`` runs ``zaumzeug doctor`` after install."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        calls.append(list(cmd))
        return _fake_completed(returncode=0)

    monkeypatch.setattr(client_install.subprocess, "run", fake_run)
    monkeypatch.setattr(
        client_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='zaumzeug'\n", encoding="utf-8")

    code = client_install.run_install(tmp_path, skip_venv=True, verify=True)
    assert code == 0
    doctor_calls = [c for c in calls if c[-2:] == ["zaumzeug", "doctor"]]
    assert len(doctor_calls) == 1
    assert doctor_calls[0][-3:] == ["-m", "zaumzeug", "doctor"]

    # Doctor failure propagates as non-zero exit
    calls.clear()

    def failing_run(cmd: list[str], **kwargs: Any) -> Any:
        calls.append(list(cmd))
        if cmd[-1] == "doctor":
            return _fake_completed(returncode=2)
        return _fake_completed(returncode=0)

    monkeypatch.setattr(client_install.subprocess, "run", failing_run)
    code = client_install.run_install(tmp_path, skip_venv=True, verify=True)
    assert code == 2


def test_e1_s01_ac7_pathlib_no_hardcoded_separators(client_install: ModuleType) -> None:
    """AC-7: Uses pathlib only — no hardcoded OS path separators for paths."""
    source = CLIENT_INSTALL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Docstrings are documentation; enforce non-docstring string literals only.
    docstring_nodes: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstring_nodes.add(node.body[0].value)

    # Architecture §2.5: no `/` or `\` literals for harness roots, venv, or artifacts.
    path_markers = (
        ".venv",
        "Scripts",
        "bin",
        "usr-harnesses",
        "artifacts",
        "deploy",
        "pyproject.toml",
        "Activate",
        "python.exe",
    )
    offenders: list[str] = []
    for node in ast.walk(tree):
        if node in docstring_nodes:
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if ("/" in value or "\\" in value) and any(m in value for m in path_markers):
                offenders.append(value)

    assert offenders == [], (
        "Hardcoded path separators found in install script path literals: "
        f"{offenders!r}. Use pathlib.Path parts instead (Architecture §2.5)."
    )
    assert "Path" in dir(client_install)


def test_e7_s03_ac3_cursor_mcp_flag_writes_json(
    client_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3 (E7-S03): ``--cursor-mcp`` writes live ``.cursor/mcp.json`` (opt-in)."""
    monkeypatch.setattr(
        client_install.subprocess,
        "run",
        lambda *_a, **_k: _fake_completed(),
    )
    monkeypatch.setattr(
        client_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )

    without_flag = tmp_path / "without"
    without_flag.mkdir()
    (without_flag / "pyproject.toml").write_text(
        "[project]\nname='zaumzeug'\n", encoding="utf-8"
    )
    assert client_install.run_install(without_flag, skip_venv=True, cursor_mcp=False) == 0
    assert (without_flag / ".cursor" / "mcp.json.example").is_file()
    assert not (without_flag / ".cursor" / "mcp.json").exists()

    with_flag = tmp_path / "with-flag"
    with_flag.mkdir()
    (with_flag / "pyproject.toml").write_text(
        "[project]\nname='zaumzeug'\n", encoding="utf-8"
    )
    assert client_install.run_install(with_flag, skip_venv=True, cursor_mcp=True) == 0
    live = with_flag / ".cursor" / "mcp.json"
    example = with_flag / ".cursor" / "mcp.json.example"
    assert live.is_file()
    assert example.is_file()
    live_text = live.read_text(encoding="utf-8")
    assert "http://localhost:1417/mcp" in live_text
    assert live_text == example.read_text(encoding="utf-8")

    custom = '{"mcpServers": {"custom": {"url": "http://localhost:9999/mcp"}}}\n'
    live.write_text(custom, encoding="utf-8")
    assert client_install.run_install(with_flag, skip_venv=True, cursor_mcp=True) == 0
    assert live.read_text(encoding="utf-8") == custom
