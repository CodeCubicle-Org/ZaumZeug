# Story: E6-S08 / E6.8
"""E6-S08 AC-7 — User workflow docs for human quality rating."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_TESTING = REPO_ROOT / "user-docs" / "guides" / "testing.md"
TEMPLATE_TESTING = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "guides" / "testing.md"
)
LIVE_CLI = REPO_ROOT / "user-docs" / "reference" / "cli.md"
TEMPLATE_CLI = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "reference" / "cli.md"
)
LIVE_COMPILE = REPO_ROOT / "user-docs" / "guides" / "compile.md"
TEMPLATE_COMPILE = (
    REPO_ROOT / "install" / "templates" / "user-docs" / "guides" / "compile.md"
)
LIVE_README = REPO_ROOT / "user-docs" / "README.md"
TEMPLATE_README = REPO_ROOT / "install" / "templates" / "user-docs" / "README.md"

ARCH_DATA_FLOWS = REPO_ROOT / "docs" / "architecture" / "04-data-flows.md"
ARCH_CONFIG = REPO_ROOT / "docs" / "architecture" / "05-configuration.md"
ARCH_LAYOUT = REPO_ROOT / "docs" / "architecture" / "02-repository-and-layout.md"
ARCH_SDK = REPO_ROOT / "docs" / "architecture" / "09-sdk-module-map.md"


def test_e6_s08_ac7_testing_md_workflows_abc() -> None:
    """AC-7: testing.md Journey C subsection covers Workflows A/B/C + decision table."""
    for path in (LIVE_TESTING, TEMPLATE_TESTING):
        text = path.read_text(encoding="utf-8")
        assert "Human quality rating" in text, path
        assert "Workflow A" in text, path
        assert "Workflow B" in text, path
        assert "Workflow C" in text, path
        assert "zaumzeug run" in text and "--rate" in text, path
        assert "zaumzeug rate" in text and "--unrated" in text, path
        assert "--apply --compile" in text, path
        assert "keep_val" in text, path
        assert "keep_train" in text, path
        assert "discard" in text, path
        assert "model_id" in text, path
        assert "data/traces/" in text, path
        assert "data/ratings/" in text, path
        assert "last agent stage" in text, path
        assert "dev" in text.lower(), path


def test_e6_s08_ac7_live_and_template_testing_md_match() -> None:
    """AC-7: live and install-template testing.md stay in sync."""
    live = LIVE_TESTING.read_text(encoding="utf-8")
    template = TEMPLATE_TESTING.read_text(encoding="utf-8")
    assert live == template
    assert LIVE_CLI.read_text(encoding="utf-8") == TEMPLATE_CLI.read_text(encoding="utf-8")
    assert LIVE_COMPILE.read_text(encoding="utf-8") == TEMPLATE_COMPILE.read_text(
        encoding="utf-8"
    )
    assert LIVE_README.read_text(encoding="utf-8") == TEMPLATE_README.read_text(
        encoding="utf-8"
    )


def test_e6_s08_ac7_cli_documents_rate() -> None:
    """AC-7: CLI reference documents zaumzeug rate and run --rate flags."""
    for path in (LIVE_CLI, TEMPLATE_CLI):
        text = path.read_text(encoding="utf-8")
        assert "## `zaumzeug rate`" in text, path
        assert "run --rate" in text or "--rate" in text, path
        for flag in (
            "--trace",
            "--unrated",
            "--force",
            "--apply",
            "--compile",
            "--all-agents",
            "--no-input",
            "--quality",
            "--expected",
            "--decision",
        ):
            assert flag in text, (path, flag)


def test_e6_s08_ac7_compile_crosslink() -> None:
    """AC-7: compile guide cross-links to human rating subsection."""
    for path in (LIVE_COMPILE, TEMPLATE_COMPILE):
        text = path.read_text(encoding="utf-8")
        assert "human-quality-rating" in text or "Human quality rating" in text, path
        assert "testing.md" in text, path


def test_e6_s08_ac7_readme_lists_rate() -> None:
    """AC-7: user-docs README lists `zaumzeug rate`."""
    for path in (LIVE_README, TEMPLATE_README):
        text = path.read_text(encoding="utf-8")
        assert "`zaumzeug rate`" in text, path


def test_e6_s08_ac7_architecture_rate_markers() -> None:
    """AC-7: architecture §5.5 / §6.3 / §9 / layout mention rate + data/ratings/."""
    data_flows = ARCH_DATA_FLOWS.read_text(encoding="utf-8")
    assert "zaumzeug rate" in data_flows or "human rate" in data_flows.lower()
    assert "E6-S08" in data_flows

    config = ARCH_CONFIG.read_text(encoding="utf-8")
    assert "eval/rate.py" in config or "zaumzeug rate" in config
    assert "No DeepEval required" in config or "no DeepEval required" in config.lower()

    layout = ARCH_LAYOUT.read_text(encoding="utf-8")
    assert "data/ratings/" in layout

    sdk = ARCH_SDK.read_text(encoding="utf-8")
    assert "eval/rate.py" in sdk or "run_rate" in sdk
    assert "rate" in sdk
