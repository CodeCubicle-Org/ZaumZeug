# Story: E5-S04 / E5.4
"""E5-S04 — ``HARNESS_ROOT=deploy`` environment override."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from zaumzeug.cli import build_parser
from zaumzeug.config.harness_root import (
    DEPLOY_HARNESS_ROOT,
    DEV_HARNESS_ROOT,
    HARNESS_ROOT_ENV,
    PROTOCOL_ROOT_COMMANDS,
    harness_root_segment,
    is_deploy_mode,
    resolve_harness_path,
)
from zaumzeug.serve import runner as serve_runner
from zaumzeug.serve.validate import validate_serve


def test_e5_s04_ac1_env_forces_deploy_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: ``HARNESS_ROOT=deploy`` forces deploy root for serve, mcp, acp."""
    monkeypatch.setenv(HARNESS_ROOT_ENV, "deploy")

    assert PROTOCOL_ROOT_COMMANDS == frozenset({"serve", "mcp", "acp"})
    assert is_deploy_mode() is True
    assert is_deploy_mode(deploy_flag=False) is True
    assert harness_root_segment(deploy=True) == DEPLOY_HARNESS_ROOT

    resolved = resolve_harness_path(tmp_path, "shipped")
    assert resolved == tmp_path / DEPLOY_HARNESS_ROOT / "shipped"

    # serve (validate path — no bind)
    validation = validate_serve("shipped", project_root=tmp_path)
    assert validation.harness_dir == resolved
    assert DEPLOY_HARNESS_ROOT in validation.harness_dir.parts
    assert DEV_HARNESS_ROOT not in validation.harness_dir.parts

    # mcp / acp stubs share the same resolver + honour env without --deploy
    parser = build_parser()
    for command in ("mcp", "acp"):
        assert command in PROTOCOL_ROOT_COMMANDS
        args = parser.parse_args([command, "shipped"])
        assert args.deploy is False
        path = resolve_harness_path(tmp_path, args.harness_name, deploy_flag=args.deploy)
        assert path == resolved


def test_e5_s04_ac2_default_usr_harnesses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: Default dev root remains ``usr-harnesses/`` when env unset."""
    monkeypatch.delenv(HARNESS_ROOT_ENV, raising=False)

    assert is_deploy_mode() is False
    assert harness_root_segment(deploy=False) == DEV_HARNESS_ROOT

    resolved = resolve_harness_path(tmp_path, "example")
    assert resolved == tmp_path / DEV_HARNESS_ROOT / "example"

    validation = validate_serve("example", project_root=tmp_path)
    assert validation.harness_dir == resolved
    assert DEV_HARNESS_ROOT in validation.harness_dir.parts

    # --deploy still forces deploy without env
    assert is_deploy_mode(deploy_flag=True) is True
    assert resolve_harness_path(tmp_path, "example", deploy_flag=True) == (
        tmp_path / DEPLOY_HARNESS_ROOT / "example"
    )

    # Serve runner must not hardcode the dev segment string
    source = inspect.getsource(serve_runner.run_serve)
    assert '"usr-harnesses"' not in source
    assert "'usr-harnesses'" not in source
