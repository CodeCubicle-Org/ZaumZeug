# Story: E1-S07 / E1.7
"""E1-S07 — Cross-platform CI matrix workflow verification."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci-matrix.yml"
SMOKE_SCRIPT = REPO_ROOT / "install" / "ci_serve_smoke.py"

REQUIRED_OS = ("windows-latest", "ubuntu-latest", "macos-latest")


@pytest.fixture(scope="module")
def workflow() -> dict:
    assert WORKFLOW_PATH.is_file(), f"missing workflow: {WORKFLOW_PATH}"
    data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def workflow_text() -> str:
    assert WORKFLOW_PATH.is_file(), f"missing workflow: {WORKFLOW_PATH}"
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_e1_s07_ac6_workflow_exists() -> None:
    """AC-6: Workflow lives in ``.github/workflows/``."""
    assert WORKFLOW_PATH.is_file()
    assert WORKFLOW_PATH.name == "ci-matrix.yml"


def test_e1_s07_ac1_three_os_matrix(workflow: dict) -> None:
    """AC-1: Matrix includes windows-latest, ubuntu-latest, macos-latest."""
    jobs = workflow["jobs"]
    phase1 = jobs["phase1"]
    matrix_os = phase1["strategy"]["matrix"]["os"]
    assert set(matrix_os) == set(REQUIRED_OS)
    assert phase1["runs-on"] == "${{ matrix.os }}"
    assert phase1["strategy"]["fail-fast"] is True
    assert phase1["timeout-minutes"] == 30


def test_e1_s07_ac2_install_via_wrappers_or_client_install(workflow_text: str) -> None:
    """AC-2: Each job installs via OS wrappers (delegate to client_install.py)."""
    assert "client-install.sh" in workflow_text
    assert "client-install.ps1" in workflow_text
    assert "--skip-venv" in workflow_text
    assert "--verify" in workflow_text


def test_e1_s07_ac3_doctor_and_serve_dry_run(workflow_text: str) -> None:
    """AC-3: Job steps run doctor and serve example --dry-run."""
    assert "zaumzeug doctor" in workflow_text
    assert "zaumzeug serve example --dry-run" in workflow_text


def test_e1_s07_ac4_serve_smoke_ephemeral(workflow_text: str) -> None:
    """AC-4: Mock serve smoke on ephemeral port (CLI via ci_serve_smoke)."""
    assert "ci_serve_smoke.py" in workflow_text
    assert SMOKE_SCRIPT.is_file()
    smoke_src = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "zaumzeug" in smoke_src
    assert "serve" in smoke_src
    assert "--port" in smoke_src
    assert "/v1/models" in smoke_src


def test_e1_s07_contract_pytest_and_pip_cache(workflow_text: str) -> None:
    """Contract suite + pip cache (implementation tasks / E3-S07 DoD)."""
    assert "tests/integration/test_openai_contract.py" in workflow_text
    assert "cache: pip" in workflow_text
    assert "cache-dependency-path: pyproject.toml" in workflow_text
    assert "HARNESS_LIVE_LLM=1" not in workflow_text


def test_e1_s07_ac5_no_live_llm_in_default_ci(workflow: dict) -> None:
    """AC-5 companion: default CI must not enable live LLM e2e."""
    dumped = yaml.safe_dump(workflow)
    assert "HARNESS_LIVE_LLM=1" not in dumped
