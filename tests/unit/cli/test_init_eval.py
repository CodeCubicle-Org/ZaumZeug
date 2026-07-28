# Story: E6-S04 / E6.4 (init flag)
"""E6-S04 — ``zaumzeug init --with-eval`` optional scaffold."""

from __future__ import annotations

from pathlib import Path

import pytest

from zaumzeug.cli import _init_command, build_parser
from zaumzeug.scaffold import init_harness


def test_e6_s04_init_with_eval_copies_scaffold(tmp_path: Path) -> None:
    """``--with-eval`` copies ``eval/metrics.py`` and ``eval/test_*.py``."""
    project_root = tmp_path / "project"
    (project_root / "usr-harnesses").mkdir(parents=True)

    without = init_harness("plain", project_root=project_root, with_eval=False)
    assert not (without / "eval").exists()

    with_eval = init_harness("with-eval", project_root=project_root, with_eval=True)
    assert (with_eval / "eval" / "metrics.py").is_file()
    assert (with_eval / "eval" / "test_smoke.py").is_file()
    smoke = (with_eval / "eval" / "test_smoke.py").read_text(encoding="utf-8")
    assert "with-eval" in smoke
    assert "{{name}}" not in smoke


def test_e6_s04_cli_with_eval_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI ``zaumzeug init <name> --with-eval`` wires the scaffold flag."""
    project_root = tmp_path / "project"
    (project_root / "usr-harnesses").mkdir(parents=True)
    monkeypatch.setattr(
        "zaumzeug.scaffold.init.find_project_root",
        lambda start=None: project_root,
    )

    parser = build_parser()
    args = parser.parse_args(["init", "evaled", "--with-eval"])
    assert _init_command(args) == 0

    harness = project_root / "usr-harnesses" / "evaled"
    assert (harness / "eval" / "metrics.py").is_file()
    out = capsys.readouterr().out
    assert "deepeval test run" in out
    assert "evaled" in out
