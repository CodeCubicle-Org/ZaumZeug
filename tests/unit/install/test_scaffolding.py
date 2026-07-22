# Story: E1-S03 / E1.3
"""E1-S03 — Project scaffolding on install (unit)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CLIENT_INSTALL_PATH = REPO_ROOT / "install" / "client_install.py"
TEMPLATES_DIR = REPO_ROOT / "install" / "templates"


def _load_client_install() -> ModuleType:
    """Load ``install/client_install.py`` without requiring ``install`` as a package."""
    spec = importlib.util.spec_from_file_location(
        "zaumzeug_client_install_scaffold",
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


def test_e1_s03_ac1_copies_example_harness(
    client_install: ModuleType,
    tmp_path: Path,
) -> None:
    """AC-1: Copies ``usr-harnesses/example/`` from install templates."""
    client_install.scaffold_project(tmp_path, no_example=False, cursor_mcp=False)

    example = tmp_path / "usr-harnesses" / "example"
    assert (example / "harness.yaml").is_file()
    assert (example / "workflow.yaml").is_file()
    assert (example / "agents" / "researcher" / "agent.yaml").is_file()
    assert (example / "agents" / "researcher" / "agents-models.yaml").is_file()

    agents_models = yaml.safe_load(
        (example / "agents" / "researcher" / "agents-models.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert agents_models["default_model_id"] == "mock"

    # Idempotent: user edits are preserved on re-run
    harness_path = example / "harness.yaml"
    harness_path.write_text("# user edit\n", encoding="utf-8")
    client_install.scaffold_project(tmp_path, no_example=False, cursor_mcp=False)
    assert harness_path.read_text(encoding="utf-8") == "# user edit\n"


def test_e1_s03_ac2_copies_config_and_env_example(
    client_install: ModuleType,
    tmp_path: Path,
) -> None:
    """AC-2: Copies ``config/models.yaml``, ``.env.example``, ``.cursor/mcp.json.example``."""
    client_install.scaffold_project(tmp_path, no_example=True, cursor_mcp=False)

    models_path = tmp_path / "config" / "models.yaml"
    assert models_path.is_file()
    models = yaml.safe_load(models_path.read_text(encoding="utf-8"))
    assert models["default_model_id"] == "mock"
    assert models["models"]["mock"]["provider"] == "mock"

    assert (tmp_path / ".env.example").is_file()
    assert (tmp_path / ".cursor" / "mcp.json.example").is_file()
    mcp = (tmp_path / ".cursor" / "mcp.json.example").read_text(encoding="utf-8")
    assert "localhost:1417" in mcp

    # Template source for models is models.example.yaml
    assert (TEMPLATES_DIR / "config" / "models.example.yaml").is_file()


def test_e1_s03_ac3_gitignore_entries(
    client_install: ModuleType,
    tmp_path: Path,
) -> None:
    """AC-3: Updates ``.gitignore`` for ``.venv``, ``artifacts/``, ``deploy/``, ``.env``."""
    (tmp_path / ".gitignore").write_text("# existing\n__pycache__/\n", encoding="utf-8")

    client_install.scaffold_project(tmp_path, no_example=True, cursor_mcp=False)

    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    lines = {line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")}
    assert ".venv" in lines
    assert ".env" in lines
    assert "deploy/" in lines
    assert "artifacts/" in lines
    assert "__pycache__/" in lines  # pre-existing preserved

    # Second run does not duplicate
    client_install.scaffold_project(tmp_path, no_example=True, cursor_mcp=False)
    text2 = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert text2.count("deploy/") == 1
    assert text2.count("artifacts/") == 1


def test_e1_s03_ac4_preserves_existing_env(
    client_install: ModuleType,
    tmp_path: Path,
) -> None:
    """AC-4: Never overwrites an existing ``.env``."""
    secret = "OPENAI_API_KEY=do-not-clobber\n"
    (tmp_path / ".env").write_text(secret, encoding="utf-8")

    client_install.scaffold_project(tmp_path, no_example=True, cursor_mcp=False)

    assert (tmp_path / ".env").read_text(encoding="utf-8") == secret
    assert (tmp_path / ".env.example").is_file()

    # Fresh project without .env gets a seed copy
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    client_install.scaffold_project(fresh, no_example=True, cursor_mcp=False)
    assert (fresh / ".env").is_file()
    assert (fresh / ".env").read_text(encoding="utf-8") == (
        fresh / ".env.example"
    ).read_text(encoding="utf-8")


def test_e1_s03_ac5_no_example_flag_skips_copy(
    client_install: ModuleType,
    tmp_path: Path,
) -> None:
    """AC-5: ``--no-example`` skips example harness copy."""
    client_install.scaffold_project(tmp_path, no_example=True, cursor_mcp=False)

    assert not (tmp_path / "usr-harnesses" / "example").exists()
    # Other scaffolding still runs
    assert (tmp_path / "config" / "models.yaml").is_file()
    assert (tmp_path / ".env.example").is_file()
