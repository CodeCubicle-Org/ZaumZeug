# Story: E1-S06 / E1.6
"""E1-S06 — New contributor guide (CONTRIBUTING.md) content checks."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"

# AC-2 — vision, install table, mock quick start
REQUIRED_SNIPPETS = (
    "harness SDK and factory",
    r".\install\client-install.ps1",
    r"python install\client_install.py",
    "./install/client-install.sh",
    "python install/client_install.py",
    "zaumzeug serve example",
    "mock model",
)

# AC-3 — time + disk planning ranges (align with PRD §11)
AC3_MARKERS = (
    "< 15 minutes",
    "~1–2.5 GB",
)

# AC-4 — updating dependencies / post-git pull
AC4_MARKERS = (
    "Updating dependencies",
    "git pull",
    r".\install\client-install.ps1 --verify",
    "./install/client-install.sh --verify",
)

# AC-5 — link to installation.md; not a full duplicate of user-docs
AC5_LINK = "user-docs/getting-started/installation.md"
# Headings that belong in the full install guide, not this short entry
FULL_GUIDE_ONLY_HEADINGS = (
    "## Troubleshooting",
)


def test_e1_s06_ac1_contributing_exists() -> None:
    """AC-1: New-contributor guide exists at repo root (alongside install path)."""
    assert CONTRIBUTING.is_file(), f"Missing {CONTRIBUTING}"


def test_e1_s06_ac2_vision_install_mock_quick_start() -> None:
    """AC-2: Vision one-liner, install command table, mock-first quick start."""
    text = CONTRIBUTING.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED_SNIPPETS if s not in text]
    assert not missing, f"Missing AC-2 snippets: {missing}"


def test_e1_s06_ac3_time_and_disk_ranges() -> None:
    """AC-3: States < 15 min target and ~1–2.5 GB dev venv planning range."""
    text = CONTRIBUTING.read_text(encoding="utf-8")
    missing = [m for m in AC3_MARKERS if m not in text]
    assert not missing, f"Missing AC-3 markers: {missing}"


def test_e1_s06_ac4_updating_dependencies_after_pull() -> None:
    """AC-4: Updating-dependencies summary with post-git pull commands."""
    text = CONTRIBUTING.read_text(encoding="utf-8")
    missing = [m for m in AC4_MARKERS if m not in text]
    assert not missing, f"Missing AC-4 markers: {missing}"


def test_e1_s06_ac5_links_installation_not_full_duplicate() -> None:
    """AC-5: Links to installation.md for depth; no full user-docs duplicate."""
    text = CONTRIBUTING.read_text(encoding="utf-8")
    assert AC5_LINK in text
    present = [h for h in FULL_GUIDE_ONLY_HEADINGS if h in text]
    assert not present, f"Short guide should not duplicate full install sections: {present}"
    # Abbreviated layout + maintainer cross-links (implementation tasks)
    assert "usr-harnesses/" in text
    assert "deploy/" in text
    assert "config/" in text
    assert "docs/prd.md" in text
    assert "docs/architecture.md" in text
