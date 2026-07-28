"""Dev-vs-deploy path policy and strip helpers (Architecture §10.1).

Exclude sets are shared with E6-S04. Strip helpers and include checks support
the E5-S01 packager; the full include/pin golden matrix remains E5-S02.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

__all__ = [
    "DEV_ONLY_AGENT_DIRS",
    "DEV_ONLY_TOP_LEVEL_DIRS",
    "STRIPPED_AGENT_KEYS",
    "STRIPPED_HARNESS_KEYS",
    "is_excluded_from_deploy",
    "strip_agent_yaml",
    "strip_harness_yaml",
]

# Top-level under usr-harnesses/<name>/ — never copied to deploy/<name>/.
DEV_ONLY_TOP_LEVEL_DIRS: frozenset[str] = frozenset({"data", "eval"})

# Under agents/<agent-name>/ — never copied to deploy.
DEV_ONLY_AGENT_DIRS: frozenset[str] = frozenset({"modules", "skills", "data"})

# Dropped from harness.yaml in the deploy bundle (Architecture §10.2 step 3).
STRIPPED_HARNESS_KEYS: frozenset[str] = frozenset({"compile", "eval", "deploy"})

# Dropped from agent.yaml in the deploy bundle (E5-S02 AC-5).
STRIPPED_AGENT_KEYS: frozenset[str] = frozenset({"compile"})


def is_excluded_from_deploy(relative_path: str | Path) -> bool:
    """Return True if *relative_path* (harness-relative) must not enter the bundle.

    Paths may use ``/`` or ``\\``; both are normalized before segment checks
    (Architecture §10.1). Comparison is case-sensitive on path segment names.
    """
    # Normalize Windows separators so Linux CI accepts harness-relative strings
    # written with backslashes (Path.as_posix() alone does not rewrite ``\\``).
    normalized = str(relative_path).replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if not parts:
        return False
    if parts[0] in DEV_ONLY_TOP_LEVEL_DIRS:
        return True
    if len(parts) >= 3 and parts[0] == "agents" and parts[2] in DEV_ONLY_AGENT_DIRS:
        return True
    return False


def strip_harness_yaml(data: dict[str, Any]) -> dict[str, Any]:
    """Return a harness.yaml mapping without ``compile`` / ``eval`` / ``deploy``."""
    return {key: value for key, value in data.items() if key not in STRIPPED_HARNESS_KEYS}


def strip_agent_yaml(data: dict[str, Any]) -> dict[str, Any]:
    """Return an agent.yaml mapping without the ``compile`` section."""
    return {key: value for key, value in data.items() if key not in STRIPPED_AGENT_KEYS}
