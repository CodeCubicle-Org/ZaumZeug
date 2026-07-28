"""Export GEPA-optimized DSPy module state to Haystack-compatible artifacts (E4-S03a).

Maps ``dump_state()`` into ``prompts/system.md``, optional ``prompts/input_rewrite.md``,
``agent.json`` (tool descriptions + pipeline Jinja field templates), and
``artifact-manifest.json`` (canonical). Legacy ``manifest.json`` is accepted when
loading during migration.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "AGENT_JSON_REL",
    "ARTIFACT_MANIFEST_NAME",
    "EXPORT_VERSION",
    "ExportError",
    "ExportPaths",
    "ExportResult",
    "INPUT_REWRITE_REL",
    "LEGACY_MANIFEST_NAME",
    "SYSTEM_PROMPT_REL",
    "compute_module_hash",
    "dump_module_state",
    "export_optimized_module",
    "find_artifact_manifest",
    "map_dump_state_to_haystack",
]

ARTIFACT_MANIFEST_NAME = "artifact-manifest.json"
LEGACY_MANIFEST_NAME = "manifest.json"
EXPORT_VERSION = 1

SYSTEM_PROMPT_REL = "prompts/system.md"
INPUT_REWRITE_REL = "prompts/input_rewrite.md"
AGENT_JSON_REL = "agent.json"

_FALLBACK_SYSTEM_PROMPT = (
    "You are a helpful assistant. Follow the compiled instructions carefully."
)

# Keep in sync with zaumzeug.compile.gepa_runner.module_has_input_rewrite hints.
_INPUT_REWRITE_HINTS = frozenset(
    {
        "input_rewrite",
        "clarify",
        "rewrite",
        "clarify_rewrite",
        "input_clarify",
    }
)


class ExportError(RuntimeError):
    """Haystack export from DSPy state failed."""

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


@dataclass(frozen=True, slots=True)
class ExportPaths:
    """Relative paths written under an artifact run directory."""

    system_prompt: str = SYSTEM_PROMPT_REL
    input_rewrite: str | None = None
    agent_json: str = AGENT_JSON_REL
    tools: str | None = None
    templates: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ExportResult:
    """Outcome of writing Haystack export files into an artifact run dir."""

    artifact_dir: Path
    manifest_path: Path
    module_hash: str
    paths: ExportPaths
    has_input_rewrite: bool
    agent_json: dict[str, Any]
    manifest: dict[str, Any]


def find_artifact_manifest(artifact_dir: Path | str) -> Path | None:
    """Locate the artifact manifest, preferring the canonical name.

    Accepts legacy ``manifest.json`` during migration (Architecture §5.3).
    Returns ``None`` when neither file exists.
    """
    root = Path(artifact_dir)
    canonical = root / ARTIFACT_MANIFEST_NAME
    if canonical.is_file():
        return canonical
    legacy = root / LEGACY_MANIFEST_NAME
    if legacy.is_file():
        return legacy
    return None


def dump_module_state(module: Any) -> dict[str, Any]:
    """Return ``module.dump_state()`` as a dict, or raise :class:`ExportError`."""
    dump = getattr(module, "dump_state", None)
    if not callable(dump):
        raise ExportError(
            "Optimized module has no dump_state(); cannot export Haystack artifacts",
            suggestion="Ensure compile.module is a dspy.Module with dump_state()",
        )
    try:
        state = dump()
    except Exception as exc:
        raise ExportError(
            f"dump_state() failed: {exc}",
            suggestion="Inspect the optimized DSPy module predictors and retry compile",
        ) from exc
    if not isinstance(state, dict):
        return {"state": state}
    return state


def compute_module_hash(state: dict[str, Any]) -> str:
    """Stable SHA-256 of canonical JSON for ``dump_state()`` output."""
    payload = json.dumps(state, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def map_dump_state_to_haystack(
    state: dict[str, Any],
    *,
    module: Any | None = None,
) -> tuple[str, ExportPaths, dict[str, Any], str | None]:
    """Map ``dump_state()`` to system prompt, paths, agent.json body, rewrite text.

    Primary predictors (non-rewrite) contribute instructions → ``system_prompt`` and
    field descriptions → pipeline Jinja templates. Optional clarify/rewrite predictors
    contribute ``input_rewrite`` only when present.
    """
    rewrite_names = _rewrite_predictor_names(state, module=module)
    system_chunks: list[str] = []
    templates: dict[str, str] = {}
    tools: list[dict[str, Any]] = []
    rewrite_text: str | None = None

    for name, pred_state in state.items():
        if not isinstance(pred_state, dict):
            continue
        signature = pred_state.get("signature")
        if not isinstance(signature, dict):
            signature = {}
        instructions = _as_text(signature.get("instructions"))
        fields = signature.get("fields") if isinstance(signature.get("fields"), list) else []

        if name in rewrite_names or _name_looks_like_rewrite(str(name)):
            if instructions and rewrite_text is None:
                rewrite_text = instructions
            continue

        if instructions:
            system_chunks.append(instructions)

        for index, field_info in enumerate(fields):
            if not isinstance(field_info, dict):
                continue
            prefix = _as_text(field_info.get("prefix")) or f"field_{index}"
            description = _as_text(field_info.get("description"))
            if description:
                templates[_template_key(str(name), prefix)] = _to_jinja_template(description)

        tools.extend(_tools_from_predictor_state(pred_state))

    if module is not None:
        tools.extend(_tools_from_module(module))
        tools = _dedupe_tools(tools)

    system_prompt = "\n\n".join(chunk for chunk in system_chunks if chunk.strip())
    if not system_prompt.strip():
        system_prompt = _FALLBACK_SYSTEM_PROMPT

    paths = ExportPaths(
        system_prompt=SYSTEM_PROMPT_REL,
        input_rewrite=INPUT_REWRITE_REL if rewrite_text else None,
        agent_json=AGENT_JSON_REL,
        templates=dict(sorted(templates.items())),
    )
    agent_json: dict[str, Any] = {
        "export_version": EXPORT_VERSION,
        "system_prompt": paths.system_prompt,
        "tools": tools,
        "templates": paths.templates,
    }
    if paths.input_rewrite is not None:
        agent_json["input_rewrite"] = paths.input_rewrite

    return system_prompt, paths, agent_json, rewrite_text


def export_optimized_module(
    artifact_dir: Path | str,
    module: Any,
    *,
    run_id: str,
    module_ref: str | None = None,
    harness_name: str | None = None,
    agent_name: str | None = None,
    gepa_metadata: dict[str, Any] | None = None,
    write_legacy_alias: bool = False,
) -> ExportResult:
    """Write Haystack export files into ``artifacts/<run_id>/``.

    Always writes canonical ``artifact-manifest.json``. When *write_legacy_alias* is
    true, also writes ``manifest.json`` (migration aid). Loaders accept either name
    via :func:`find_artifact_manifest`.
    """
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    state = dump_module_state(module)
    module_hash = compute_module_hash(state)
    system_prompt, paths, agent_json, rewrite_text = map_dump_state_to_haystack(
        state,
        module=module,
    )

    prompts_dir = artifact_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / paths.system_prompt).write_text(
        _ensure_trailing_newline(system_prompt),
        encoding="utf-8",
    )

    has_rewrite = paths.input_rewrite is not None
    if has_rewrite and rewrite_text is not None and paths.input_rewrite is not None:
        (artifact_dir / paths.input_rewrite).write_text(
            _ensure_trailing_newline(rewrite_text),
            encoding="utf-8",
        )

    (artifact_dir / paths.agent_json).write_text(
        json.dumps(agent_json, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    path_map: dict[str, str] = {
        "system_prompt": paths.system_prompt,
        "agent_json": paths.agent_json,
    }
    if paths.input_rewrite is not None:
        path_map["input_rewrite"] = paths.input_rewrite

    manifest: dict[str, Any] = {
        "export_version": EXPORT_VERSION,
        "run_id": run_id,
        "module_hash": module_hash,
        "module_ref": module_ref,
        "harness_name": harness_name,
        "agent_name": agent_name,
        "paths": path_map,
        "has_input_rewrite": has_rewrite,
        # GEPA optimized the template offline; runtime applies fixed exported text only.
        "optimization_target": "template",
        "legacy_manifest_alias": LEGACY_MANIFEST_NAME,
    }
    if gepa_metadata:
        manifest["gepa"] = gepa_metadata

    manifest_path = artifact_dir / ARTIFACT_MANIFEST_NAME
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    if write_legacy_alias:
        (artifact_dir / LEGACY_MANIFEST_NAME).write_text(manifest_text, encoding="utf-8")

    return ExportResult(
        artifact_dir=artifact_dir,
        manifest_path=manifest_path,
        module_hash=module_hash,
        paths=paths,
        has_input_rewrite=has_rewrite,
        agent_json=agent_json,
        manifest=manifest,
    )


def _rewrite_predictor_names(state: dict[str, Any], *, module: Any | None) -> set[str]:
    names: set[str] = set()
    for name in state:
        if _name_looks_like_rewrite(str(name)):
            names.add(str(name))
    if module is None:
        return names
    named = getattr(module, "named_predictors", None)
    if not callable(named):
        return names
    for name, _pred in named():
        if _name_looks_like_rewrite(str(name)):
            names.add(str(name))
    return names


def _name_looks_like_rewrite(name: str) -> bool:
    lowered = name.lower()
    return lowered in _INPUT_REWRITE_HINTS or "rewrite" in lowered or "clarify" in lowered


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _template_key(predictor: str, prefix: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", prefix.strip().rstrip(":")).strip("_").lower()
    return f"{predictor}.{slug or 'field'}"


def _to_jinja_template(description: str) -> str:
    """Normalize ``${var}`` field placeholders to Jinja ``{{ var }}`` for pipelines."""
    text = description.strip()
    if "{{" in text:
        return text

    def _repl(match: re.Match[str]) -> str:
        return "{{ " + match.group(1) + " }}"

    return re.sub(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}", _repl, text)


def _tools_from_predictor_state(pred_state: dict[str, Any]) -> list[dict[str, Any]]:
    tools_raw = pred_state.get("tools")
    if not isinstance(tools_raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in tools_raw:
        mapped = _normalize_tool(item)
        if mapped is not None:
            out.append(mapped)
    return out


def _tools_from_module(module: Any) -> list[dict[str, Any]]:
    tools_attr = getattr(module, "tools", None)
    if tools_attr is None:
        return []
    if callable(tools_attr):
        try:
            tools_attr = tools_attr()
        except Exception:
            return []
    if not isinstance(tools_attr, (list, tuple)):
        return []
    out: list[dict[str, Any]] = []
    for item in tools_attr:
        mapped = _normalize_tool(item)
        if mapped is not None:
            out.append(mapped)
    return out


def _normalize_tool(item: Any) -> dict[str, Any] | None:
    if isinstance(item, dict):
        name = item.get("name") or item.get("tool_name")
        description = item.get("description") or item.get("desc") or ""
        if name:
            return {"name": str(name), "description": str(description)}
        return None
    name = getattr(item, "name", None) or getattr(item, "__name__", None)
    if not name:
        return None
    description = getattr(item, "description", None) or getattr(item, "__doc__", None) or ""
    return {"name": str(name), "description": str(description).strip()}


def _dedupe_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = tool["name"]
        if name in seen:
            continue
        seen.add(name)
        out.append(tool)
    return out


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"
