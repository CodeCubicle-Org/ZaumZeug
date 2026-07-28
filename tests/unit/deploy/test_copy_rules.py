# Story: E5-S02 / E5.2 (shared E6-S04 / E6.4)
"""E5-S02 — deploy copy rules (partial: ``eval/`` exclusion for E6-S04 AC-3).

Full include/pin matrix tests land with E5-S02; this module asserts the shared
``eval/`` exclusion policy early so E6-S04 can close AC-3.
"""

from __future__ import annotations

import pytest

from zaumzeug.deploy.copy_rules import (
    DEV_ONLY_TOP_LEVEL_DIRS,
    is_excluded_from_deploy,
)


def test_e5_s02_excludes_eval() -> None:
    """AC (E6-S04 AC-3 / E5-S02): ``eval/`` is excluded from the deploy bundle."""
    assert "eval" in DEV_ONLY_TOP_LEVEL_DIRS
    assert is_excluded_from_deploy("eval") is True
    assert is_excluded_from_deploy("eval/metrics.py") is True
    assert is_excluded_from_deploy("eval/test_researcher.py") is True
    assert is_excluded_from_deploy(r"eval\test_smoke.py") is True
    # Runtime paths remain eligible (full matrix in E5-S02).
    assert is_excluded_from_deploy("harness.yaml") is False
    assert is_excluded_from_deploy("workflow.yaml") is False
    assert is_excluded_from_deploy("agents/researcher/agent.yaml") is False


@pytest.mark.parametrize(
    "path",
    [
        "data/val.jsonl",
        "agents/researcher/modules/researcher.py",
        "agents/researcher/skills/recon.md",
        "agents/researcher/data/train.jsonl",
    ],
)
def test_e5_s02_excludes_other_dev_only_paths(path: str) -> None:
    """Smoke: other Architecture §10.1 dev-only paths are also marked excluded."""
    assert is_excluded_from_deploy(path) is True
