"""Runtime input-rewrite preprocess (E4-S03b / Pattern A).

Loads optional ``prompts/input_rewrite.md`` (or manifest path) from a compiled
artifact and applies the **fixed** template to user text before ``Agent.run``.
No DSPy / GEPA on this path — GEPA optimized the template offline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, TemplateSyntaxError

from zaumzeug.config.resolver import ARTIFACT_MANIFEST, LEGACY_ARTIFACT_MANIFEST

__all__ = [
    "PreprocessError",
    "apply_input_rewrite",
    "load_input_rewrite_template",
    "preprocess_openai_messages",
    "preprocess_user_text",
    "resolve_input_rewrite_path",
]

# Variables available to Jinja / str.format templates (export contract).
_TEMPLATE_VAR_NAMES = ("user_input", "message", "input", "text", "query")


class PreprocessError(RuntimeError):
    """Input-rewrite preprocess failed with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.suggestion = suggestion
        super().__init__(message)


def _find_artifact_manifest(artifact_dir: Path) -> Path | None:
    """Prefer ``artifact-manifest.json``; accept legacy ``manifest.json``."""
    canonical = artifact_dir / ARTIFACT_MANIFEST
    if canonical.is_file():
        return canonical
    legacy = artifact_dir / LEGACY_ARTIFACT_MANIFEST
    if legacy.is_file():
        return legacy
    return None


def resolve_input_rewrite_path(artifact_dir: Path | str) -> Path | None:
    """Return the absolute rewrite file path when the manifest lists ``input_rewrite``.

    Returns ``None`` when the artifact has no rewrite entry (normal for default
    harnesses). Does not check whether the file exists — use
    :func:`load_input_rewrite_template` for that.
    """
    root = Path(artifact_dir)
    manifest_path = _find_artifact_manifest(root)
    if manifest_path is None:
        return None

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreprocessError(
            f"Cannot read artifact manifest at {manifest_path}: {exc}",
            path=manifest_path,
            suggestion=f"Re-run compile or fix {ARTIFACT_MANIFEST}",
        ) from exc

    if not isinstance(payload, dict):
        return None

    paths = payload.get("paths")
    if not isinstance(paths, dict):
        return None

    rel = paths.get("input_rewrite")
    if rel is None or rel == "":
        return None

    return (root / str(rel)).resolve()


def load_input_rewrite_template(artifact_dir: Path | str) -> str | None:
    """Load rewrite template text when the manifest lists ``input_rewrite``.

    Returns ``None`` when rewrite is not listed. Raises :class:`PreprocessError`
    when listed but the file is missing (AC-4).
    """
    path = resolve_input_rewrite_path(artifact_dir)
    if path is None:
        return None
    if not path.is_file():
        raise PreprocessError(
            f"artifact lists input_rewrite but file is missing: {path}",
            path=path,
            suggestion=(
                f"Restore {path} or re-run `zaumzeug compile` so the export "
                "writes prompts/input_rewrite.md"
            ),
        )
    return path.read_text(encoding="utf-8")


def apply_input_rewrite(template: str, user_message: str) -> str:
    """Apply fixed rewrite template text to a user message (AC-2).

    Supports Jinja (``{{ user_input }}``), ``str.format`` placeholders, or plain
    instruction text (prepended when no placeholders are present).
    """
    context = {name: user_message for name in _TEMPLATE_VAR_NAMES}
    text = template

    if "{{" in text or "{%" in text:
        try:
            env = Environment(autoescape=False)
            rendered = env.from_string(text).render(**context)
        except TemplateSyntaxError as exc:
            raise PreprocessError(
                f"Invalid Jinja in input_rewrite template: {exc}",
                suggestion="Fix prompts/input_rewrite.md or re-run compile",
            ) from exc
        return str(rendered)

    if "{" in text and "}" in text:
        try:
            return text.format(**context)
        except (KeyError, ValueError, IndexError):
            pass

    stripped = text.rstrip()
    if not stripped:
        return user_message
    return f"{stripped}\n\n{user_message}"


def preprocess_user_text(template: str | None, user_message: str) -> str:
    """Return *user_message* unchanged when *template* is ``None``."""
    if template is None:
        return user_message
    return apply_input_rewrite(template, user_message)


def preprocess_openai_messages(
    template: str | None,
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Preprocess every ``role=user`` content string in OpenAI-shaped messages."""
    if template is None:
        return messages
    out: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            out.append(message)
            continue
        role = message.get("role")
        content = message.get("content")
        if role == "user" and isinstance(content, str):
            updated = dict(message)
            updated["content"] = apply_input_rewrite(template, content)
            out.append(updated)
        else:
            out.append(message)
    return out
