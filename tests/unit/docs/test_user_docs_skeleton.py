# Story: E1-S05 / E1.5
"""E1-S05 — User documentation skeleton path presence."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DOCS = REPO_ROOT / "install" / "templates" / "user-docs"
LIVE_DOCS = REPO_ROOT / "user-docs"

# AC-1 required paths (Architecture §3.5 / PRD E1.5)
REQUIRED_RELATIVE_PATHS = (
    "README.md",
    "getting-started/installation.md",
    "getting-started/project-setup.md",
    "getting-started/first-harness.md",
    "reference/cli.md",
    "guides/multi-agent-workflow.md",
    "guides/testing.md",
    "guides/deploy.md",
)

# AC-2 / DoD — installation.md must cover PRD §7.4 topics
INSTALLATION_REQUIRED_HEADINGS = (
    "Prerequisites",
    "Effort and complexity",
    "Commands",
    "Disk space",
    "Optional extras",
    "Updating dependencies",
    "Troubleshooting",
)

INSTALLATION_REQUIRED_COMMANDS = (
    r".\install\client-install.ps1",
    r"python install\client_install.py",
    "./install/client-install.sh",
    "python install/client_install.py",
)

INSTALLATION_UPDATE_MARKERS = (
    "git pull",
    'pip install -e ".[dev]"',
    "target_install",
)


def test_e1_s05_ac1_template_tree_has_required_paths() -> None:
    """AC-1: install template user-docs tree contains the skeleton paths."""
    missing = [
        rel
        for rel in REQUIRED_RELATIVE_PATHS
        if not (TEMPLATE_DOCS / rel).is_file()
    ]
    assert not missing, f"Missing template paths: {missing}"


def test_e1_s05_ac1_live_tree_has_required_paths() -> None:
    """AC-1: live user-docs/ tree matches the post-install skeleton."""
    missing = [
        rel for rel in REQUIRED_RELATIVE_PATHS if not (LIVE_DOCS / rel).is_file()
    ]
    assert not missing, f"Missing live user-docs paths: {missing}"


def test_e1_s05_ac2_installation_covers_prd_74_topics() -> None:
    """AC-2: installation.md covers prerequisites, effort, disk, extras, updates, troubleshooting."""
    text = (TEMPLATE_DOCS / "getting-started" / "installation.md").read_text(
        encoding="utf-8"
    )
    missing_headings = [h for h in INSTALLATION_REQUIRED_HEADINGS if h not in text]
    assert not missing_headings, f"Missing §7.4 headings: {missing_headings}"

    missing_cmds = [c for c in INSTALLATION_REQUIRED_COMMANDS if c not in text]
    assert not missing_cmds, f"Missing install table commands: {missing_cmds}"

    missing_updates = [m for m in INSTALLATION_UPDATE_MARKERS if m not in text]
    assert not missing_updates, f"Missing update scenarios: {missing_updates}"


def test_e1_s05_ac3_installation_links_architecture_not_sdk_internals() -> None:
    """AC-3: user guide points at Architecture for technical behavior; no SDK module dumps."""
    text = (TEMPLATE_DOCS / "getting-started" / "installation.md").read_text(
        encoding="utf-8"
    )
    assert "Architecture §3.4" in text
    # Stay user-facing — do not paste SDK package internals
    assert "src/zaumzeug" not in text
    assert "client_install.py" in text  # user-facing script path is OK
