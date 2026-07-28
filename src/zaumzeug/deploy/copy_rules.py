"""Dev-vs-deploy path exclusion policy (Architecture §10.1).

Full packager copy matrix lands in E5-S01 / E5-S02. This module exports the
canonical exclude sets so E6-S04 can assert ``eval/`` never ships, and E5-S02
can expand include/pin rules against the same source of truth.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

__all__ = [
    "DEV_ONLY_AGENT_DIRS",
    "DEV_ONLY_TOP_LEVEL_DIRS",
    "is_excluded_from_deploy",
]

# Top-level under usr-harnesses/<name>/ — never copied to deploy/<name>/.
DEV_ONLY_TOP_LEVEL_DIRS: frozenset[str] = frozenset({"data", "eval"})

# Under agents/<agent-name>/ — never copied to deploy.
DEV_ONLY_AGENT_DIRS: frozenset[str] = frozenset({"modules", "skills", "data"})


def is_excluded_from_deploy(relative_path: str | Path) -> bool:
    """Return True if *relative_path* (harness-relative) must not enter the bundle.

    Paths use forward or native separators; comparison is case-sensitive on the
    first path segment names as in Architecture §10.1.
    """
    parts = PurePosixPath(Path(relative_path).as_posix()).parts
    if not parts:
        return False
    if parts[0] in DEV_ONLY_TOP_LEVEL_DIRS:
        return True
    if len(parts) >= 3 and parts[0] == "agents" and parts[2] in DEV_ONLY_AGENT_DIRS:
        return True
    return False
