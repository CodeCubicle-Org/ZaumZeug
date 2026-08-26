"""Harness directory root resolution (dev vs deploy).

Canonical entry for ``--deploy`` / ``HARNESS_ROOT=deploy`` (Architecture §8.1, E5-S04).
Serve, MCP, and ACP (and other root-aware CLI commands) resolve bundles through
:func:`resolve_harness_path` so container/systemd environments can default to
``deploy/`` without repeating path logic.
"""

from __future__ import annotations

import os
from pathlib import Path

HARNESS_ROOT_ENV = "HARNESS_ROOT"
DEV_HARNESS_ROOT = "usr-harnesses"
DEPLOY_HARNESS_ROOT = "deploy"
DEPLOY_MANIFEST = "manifest.json"

# Protocol / ops surfaces that must honour ``HARNESS_ROOT`` (E5-S04 AC-1).
PROTOCOL_ROOT_COMMANDS = frozenset({"serve", "mcp", "acp", "a2a"})


def is_deploy_mode(*, deploy_flag: bool = False) -> bool:
    """Return True when *deploy_flag* is set or ``HARNESS_ROOT=deploy``."""
    if deploy_flag:
        return True
    return os.environ.get(HARNESS_ROOT_ENV, "").strip().lower() == DEPLOY_HARNESS_ROOT


def harness_root_segment(*, deploy: bool) -> str:
    """Return the subdirectory name under the project root for harness bundles."""
    return DEPLOY_HARNESS_ROOT if deploy else DEV_HARNESS_ROOT


def harness_dir(project_root: Path | str, harness_name: str, *, deploy: bool) -> Path:
    """Resolve ``<root>/<usr-harnesses|deploy>/<harness_name>/`` (caller sets *deploy*)."""
    return Path(project_root) / harness_root_segment(deploy=deploy) / harness_name


def resolve_harness_path(
    project_root: Path | str,
    harness_name: str,
    *,
    deploy_flag: bool = False,
) -> Path:
    """Resolve harness path honouring ``--deploy`` and ``HARNESS_ROOT=deploy``.

    Prefer this over calling :func:`harness_dir` with a raw flag when the
    command should respect the environment override (serve / mcp / acp / run /
    doctor).
    """
    return harness_dir(
        project_root,
        harness_name,
        deploy=is_deploy_mode(deploy_flag=deploy_flag),
    )
