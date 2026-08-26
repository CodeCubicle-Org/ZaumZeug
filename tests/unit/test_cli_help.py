# Story: E2-S00
"""E2-S00 — SDK package skeleton and CLI foundation (CLI help)."""

from __future__ import annotations

import subprocess
import sys

import pytest

from zaumzeug.cli import build_parser, main

REQUIRED_SUBCOMMANDS = (
    "init",
    "doctor",
    "serve",
    "run",
    "compile",
    "deploy",
    "eval",
    "rate",
    "mcp",
    "acp",
    "a2a",
)


def test_e2_s00_ac5_help_lists_subcommands() -> None:
    """AC-5: zaumzeug --help exits 0 and lists required subcommand stubs."""
    parser = build_parser()
    help_text = parser.format_help()
    for name in REQUIRED_SUBCOMMANDS:
        assert name in help_text, f"subcommand missing from help: {name}"

    result = subprocess.run(
        [sys.executable, "-m", "zaumzeug.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    combined = f"{result.stdout}\n{result.stderr}"
    for name in REQUIRED_SUBCOMMANDS:
        assert name in combined, f"subcommand missing from CLI --help: {name}"

    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
