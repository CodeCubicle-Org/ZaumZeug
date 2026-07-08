"""Project root and harness discovery for doctor."""

from __future__ import annotations

from pathlib import Path


def find_project_root(start: Path | str | None = None) -> Path:
    """Walk upward from *start* (or cwd) to locate the harness project root."""
    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "usr-harnesses").is_dir():
            return candidate
        if (candidate / "config" / "models.yaml").is_file():
            return candidate
    return current


def discover_harnesses(project_root: Path | str) -> list[tuple[str, Path]]:
    """Return ``(name, harness_dir)`` for each harness under ``usr-harnesses/``."""
    project_root = Path(project_root)
    harness_root = project_root / "usr-harnesses"
    if not harness_root.is_dir():
        return []

    harnesses: list[tuple[str, Path]] = []
    for child in sorted(harness_root.iterdir()):
        if child.is_dir() and (child / "harness.yaml").is_file():
            harnesses.append((child.name, child))
    return harnesses


def list_agent_names(harness_dir: Path | str) -> list[str]:
    """List agent folder names that contain ``agent.yaml``."""
    harness_dir = Path(harness_dir)
    agents_dir = harness_dir / "agents"
    if not agents_dir.is_dir():
        return []
    return sorted(
        entry.name
        for entry in agents_dir.iterdir()
        if entry.is_dir() and (entry / "agent.yaml").is_file()
    )
