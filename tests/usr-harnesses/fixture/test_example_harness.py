# Story: E3-S04 / E3.4
"""E3-S04 — Example harness (general research agent) fixture tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from zaumzeug.config import load_harness, load_workflow

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_HARNESS = REPO_ROOT / "usr-harnesses" / "example"
TEMPLATE_HARNESS = (
    REPO_ROOT / "install" / "templates" / "usr-harnesses" / "example"
)

_RAG_KEYS = frozenset(
    {
        "rag",
        "retriever",
        "document_store",
        "embedding",
        "embeddings",
        "vector_store",
        "index",
        "indexing",
    }
)


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _collect_keys(data: object, *, found: set[str] | None = None) -> set[str]:
    keys = found if found is not None else set()
    if isinstance(data, dict):
        for key, value in data.items():
            keys.add(str(key).lower())
            _collect_keys(value, found=keys)
    elif isinstance(data, list):
        for item in data:
            _collect_keys(item, found=keys)
    return keys


def test_e3_s04_ac1_researcher_agent_layout() -> None:
    """AC-1: example uses agents/researcher/ per Architecture §6.6."""
    agent_dir = EXAMPLE_HARNESS / "agents" / "researcher"
    assert agent_dir.is_dir()
    assert (agent_dir / "agent.yaml").is_file()
    assert (agent_dir / "agents-models.yaml").is_file()
    assert (agent_dir / "prompts" / "system.md").is_file()

    harness = load_harness(EXAMPLE_HARNESS / "harness.yaml")
    assert harness.name == "example"

    agent = _load_yaml(agent_dir / "agent.yaml")
    assert agent["name"] == "researcher"
    assert agent["agent"]["system_prompt"] == "prompts/system.md"
    assert "web_fetch" in agent.get("tools", {}).get("builtin", [])


def test_e3_s04_ac2_workflow_yaml_single_stage() -> None:
    """AC-2: workflow.yaml has one stage (researcher)."""
    workflow = load_workflow(EXAMPLE_HARNESS)
    assert workflow.entry == "researcher"
    assert len(workflow.stages) == 1
    assert workflow.stages[0].agent == "researcher"
    assert workflow.stages[0].pipeline is None


def test_e3_s04_ac3_agents_models_mock_default() -> None:
    """AC-3: agents/researcher/agents-models.yaml defaults to mock."""
    registry = _load_yaml(
        EXAMPLE_HARNESS / "agents" / "researcher" / "agents-models.yaml"
    )
    assert registry["default_model_id"] == "mock"
    assert registry["models"]["mock"]["provider"] == "mock"
    assert registry["models"]["mock"]["model"] == "harness-fixture"

    agent = _load_yaml(EXAMPLE_HARNESS / "agents" / "researcher" / "agent.yaml")
    assert agent["default_model_id"] == "mock"


def test_e3_s04_ac5_no_rag_sections() -> None:
    """AC-5: example harness has no RAG sections until Epic E8."""
    yaml_paths = list(EXAMPLE_HARNESS.rglob("*.yaml")) + list(
        EXAMPLE_HARNESS.rglob("*.yml")
    )
    assert yaml_paths
    for path in yaml_paths:
        keys = _collect_keys(_load_yaml(path))
        rag_hits = sorted(keys & _RAG_KEYS)
        assert not rag_hits, f"{path.relative_to(REPO_ROOT)} has RAG keys: {rag_hits}"

    assert not (EXAMPLE_HARNESS / "pipelines").exists()


def test_e3_s04_ac6_install_template_mirrors_example() -> None:
    """AC-6 (manual support): install template tree mirrors usr-harnesses/example."""
    required = [
        "harness.yaml",
        "workflow.yaml",
        "models.yaml",
        "agents/researcher/agent.yaml",
        "agents/researcher/agents-models.yaml",
        "agents/researcher/prompts/system.md",
        "agents/researcher/modules/researcher.py",
        "agents/researcher/data/train.jsonl",
        "agents/researcher/data/val.jsonl",
    ]
    for relative in required:
        assert (TEMPLATE_HARNESS / relative).is_file(), relative
        assert (EXAMPLE_HARNESS / relative).is_file(), relative
