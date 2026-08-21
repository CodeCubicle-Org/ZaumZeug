"""Load and run harness ``pipelines/`` YAML listed in ``serve.expose`` (E8-S01)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from zaumzeug.config.schemas import ServeExposeEntry

_PIPELINE_SUFFIXES = (".yaml", ".yml")


class PipelineExposeError(RuntimeError):
    """Raised when an exposed pipeline cannot be resolved, loaded, or run."""


def coerce_expose_entries(
    expose: Sequence[Any] | None,
) -> list[ServeExposeEntry]:
    """Normalize string ids and ``{id, path}`` maps into schema entries."""
    if not expose:
        return []
    entries: list[ServeExposeEntry] = []
    seen: set[str] = set()
    for item in expose:
        if isinstance(item, ServeExposeEntry):
            entry = item
        elif isinstance(item, str):
            entry = ServeExposeEntry(id=item)
        elif isinstance(item, Mapping):
            entry = ServeExposeEntry.model_validate(item)
        else:
            raise PipelineExposeError(
                "serve.expose entries must be pipeline ids or `{id, path}` maps"
            )
        if entry.id in seen:
            raise PipelineExposeError(
                f"duplicate serve.expose id {entry.id!r}"
            )
        seen.add(entry.id)
        entries.append(entry)
    return entries


def expose_entries_from_harness(harness_config: Any) -> list[ServeExposeEntry]:
    """Return ``serve.expose`` entries from a loaded :class:`HarnessConfig`."""
    serve = getattr(harness_config, "serve", None)
    if serve is None:
        return []
    raw = getattr(serve, "expose", None) or []
    return coerce_expose_entries(list(raw))


def pipeline_file_candidates(harness_dir: Path, entry: ServeExposeEntry) -> list[Path]:
    """Possible files for one expose entry (id shorthand or explicit path)."""
    root = Path(harness_dir)
    rel = entry.relative_path().replace("\\", "/").lstrip("./")
    candidates = [root / rel]
    stem = Path(rel).name
    if stem.endswith(_PIPELINE_SUFFIXES):
        base = stem.rsplit(".", 1)[0]
    else:
        base = stem
        candidates.append(root / "pipelines" / f"{base}.yaml")
        candidates.append(root / "pipelines" / f"{base}.yml")
    pipelines = root / "pipelines"
    candidates.extend(
        [
            pipelines / f"{base}.yaml",
            pipelines / f"{base}.yml",
            pipelines / base,
            pipelines / stem,
        ]
    )
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def resolve_pipeline_file(harness_dir: Path | str, entry: ServeExposeEntry) -> Path:
    """Return the YAML file for *entry* or raise :class:`PipelineExposeError`."""
    root = Path(harness_dir)
    found = next(
        (path for path in pipeline_file_candidates(root, entry) if path.is_file()),
        None,
    )
    if found is None:
        raise PipelineExposeError(
            f"Pipeline '{entry.id}' listed in serve.expose is missing under pipelines/ "
            f"(looked for {entry.relative_path()}). "
            f"Add the YAML file or remove it from serve.expose."
        )
    return found


def load_pipeline_yaml(path: Path | str) -> Any:
    """Deserialize a Haystack ``Pipeline`` from YAML."""
    from haystack import Pipeline

    yaml_path = Path(path)
    try:
        source = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PipelineExposeError(f"Cannot read pipeline YAML {yaml_path}: {exc}") from exc
    try:
        return Pipeline.loads(source)
    except Exception as exc:
        raise PipelineExposeError(
            f"Failed to load Haystack pipeline from {yaml_path}: {exc}"
        ) from exc


def _map_flat_query(source: str, query: str, extra: Mapping[str, Any] | None) -> dict[str, Any]:
    """Map a user query onto YAML ``inputs:`` (Hayhooks IO) when declared."""
    payload: dict[str, Any] = dict(extra or {})
    payload.setdefault("query", query)
    try:
        from hayhooks.server.utils.yaml_pipeline_wrapper import (
            _map_flat_inputs_to_components,
        )
        from hayhooks.server.utils.yaml_utils import get_inputs_outputs_from_yaml
    except ImportError:
        return payload

    try:
        resolved = get_inputs_outputs_from_yaml(source)
        inputs = resolved.get("inputs") or {}
    except Exception:
        return payload
    if not inputs:
        return payload
    mapped = _map_flat_inputs_to_components(payload, inputs)
    if mapped:
        return mapped
    return payload


def run_pipeline_query(
    pipeline: Any,
    query: str,
    *,
    source_yaml: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run *pipeline* with a user *query* (Hayhooks-style flat or component map)."""
    data: dict[str, Any]
    if source_yaml:
        data = _map_flat_query(source_yaml, query, extra)
    else:
        data = dict(extra or {})
        data.setdefault("query", query)

    try:
        return pipeline.run(data)
    except Exception:
        # Common RAG shape: retriever.query without YAML inputs.
        try:
            return pipeline.run({"retriever": {"query": query}})
        except Exception as exc:
            raise PipelineExposeError(
                f"Pipeline run failed for query {query!r}: {exc}"
            ) from exc


def format_pipeline_output(result: Mapping[str, Any]) -> str:
    """Flatten a Haystack ``Pipeline.run`` result into agent-readable text."""
    chunks: list[str] = []
    for component_data in result.values():
        if not isinstance(component_data, Mapping):
            continue
        documents = component_data.get("documents")
        if isinstance(documents, list):
            for doc in documents:
                content = getattr(doc, "content", None)
                if content:
                    chunks.append(str(content))
        prompt = component_data.get("prompt")
        if isinstance(prompt, str) and prompt.strip():
            chunks.append(prompt.strip())
        replies = component_data.get("replies")
        if isinstance(replies, list):
            for reply in replies:
                text = getattr(reply, "text", None) or str(reply)
                if text:
                    chunks.append(str(text))
        answers = component_data.get("answers")
        if isinstance(answers, list):
            for answer in answers:
                data = getattr(answer, "data", None)
                if data:
                    chunks.append(str(data))
    if chunks:
        return "\n\n".join(chunks)
    return str(result)


def select_rag_entry(
    entries: Sequence[ServeExposeEntry],
) -> ServeExposeEntry | None:
    """Prefer a RAG-named expose row; otherwise the first listed pipeline."""
    if not entries:
        return None
    for entry in entries:
        blob = f"{entry.id} {entry.relative_path()}".lower()
        if "rag" in blob:
            return entry
    return entries[0]


def load_rag_pipeline(
    harness_dir: Path | str,
    entries: Sequence[ServeExposeEntry],
) -> tuple[Any, ServeExposeEntry, str]:
    """Load the RAG (or first) exposed pipeline. Raises if none listed."""
    entry = select_rag_entry(entries)
    if entry is None:
        raise PipelineExposeError(
            "search_docs requires a RAG pipeline listed in serve.expose "
            "(e.g. id: rag_pipeline, path: pipelines/rag.yaml)"
        )
    path = resolve_pipeline_file(harness_dir, entry)
    source = path.read_text(encoding="utf-8")
    pipeline = load_pipeline_yaml(path)
    return pipeline, entry, source
