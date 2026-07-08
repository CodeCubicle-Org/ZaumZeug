"""Harness directory root resolution (dev vs deploy)."""

from __future__ import annotations

import os
from pathlib import Path

HARNESS_ROOT_ENV = "HARNESS_ROOT"
DEV_HARNESS_ROOT = "usr-harnesses"
DEPLOY_HARNESS_ROOT = "deploy"
DEPLOY_MANIFEST = "manifest.json"


def is_deploy_mode(*, deploy_flag: bool = False) -> bool:
    """Return True when *deploy_flag* is set or ``HARNESS_ROOT=deploy``."""
    if deploy_flag:
        return True
    return os.environ.get(HARNESS_ROOT_ENV, "").strip().lower() == DEPLOY_HARNESS_ROOT


def harness_root_segment(*, deploy: bool) -> str:
    """Return the subdirectory name under the project root for harness bundles."""
    return DEPLOY_HARNESS_ROOT if deploy else DEV_HARNESS_ROOT


def harness_dir(project_root: Path | str, harness_name: str, *, deploy: bool) -> Path:
    """Resolve ``<root>/<usr-harnesses|deploy>/<harness_name>/``."""
    return Path(project_root) / harness_root_segment(deploy=deploy) / harness_name
