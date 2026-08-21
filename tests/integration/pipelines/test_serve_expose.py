# Story: E8-S01 / E8.1
"""E8-S01 — Pipeline exposure via ``serve.expose``."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from haystack import Document, Pipeline
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore

from zaumzeug.config import ConfigValidationError, HarnessConfig, load_harness
from zaumzeug.runtime.factory import RuntimeFactoryError, build_agent_tools
from zaumzeug.runtime.pipelines import coerce_expose_entries
from zaumzeug.runtime.tools.search_docs import SearchDocs
from zaumzeug.runtime.workflow import run_workflow
from zaumzeug.serve.runner import prepare_serve

ECHO_PIPELINE_YAML = """\
components:
  prompt:
    init_parameters:
      required_variables:
      - query
      template: 'Query: {{ query }}'
      variables: null
    type: haystack.components.builders.prompt_builder.PromptBuilder
connections: []
inputs:
  query: prompt.query
outputs:
  prompt: prompt.prompt
"""


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _minimal_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    port: int = 1416,
    expose: list | None = None,
    pipeline_id: str = "echo",
    pipeline_yaml: str = ECHO_PIPELINE_YAML,
    builtin: list[str] | None = None,
    stages: list[dict] | None = None,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    serve: dict = {"hayhooks": {"port": port}}
    if expose is not None:
        serve["expose"] = expose
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": harness_name, "serve": serve},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {
            "entry": "researcher",
            "stages": stages or [{"agent": "researcher"}],
        },
    )
    agent_dir = harness_dir / "agents" / "researcher"
    agent_yaml: dict = {
        "name": "researcher",
        "default_model_id": "mock",
        "agent": {"system_prompt": "prompts/system.md"},
    }
    if builtin:
        agent_yaml["tools"] = {"builtin": builtin}
    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("You are a researcher.", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    if expose:
        pipe_path = harness_dir / "pipelines" / f"{pipeline_id}.yaml"
        pipe_path.parent.mkdir(parents=True, exist_ok=True)
        pipe_path.write_text(pipeline_yaml, encoding="utf-8")
        # Object-form path may differ from id.yaml
        for item in expose:
            if isinstance(item, dict) and item.get("path"):
                extra = harness_dir / str(item["path"])
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text(pipeline_yaml, encoding="utf-8")
    return harness_dir


def test_e8_s01_expose_schema_accepts_string_and_object(tmp_path: Path) -> None:
    """Phase 4 schema: string ids and ``{id, path}`` maps both validate."""
    string_path = _write_yaml(
        tmp_path / "string.yaml",
        {
            "name": "example",
            "serve": {
                "hayhooks": {"port": 1416},
                "expose": ["summarize", "rag_pipeline"],
            },
        },
    )
    string_cfg = load_harness(string_path)
    assert string_cfg.serve is not None
    assert [row.id for row in string_cfg.serve.expose] == ["summarize", "rag_pipeline"]
    assert string_cfg.serve.expose[0].relative_path() == "pipelines/summarize.yaml"

    object_path = _write_yaml(
        tmp_path / "object.yaml",
        {
            "name": "example",
            "serve": {
                "hayhooks": {"port": 1416},
                "expose": [{"id": "rag_pipeline", "path": "pipelines/rag.yaml"}],
            },
        },
    )
    object_cfg = load_harness(object_path)
    assert object_cfg.serve is not None
    assert object_cfg.serve.expose[0].id == "rag_pipeline"
    assert object_cfg.serve.expose[0].relative_path() == "pipelines/rag.yaml"

    entries = coerce_expose_entries(["echo", {"id": "rag_pipeline", "path": "pipelines/rag.yaml"}])
    assert [e.id for e in entries] == ["echo", "rag_pipeline"]


def test_e8_s01_ac1_pipelines_registered_from_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: User ``pipelines/`` YAML listed in ``serve.expose`` is registered."""
    project_root = tmp_path / "project"
    _minimal_harness(
        project_root,
        expose=[{"id": "echo", "path": "pipelines/echo.yaml"}],
        pipeline_id="echo",
    )
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    prepared = prepare_serve("example", project_root=project_root)
    assert "echo" in prepared.exposed_pipeline_ids

    client = TestClient(prepared.app)
    models = client.get("/v1/models")
    assert models.status_code == 200
    model_ids = {item["id"] for item in models.json()["data"]}
    assert "example" in model_ids


def test_e8_s01_ac4_post_pipeline_run_endpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: ``POST /{pipeline}/run`` executes the exposed Haystack pipeline."""
    project_root = tmp_path / "project"
    _minimal_harness(project_root, expose=["echo"], pipeline_id="echo")
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    prepared = prepare_serve("example", project_root=project_root)
    client = TestClient(prepared.app)
    response = client.post("/echo/run", json={"query": "languages"})
    assert response.status_code == 200, response.text
    payload = response.json()
    result = payload.get("result", payload)
    text = str(result)
    assert "languages" in text
    assert "Query:" in text


def test_e8_s01_search_docs_attaches_when_rag_present(tmp_path: Path) -> None:
    """DoD: ``search_docs`` builtin attaches when a RAG pipeline is listed."""
    store = InMemoryDocumentStore()
    store.write_documents(
        [Document(content="Haystack pipelines retrieve then generate.")]
    )
    pipeline = Pipeline()
    pipeline.add_component(
        "retriever",
        InMemoryBM25Retriever(document_store=store),
    )
    tool = SearchDocs(pipeline)
    out = tool.run(query="pipelines")
    assert "Haystack" in out["documents"]

    harness_dir = tmp_path / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": "example",
            "serve": {
                "hayhooks": {"port": 1416},
                "expose": [{"id": "rag_pipeline", "path": "pipelines/rag.yaml"}],
            },
        },
    )
    (harness_dir / "pipelines").mkdir(parents=True)
    (harness_dir / "pipelines" / "rag.yaml").write_text(
        ECHO_PIPELINE_YAML,
        encoding="utf-8",
    )
    harness = HarnessConfig.model_validate(
        yaml.safe_load((harness_dir / "harness.yaml").read_text(encoding="utf-8"))
    )
    tools = build_agent_tools(
        {"tools": {"builtin": ["search_docs"]}},
        workspace=harness_dir,
        harness_config=harness,
    )
    assert any(getattr(tool, "name", None) == "search_docs" for tool in tools)


def test_e8_s01_search_docs_requires_expose(tmp_path: Path) -> None:
    """``search_docs`` fails clearly when no RAG pipeline is listed."""
    with pytest.raises(RuntimeFactoryError, match="serve.expose"):
        build_agent_tools(
            {"tools": {"builtin": ["search_docs"]}},
            workspace=tmp_path,
            harness_config=HarnessConfig(name="empty"),
        )


def test_e8_s01_workflow_invokes_exposed_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline stages in ``workflow.yaml`` run the exposed Haystack YAML."""
    project_root = tmp_path / "project"
    _minimal_harness(
        project_root,
        expose=["echo"],
        pipeline_id="echo",
        stages=[{"agent": "researcher"}, {"pipeline": "echo"}],
    )
    monkeypatch.setattr(
        "zaumzeug.runtime.workflow.find_project_root",
        lambda start=None: project_root,
    )
    result = run_workflow(
        "example",
        user_input="batch-query",
        project_root=project_root,
    )
    kinds = [stage.kind for stage in result.stages]
    assert kinds == ["agent", "pipeline"]
    assert result.stages[-1].stage_id == "echo"
    assert "batch-query" in result.stages[-1].output
    assert result.final_output == result.stages[-1].output


def test_e8_s01_ac2_rag_pattern_documented() -> None:
    """AC-2: user-docs RAG path documents retriever → prompt → generator."""
    repo = Path(__file__).resolve().parents[3]
    live = (repo / "user-docs" / "guides" / "pipelines.md").read_text(encoding="utf-8")
    template = (
        repo / "install" / "templates" / "user-docs" / "guides" / "pipelines.md"
    ).read_text(encoding="utf-8")
    for text in (live, template):
        assert "retriever" in text.lower()
        assert "prompt" in text.lower()
        assert "generator" in text.lower()
        assert "serve.expose" in text
        assert "POST /{pipeline}/run" in text or "POST /{id}/run" in text
        assert "rag_pipeline" in text or "pipelines/rag.yaml" in text
