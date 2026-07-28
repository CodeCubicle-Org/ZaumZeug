# Story: E5-S05 / E5.5 · E5-S09a / E5.9 · E5-S09b / E5.9 · E5-S09c / E5.9
"""E5-S05 / E5-S09a / E5-S09b / E5-S09c — Target ship, install, wrappers, verify."""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import re
import shutil
import stat
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from zaumzeug.deploy.packager import package_harness
from zaumzeug.doctor.report import CheckResult, DoctorReport

from tests.integration.deploy.test_deploy import _seed_deploy_harness

REPO_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT = REPO_ROOT / "pyproject.toml"
INSTALL_DIR = REPO_ROOT / "install"
TARGET_INSTALL = INSTALL_DIR / "target_install.py"
TARGET_SH_WRAPPER = INSTALL_DIR / "target-install.sh"
TARGET_PS1_WRAPPER = INSTALL_DIR / "target-install.ps1"
README_DEPLOY_TEMPLATE = (
    REPO_ROOT / "install" / "templates" / "deploy" / "README.deploy.md"
)
SHIP_GUIDE = REPO_ROOT / "user-docs" / "guides" / "deploy.md"

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
    normalized = which.replace("/", "\\").lower()
    if normalized.endswith(r"system32\bash.exe"):
        return None
    return which


def _stub_target_install(target: Path, *, exit_code: int = 0) -> None:
    """Write a stub that records argv and exits with ``exit_code``."""
    target.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json, sys",
                "from pathlib import Path",
                "out = Path(__file__).resolve().parent / '_wrapper_argv.json'",
                "out.write_text(json.dumps(sys.argv[1:]), encoding='utf-8')",
                f"raise SystemExit({exit_code})",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _sandbox_target_wrappers(tmp_path: Path, *, exit_code: int = 0) -> Path:
    """Copy target wrappers into a temp dir with a stub ``target_install.py``."""
    sandbox = tmp_path / "bundle"
    sandbox.mkdir(parents=True)
    shutil.copy2(TARGET_SH_WRAPPER, sandbox / "target-install.sh")
    shutil.copy2(TARGET_PS1_WRAPPER, sandbox / "target-install.ps1")
    _stub_target_install(sandbox / "target_install.py", exit_code=exit_code)
    sh = sandbox / "target-install.sh"
    sh.chmod(sh.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return sandbox


def _load_target_install() -> ModuleType:
    """Load ``install/target_install.py`` without requiring ``install`` as a package."""
    spec = importlib.util.spec_from_file_location(
        "zaumzeug_target_install",
        TARGET_INSTALL,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def target_install() -> ModuleType:
    return _load_target_install()


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


def _seed_minimal_bundle(deploy_dir: Path) -> None:
    """Write the minimum files ``preflight_bundle`` requires."""
    deploy_dir.mkdir(parents=True, exist_ok=True)
    (deploy_dir / "harness.yaml").write_text("name: example\n", encoding="utf-8")
    (deploy_dir / "manifest.json").write_text("{}\n", encoding="utf-8")


def _fake_venv_builder(module: ModuleType) -> type:
    class FakeBuilder:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def create(self, env_dir: str | Path) -> None:
            path = Path(env_dir)
            scripts = path / ("Scripts" if module.is_windows() else "bin")
            scripts.mkdir(parents=True)
            python_name = "python.exe" if module.is_windows() else "python"
            (scripts / python_name).write_text("", encoding="utf-8")

    return FakeBuilder


FORBIDDEN_RUNTIME_PACKAGES = frozenset(
    {
        "dspy",
        "dspy-ai",
        "gepa",
        "deepeval",
    }
)


def _dep_name(spec: str) -> str:
    for sep in ("[", ">", "<", "=", "!", " ", ";"):
        if sep in spec:
            return spec.split(sep, 1)[0].strip().lower()
    return spec.strip().lower()


def _ok_doctor(**kwargs) -> DoctorReport:  # noqa: ANN003
    del kwargs
    return DoctorReport(
        checks=[
            CheckResult(name="preflight", severity="pass", message="ok"),
        ]
    )


def test_e5_s05_ac2_runtime_only_install() -> None:
    """AC-2: Target installs runtime deps only (``pip install zaumzeug``)."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    runtime_names = {_dep_name(dep) for dep in project["dependencies"]}
    leaked = FORBIDDEN_RUNTIME_PACKAGES & runtime_names
    assert not leaked, f"core install must not include: {sorted(leaked)}"

    assert "haystack-ai" in runtime_names
    assert "hayhooks" in runtime_names
    extras = project["optional-dependencies"]
    assert "dspy-ai" in {_dep_name(d) for d in extras["dev"]}
    assert "gepa" in {_dep_name(d) for d in extras["dev"]}
    assert "deepeval" in {_dep_name(d) for d in extras["eval"]}

    script = TARGET_INSTALL.read_text(encoding="utf-8")
    assert "pip install zaumzeug" in script
    assert re.search(r"pip install zaumzeug\[(dev|eval)\]", script) is None
    assert "no [dev]" in script.lower() or "runtime only" in script.lower()

    readme = README_DEPLOY_TEMPLATE.read_text(encoding="utf-8")
    assert "pip install zaumzeug" in readme
    assert "runtime only" in readme.lower()
    assert "Ship workflow" in readme

    guide = SHIP_GUIDE.read_text(encoding="utf-8")
    assert "pip install zaumzeug" in guide
    assert "runtime only" in guide.lower()


def test_e5_s05_ac3_no_dspy_gepa_deepeval() -> None:
    """AC-3: No DSPy, GEPA, or DeepEval on production server by default."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    runtime_names = {_dep_name(dep) for dep in project["dependencies"]}
    for name in ("dspy-ai", "dspy", "gepa", "deepeval"):
        assert name not in runtime_names

    for path in (TARGET_INSTALL, README_DEPLOY_TEMPLATE, SHIP_GUIDE):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        assert "dspy" in lower, f"{path.name} should mention DSPy"
        assert "gepa" in lower, f"{path.name} should mention GEPA"
        assert "deepeval" in lower, f"{path.name} should mention DeepEval"
        # Docs must state these stay off the default production path.
        asserts_absence = (
            "no dspy" in lower
            or "no [dev]" in lower
            or "**no**" in lower
            or "not installed by default" in lower
            or "compile on" in lower
            or "dev/ci" in lower
            or "dev / ci" in lower
            or ("never" in lower and ("dspy" in lower or "gepa" in lower))
        )
        assert asserts_absence, (
            f"{path.name} must document that DSPy/GEPA/DeepEval stay off the target"
        )


def test_e5_s05_docs_ship_workflow_steps() -> None:
    """AC-1 / AC-4 (docs): ship path + Python 3.11+ prerequisite are documented."""
    readme = README_DEPLOY_TEMPLATE.read_text(encoding="utf-8")
    guide = SHIP_GUIDE.read_text(encoding="utf-8")

    for text in (readme, guide):
        assert "3.11" in text
        assert "target-install.ps1" in text
        assert "target-install.sh" in text
        assert ".env" in text
        assert "zaumzeug serve" in text
        assert "--deploy" in text
        assert "Windows" in text and "Linux" in text and "macOS" in text


def test_e5_s05_bundled_readme_renders_ship_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Packaged README.deploy.md retains the ship workflow after deploy."""
    monkeypatch.chdir(tmp_path)
    _seed_deploy_harness(tmp_path)

    result = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert result.bundle_dir is not None
    readme = (result.bundle_dir / "README.deploy.md").read_text(encoding="utf-8")
    assert "Ship workflow" in readme
    assert "example" in readme
    assert "pip install zaumzeug" in readme
    assert "3.11" in readme
    assert ".env" in readme
    assert "never" in readme.lower()
    assert "target-install.ps1" in readme
    assert "target-install.sh" in readme


# --- E5-S09a / E5.9 — target_install core ---------------------------------


def test_e5_s09_ac1_runs_on_linux(target_install: ModuleType) -> None:
    """AC-1: ``target_install.py`` is Linux-capable (OS-neutral pathlib, no hard-coded seps)."""
    source = TARGET_INSTALL.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Must be a plain script runnable with ``python target_install.py`` on Linux.
    assert source.startswith("#!/usr/bin/env python3")
    assert "from pathlib import Path" in source
    assert 'venv_dir / "bin"' in source  # POSIX venv layout
    assert "Scripts" in source  # Windows layout also supported

    # No hard-coded OS path separators in string literals (same rule as E1-S01).
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if "\\" in value and not value.startswith("\\"):
                # Allow escaped newlines / regex-ish text, not Windows paths.
                assert "\\\\" in value or value.count("\\") == value.count("\\n"), (
                    f"suspicious backslash string at line {node.lineno}: {value!r}"
                )

    assert callable(target_install.preflight_bundle)
    assert callable(target_install.run_install)
    assert target_install.RUNTIME_PIP_SPEC == "zaumzeug"
    assert target_install.MIN_PYTHON == (3, 11)


def test_e5_s09_ac2_optional_venv(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: Assumes Python 3.11+; creates optional ``.venv`` beside the bundle."""
    created: list[Path] = []
    FakeBuilder = _fake_venv_builder(target_install)

    class TrackingBuilder(FakeBuilder):  # type: ignore[valid-type,misc]
        def create(self, env_dir: str | Path) -> None:
            created.append(Path(env_dir))
            super().create(env_dir)

    monkeypatch.setattr(target_install.venv, "EnvBuilder", TrackingBuilder)
    monkeypatch.setattr(
        target_install.subprocess,
        "run",
        lambda *_a, **_k: _fake_completed(stdout="zaumzeug 0.1.0\n"),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)

    code = target_install.run_install(deploy_dir, skip_venv=False)
    assert code == 0
    assert created == [deploy_dir / ".venv"]
    assert (deploy_dir / ".venv").exists()

    # --skip-venv must not create .venv
    other = tmp_path / "deploy" / "skip"
    _seed_minimal_bundle(other)
    created.clear()
    code = target_install.run_install(other, skip_venv=True)
    assert code == 0
    assert created == []
    assert not (other / ".venv").exists()


def test_e5_s09_ac3_runtime_only_pip_install(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: ``pip install zaumzeug`` runtime only — no ``[dev]``, ``[eval]``, DSPy, GEPA."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: Any) -> Any:
        calls.append(list(cmd))
        return _fake_completed(stdout="ok\n")

    monkeypatch.setattr(target_install.subprocess, "run", fake_run)
    monkeypatch.setattr(
        target_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)

    code = target_install.run_install(deploy_dir, skip_venv=True)
    assert code == 0
    assert calls, "expected pip / version subprocess calls"

    pip_cmds = [c for c in calls if "pip" in c]
    assert pip_cmds, f"expected a pip install call; got {calls}"
    pip_cmd = pip_cmds[0]
    assert pip_cmd[-4:] == ["-m", "pip", "install", "zaumzeug"]
    joined = " ".join(pip_cmd)
    assert "[dev]" not in joined
    assert "[eval]" not in joined
    assert "dspy" not in joined.lower()
    assert "gepa" not in joined.lower()
    assert "deepeval" not in joined.lower()
    assert target_install.RUNTIME_PIP_SPEC == "zaumzeug"


def test_e5_s09_ac5_env_example_copy_preserves_existing(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: Copies ``.env.example`` → ``.env`` if missing; never overwrites ``.env``."""
    monkeypatch.setattr(
        target_install.subprocess,
        "run",
        lambda *_a, **_k: _fake_completed(),
    )
    monkeypatch.setattr(
        target_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)

    # Prefer project-root ``.env.example`` (parent of deploy/<name>/).
    project_root = tmp_path
    example = project_root / ".env.example"
    example.write_text("OPENAI_API_KEY=replace-me\n", encoding="utf-8")

    code = target_install.run_install(deploy_dir, skip_venv=True)
    assert code == 0
    env_path = project_root / ".env"
    assert env_path.is_file()
    assert env_path.read_text(encoding="utf-8") == "OPENAI_API_KEY=replace-me\n"

    # Existing .env must never be overwritten.
    env_path.write_text("OPENAI_API_KEY=keep-me\n", encoding="utf-8")
    example.write_text("OPENAI_API_KEY=should-not-land\n", encoding="utf-8")
    code = target_install.run_install(deploy_dir, skip_venv=True)
    assert code == 0
    assert env_path.read_text(encoding="utf-8") == "OPENAI_API_KEY=keep-me\n"


def test_e5_s09_ac8_idempotent_rerun(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-5: Idempotent re-run (reuse existing ``.venv``; no broken state)."""
    create_count = {"n": 0}
    FakeBuilder = _fake_venv_builder(target_install)

    class CountingBuilder(FakeBuilder):  # type: ignore[valid-type,misc]
        def create(self, env_dir: str | Path) -> None:
            create_count["n"] += 1
            super().create(env_dir)

    monkeypatch.setattr(target_install.venv, "EnvBuilder", CountingBuilder)
    monkeypatch.setattr(
        target_install.subprocess,
        "run",
        lambda *_a, **_k: _fake_completed(),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)
    (tmp_path / ".env.example").write_text("KEY=1\n", encoding="utf-8")

    assert target_install.run_install(deploy_dir) == 0
    assert create_count["n"] == 1
    assert (tmp_path / ".env").is_file()

    assert target_install.run_install(deploy_dir) == 0
    assert create_count["n"] == 1  # existing .venv reused
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "KEY=1\n"


def test_e5_s09a_preflight_requires_manifest_and_harness(
    target_install: ModuleType,
    tmp_path: Path,
) -> None:
    """Build task: preflight verifies deploy ``manifest.json`` + ``harness.yaml``."""
    empty = tmp_path / "deploy" / "empty"
    empty.mkdir(parents=True)
    errors = target_install.preflight_bundle(empty)
    assert any("harness.yaml" in e for e in errors)
    assert any("manifest.json" in e for e in errors)

    _seed_minimal_bundle(empty)
    assert target_install.preflight_bundle(empty) == []

    code = target_install.main(["--deploy-dir", str(tmp_path / "missing")])
    assert code == 1


# --- E5-S09b / E5.9 — target install shell wrappers -----------------------


def test_e5_s09b_ac1_wrappers_invoke_python(tmp_path: Path) -> None:
    """AC-1: ``target-install.sh`` / ``.ps1`` invoke ``target_install.py`` with forwarded args."""
    assert TARGET_SH_WRAPPER.is_file(), f"missing wrapper: {TARGET_SH_WRAPPER}"
    assert TARGET_PS1_WRAPPER.is_file(), f"missing wrapper: {TARGET_PS1_WRAPPER}"

    sh_text = TARGET_SH_WRAPPER.read_text(encoding="utf-8")
    ps1_text = TARGET_PS1_WRAPPER.read_text(encoding="utf-8")
    assert "target_install.py" in sh_text
    assert "target_install.py" in ps1_text
    assert '"$@"' in sh_text, 'bash wrapper must forward all args via "$@"'
    assert "@args" in ps1_text, "PowerShell wrapper must forward all args via @args"
    assert "pip install" not in sh_text.lower()
    assert "pip install" not in ps1_text.lower()
    # Sibling script path — works under install/ and inside deploy/<name>/.
    assert "${HERE}/target_install.py" in sh_text or 'HERE}/target_install.py' in sh_text
    assert "$PSScriptRoot" in ps1_text
    assert "client_install.py" not in sh_text
    assert "client_install.py" not in ps1_text

    sandbox = _sandbox_target_wrappers(tmp_path)
    forwarded = ("--skip-venv", "--deploy-dir", str(sandbox))
    ran = False

    bash = _resolve_bash()
    if bash is not None:
        result = subprocess.run(
            [bash, str(sandbox / "target-install.sh"), *forwarded],
            check=False,
            capture_output=True,
            text=True,
            cwd=sandbox,
        )
        assert result.returncode == 0, f"stderr={result.stderr!r} stdout={result.stdout!r}"
        argv = json.loads((sandbox / "_wrapper_argv.json").read_text(encoding="utf-8"))
        assert argv == list(forwarded)
        ran = True
        (sandbox / "_wrapper_argv.json").unlink(missing_ok=True)

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
                str(sandbox / "target-install.ps1"),
                *forwarded,
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=sandbox,
        )
        assert result.returncode == 0, f"stderr={result.stderr!r} stdout={result.stdout!r}"
        argv = json.loads((sandbox / "_wrapper_argv.json").read_text(encoding="utf-8"))
        assert argv == list(forwarded)
        ran = True

    if not ran:
        pytest.skip("neither bash nor PowerShell available for wrapper runtime check")


def test_e5_s09b_ac3_wrapper_exit_code_parity(tmp_path: Path) -> None:
    """AC-3: Wrappers return the same exit code as the underlying Python script."""
    for expected in (0, 2, 7):
        sandbox = _sandbox_target_wrappers(tmp_path / f"exit_{expected}", exit_code=expected)
        ran = False

        bash = _resolve_bash()
        if bash is not None:
            result = subprocess.run(
                [bash, str(sandbox / "target-install.sh"), "--skip-venv"],
                check=False,
                capture_output=True,
                text=True,
                cwd=sandbox,
            )
            assert result.returncode == expected, (
                f"bash exit mismatch: got {result.returncode}, want {expected}; "
                f"stderr={result.stderr!r}"
            )
            ran = True

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
                    str(sandbox / "target-install.ps1"),
                    "--skip-venv",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=sandbox,
            )
            assert result.returncode == expected, (
                f"ps1 exit mismatch: got {result.returncode}, want {expected}; "
                f"stderr={result.stderr!r}"
            )
            ran = True

        if not ran:
            pytest.skip("neither bash nor PowerShell available for exit-code parity check")


# --- E5-S09c / E5.9 — target install --verify -----------------------------


def _zaumzeug_cli_cmds(calls: list[list[str]]) -> list[list[str]]:
    """Return subprocess argv lists that invoke ``-m zaumzeug <subcommand>``."""
    return [
        c
        for c in calls
        if "-m" in c and "zaumzeug" in c and len(c) > c.index("zaumzeug") + 1
    ]


def test_e5_s09_ac4_verify_runs_doctor_deploy(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: ``--verify`` runs ``zaumzeug doctor <name> --deploy``."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: Any) -> Any:
        calls.append(list(cmd))
        return _fake_completed(stdout="ok\n")

    monkeypatch.setattr(target_install.subprocess, "run", fake_run)
    monkeypatch.setattr(
        target_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)

    code = target_install.run_install(deploy_dir, skip_venv=True, verify=True)
    assert code == 0

    cli = _zaumzeug_cli_cmds(calls)
    doctor = [c for c in cli if "doctor" in c]
    assert doctor, f"expected doctor --deploy call; got {calls}"
    doctor_cmd = doctor[0]
    assert doctor_cmd[-3:] == ["doctor", "example", "--deploy"]
    assert doctor_cmd[-4] == "zaumzeug"


def test_e5_s09_ac6_verify_runs_serve_dry_run(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: ``--verify`` runs ``zaumzeug serve <name> --deploy --dry-run``."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: Any) -> Any:
        calls.append(list(cmd))
        return _fake_completed(stdout="ok\n")

    monkeypatch.setattr(target_install.subprocess, "run", fake_run)
    monkeypatch.setattr(
        target_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)

    code = target_install.run_install(deploy_dir, skip_venv=True, verify=True)
    assert code == 0

    cli = _zaumzeug_cli_cmds(calls)
    serve = [c for c in cli if "serve" in c]
    assert serve, f"expected serve --deploy --dry-run call; got {calls}"
    serve_cmd = serve[0]
    assert serve_cmd[-4:] == ["serve", "example", "--deploy", "--dry-run"]
    # Doctor must run before serve dry-run.
    doctor_idx = next(i for i, c in enumerate(cli) if "doctor" in c)
    serve_idx = next(i for i, c in enumerate(cli) if "serve" in c)
    assert doctor_idx < serve_idx


def test_e5_s09_ac6_skip_venv_and_verify_flags(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: ``--skip-venv`` and ``--verify`` work together (passthrough to core)."""
    args = target_install.parse_args(["--skip-venv", "--verify"])
    assert args.skip_venv is True
    assert args.verify is True

    created: list[Path] = []
    FakeBuilder = _fake_venv_builder(target_install)

    class TrackingBuilder(FakeBuilder):  # type: ignore[valid-type,misc]
        def create(self, env_dir: str | Path) -> None:
            created.append(Path(env_dir))
            super().create(env_dir)

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: Any) -> Any:
        calls.append(list(cmd))
        return _fake_completed(stdout="ok\n")

    monkeypatch.setattr(target_install.venv, "EnvBuilder", TrackingBuilder)
    monkeypatch.setattr(target_install.subprocess, "run", fake_run)

    deploy_dir = tmp_path / "deploy" / "example"
    _seed_minimal_bundle(deploy_dir)

    code = target_install.run_install(
        deploy_dir,
        skip_venv=True,
        verify=True,
    )
    assert code == 0
    assert created == []
    assert not (deploy_dir / ".venv").exists()

    cli = _zaumzeug_cli_cmds(calls)
    assert any("doctor" in c and "--deploy" in c for c in cli)
    assert any(
        "serve" in c and "--deploy" in c and "--dry-run" in c for c in cli
    )


def test_e5_s09c_ac4_verify_fails_on_bad_bundle(
    target_install: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: Non-zero exit when doctor or serve dry-run fails under ``--verify``."""
    monkeypatch.setattr(
        target_install,
        "resolve_install_python",
        lambda *_a, **_k: Path(sys.executable),
    )

    # Doctor fails → overall install exits non-zero; serve must not run.
    doctor_calls: list[list[str]] = []

    def doctor_fails(cmd: list[str], **_kwargs: Any) -> Any:
        doctor_calls.append(list(cmd))
        if "doctor" in cmd:
            return _fake_completed(returncode=1, stderr="doctor fail\n")
        return _fake_completed(stdout="ok\n")

    monkeypatch.setattr(target_install.subprocess, "run", doctor_fails)
    deploy_dir = tmp_path / "deploy" / "bad_doctor"
    _seed_minimal_bundle(deploy_dir)
    code = target_install.main(
        ["--deploy-dir", str(deploy_dir), "--skip-venv", "--verify"]
    )
    assert code == 1
    assert any("doctor" in c for c in doctor_calls)
    assert not any("serve" in c for c in doctor_calls)

    # Serve dry-run fails after doctor passes.
    serve_calls: list[list[str]] = []

    def serve_fails(cmd: list[str], **_kwargs: Any) -> Any:
        serve_calls.append(list(cmd))
        if "serve" in cmd:
            return _fake_completed(returncode=1, stderr="serve fail\n")
        return _fake_completed(stdout="ok\n")

    monkeypatch.setattr(target_install.subprocess, "run", serve_fails)
    other = tmp_path / "deploy" / "bad_serve"
    _seed_minimal_bundle(other)
    code = target_install.main(
        ["--deploy-dir", str(other), "--skip-venv", "--verify"]
    )
    assert code == 1
    assert any("doctor" in c for c in serve_calls)
    assert any("serve" in c for c in serve_calls)
