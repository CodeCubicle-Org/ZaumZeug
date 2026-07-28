"""Scaffold a new harness under ``usr-harnesses/<name>/`` (E1-S04)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from zaumzeug.config.harness_root import DEV_HARNESS_ROOT
from zaumzeug.doctor.project import find_project_root

# Safe path segment: alphanumeric start; letters, digits, underscore, hyphen after.
_HARNESS_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

_TEXT_SUFFIXES = {".yaml", ".yml", ".md", ".txt", ".json", ".py", ".example", ".toml"}

_PLACEHOLDER = "{{name}}"


class ScaffoldError(Exception):
    """Fatal scaffolding failure with an actionable message."""


def validate_harness_name(name: str) -> str:
    """Return a validated harness name or raise :class:`ScaffoldError`."""
    if not name or not name.strip():
        raise ScaffoldError("Harness name must be a non-empty path segment.")
    name = name.strip()
    if name in {".", ".."}:
        raise ScaffoldError(f"Invalid harness name: {name!r}.")
    if "/" in name or "\\" in name or ".." in name:
        raise ScaffoldError(
            f"Invalid harness name {name!r}: must be a single path segment "
            "(no separators or '..')."
        )
    if not _HARNESS_NAME_RE.fullmatch(name):
        raise ScaffoldError(
            f"Invalid harness name {name!r}: use letters, digits, '_', or '-', "
            "starting with a letter or digit."
        )
    return name


def discover_harness_template_dir() -> Path:
    """Locate ``install/templates/harness`` by walking up from this package."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "install" / "templates" / "harness"
        if candidate.is_dir() and (candidate / "harness.yaml").is_file():
            return candidate
    raise ScaffoldError(
        "Harness template not found at install/templates/harness/. "
        "Run from a ZaumZeug repo checkout with editable install, "
        "or restore install/templates."
    )


def init_harness(
    name: str,
    *,
    project_root: Path | str | None = None,
    force: bool = False,
    with_eval: bool = False,
    templates_dir: Path | str | None = None,
) -> Path:
    """Create ``usr-harnesses/<name>/`` from the harness template.

    When *with_eval* is True, also copies optional ``eval/`` DeepEval scaffold
    (metrics + ``test_*.py``). Eval files are skipped by default.

    Returns the created harness directory. Raises :class:`ScaffoldError` on
    invalid names, missing templates, or an existing harness without *force*.
    """
    name = validate_harness_name(name)
    root = Path(project_root) if project_root is not None else find_project_root()
    root = root.resolve()

    usr_root = (root / DEV_HARNESS_ROOT).resolve()
    dest = (usr_root / name).resolve()
    if not dest.is_relative_to(usr_root):
        raise ScaffoldError(
            f"Resolved harness path escapes {DEV_HARNESS_ROOT}/: {dest}"
        )

    if dest.exists():
        if not force:
            raise ScaffoldError(
                f"Harness already exists: {dest}. "
                "Use --force to overwrite, or choose a different name."
            )
        if dest.is_dir():
            shutil.rmtree(dest)
        else:
            dest.unlink()

    template = (
        Path(templates_dir) if templates_dir is not None else discover_harness_template_dir()
    )
    if not template.is_dir() or not (template / "harness.yaml").is_file():
        raise ScaffoldError(
            f"Harness template missing or incomplete: {template}. "
            "Expected harness.yaml under install/templates/harness/."
        )

    usr_root.mkdir(parents=True, exist_ok=True)
    _copy_template_tree(template, dest, name=name, with_eval=with_eval)

    harness_yaml = dest / "harness.yaml"
    if not harness_yaml.is_file():
        raise ScaffoldError(f"Scaffold failed: missing {harness_yaml}")

    if with_eval and not (dest / "eval" / "metrics.py").is_file():
        raise ScaffoldError(
            f"Scaffold failed: --with-eval requested but missing {dest / 'eval' / 'metrics.py'}"
        )

    return dest


def _is_eval_template_path(rel: Path) -> bool:
    """True when *rel* is under the optional ``eval/`` scaffold tree."""
    parts = rel.parts
    return bool(parts) and parts[0] == "eval"


def _copy_template_tree(
    src: Path,
    dest: Path,
    *,
    name: str,
    with_eval: bool = False,
) -> None:
    """Copy *src* → *dest*, substituting ``{{name}}`` in text files.

    Optional ``eval/`` files are omitted unless *with_eval* is True (E6-S04).
    """
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        if not with_eval and _is_eval_template_path(rel):
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() in _TEXT_SUFFIXES or path.name in {
            "Dockerfile",
            "Makefile",
            ".gitignore",
        }:
            text = path.read_text(encoding="utf-8")
            target.write_text(text.replace(_PLACEHOLDER, name), encoding="utf-8")
        else:
            shutil.copy2(path, target)
