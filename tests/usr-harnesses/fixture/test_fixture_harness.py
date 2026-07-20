# Story: E3-S06
"""E3-S06 — Minimal fixture harness under ``tests/usr-harnesses/fixture/``."""

from __future__ import annotations

from pathlib import Path

import yaml

from zaumzeug.config import load_agent_config, load_harness, load_workflow
from zaumzeug.config.models import AgentModelsConfig

FIXTURE_HARNESS = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
RESPONSES_DIR = REPO_ROOT / "tests" / "fixtures" / "responses"


def test_e3_s06_ac2_minimal_harness_valid() -> None:
    """AC-2: fixture harness is minimal valid Phase 1 YAML; mock fixtures present."""
    harness = load_harness(FIXTURE_HARNESS / "harness.yaml")
    assert harness.name == "fixture"
    assert harness.serve is not None
    assert harness.serve.hayhooks is not None
    assert harness.serve.hayhooks.port == 1416

    workflow = load_workflow(FIXTURE_HARNESS)
    assert workflow.entry == "agent"
    assert len(workflow.stages) == 1
    assert workflow.stages[0].agent == "agent"

    agent_dir = FIXTURE_HARNESS / "agents" / "agent"
    agent = load_agent_config(agent_dir / "agent.yaml")
    assert agent.name == "agent"
    assert agent.default_model_id == "mock"
    assert (agent_dir / "prompts" / "system.md").is_file()

    models_raw = yaml.safe_load(
        (agent_dir / "agents-models.yaml").read_text(encoding="utf-8")
    )
    registry = AgentModelsConfig.model_validate(models_raw)
    assert registry.default_model_id == "mock"
    assert "mock" in registry.models
    assert registry.models["mock"].provider == "mock"
    assert registry.models["mock"].model == "harness-fixture"

    fixture_file = RESPONSES_DIR / "harness-fixture.txt"
    assert fixture_file.is_file()
    assert fixture_file.read_text(encoding="utf-8").strip()
