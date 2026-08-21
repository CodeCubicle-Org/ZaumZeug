"""Builtin ``search_docs`` tool — query a RAG pipeline listed in ``serve.expose`` (E8-S01)."""

from __future__ import annotations

from typing import Any

from haystack import component
from haystack.tools import ComponentTool

from zaumzeug.runtime.pipelines import (
    PipelineExposeError,
    format_pipeline_output,
    run_pipeline_query,
)


class SearchDocsError(ValueError):
    """Raised when ``search_docs`` cannot query the attached RAG pipeline."""


@component
class SearchDocs:
    """Haystack component that runs the harness RAG pipeline for a query."""

    def __init__(
        self,
        pipeline: Any,
        *,
        source_yaml: str | None = None,
        pipeline_id: str = "rag_pipeline",
    ) -> None:
        self._pipeline = pipeline
        self._source_yaml = source_yaml
        self._pipeline_id = pipeline_id

    @component.output_types(documents=str)
    def run(self, query: str) -> dict[str, str]:
        text = query.strip()
        if not text:
            raise SearchDocsError("search_docs requires a non-empty query")
        try:
            result = run_pipeline_query(
                self._pipeline,
                text,
                source_yaml=self._source_yaml,
            )
        except PipelineExposeError as exc:
            raise SearchDocsError(str(exc)) from exc
        formatted = format_pipeline_output(result)
        return {"documents": formatted or "(no documents)"}


def search_docs_tool(
    *,
    pipeline: Any,
    source_yaml: str | None = None,
    pipeline_id: str = "rag_pipeline",
) -> ComponentTool:
    """Return a Haystack ``ComponentTool`` for the builtin ``search_docs`` id."""
    return ComponentTool(
        component=SearchDocs(
            pipeline,
            source_yaml=source_yaml,
            pipeline_id=pipeline_id,
        ),
        name="search_docs",
        description=(
            "Search indexed documents via the harness RAG pipeline "
            f"({pipeline_id}). Pass a natural-language query; returns matching "
            "document text for grounded answers."
        ),
    )


def build_search_docs_tool(**kwargs: Any) -> ComponentTool:
    """Catalog factory entry for ``search_docs``."""
    pipeline = kwargs.get("pipeline")
    if pipeline is None:
        raise SearchDocsError(
            "search_docs requires a RAG pipeline listed in serve.expose "
            "(retriever → prompt → generator under pipelines/)"
        )
    allowed = {
        key: kwargs[key]
        for key in ("pipeline", "source_yaml", "pipeline_id")
        if key in kwargs
    }
    return search_docs_tool(**allowed)
