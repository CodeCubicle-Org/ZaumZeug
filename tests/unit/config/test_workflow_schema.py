# Story: E2-S07 / E2.7
"""E2-S07 — `workflow.yaml` schema (serial)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zaumzeug.config import ConfigValidationError, WorkflowConfig, load_workflow

# Architecture §6.6 — Phase 1 example workflow
EXAMPLE_WORKFLOW: dict = {
    "entry": "researcher",
    "stages": [{"agent": "researcher"}],
}


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _harness(
    tmp_path: Path,
    *,
    workflow: dict | None = None,
    agents: dict[str, dict] | None = None,
) -> Path:
    harness_dir = tmp_path / "usr-harnesses" / "example"
    _write_yaml(harness_dir / "workflow.yaml", workflow or EXAMPLE_WORKFLOW)
    for folder_name, agent_yaml in (agents or {"researcher": {"name": "researcher"}}).items():
        _write_yaml(harness_dir / "agents" / folder_name / "agent.yaml", agent_yaml)
    return harness_dir


def test_e2_s07_ac1_requires_entry_and_stages(tmp_path: Path) -> None:
    """AC-1: workflow.yaml requires entry and non-empty stages list."""
    harness_dir = tmp_path / "usr-harnesses" / "broken"
    harness_dir.mkdir(parents=True)

    missing_entry = _write_yaml(harness_dir / "workflow.yaml", {"stages": [{"agent": "a"}]})
    with pytest.raises(ConfigValidationError) as exc_info:
        load_workflow(harness_dir)
    assert "entry" in str(exc_info.value).lower()

    missing_stages = _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": []},
    )
    with pytest.raises(ConfigValidationError) as missing_stages_exc:
        load_workflow(harness_dir)
    message = str(missing_stages_exc.value)
    assert "stages" in message.lower()


def test_e2_s07_ac2_agent_or_pipeline_stage(tmp_path: Path) -> None:
    """AC-2: each stage is exactly one of agent or pipeline."""
    harness_dir = _harness(
        tmp_path,
        workflow={
            "entry": "researcher",
            "stages": [
                {"agent": "researcher"},
                {"pipeline": "dedupe"},
            ],
        },
    )

    workflow = load_workflow(harness_dir)
    assert workflow.stages[0].agent == "researcher"
    assert workflow.stages[1].pipeline == "dedupe"

    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{}]},
    )
    with pytest.raises(ConfigValidationError) as neither_exc:
        load_workflow(harness_dir)
    assert "agent" in str(neither_exc.value).lower() or "pipeline" in str(
        neither_exc.value
    ).lower()

    _write_yaml(
        harness_dir / "workflow.yaml",
        {
            "entry": "researcher",
            "stages": [{"agent": "researcher", "pipeline": "dedupe"}],
        },
    )
    with pytest.raises(ConfigValidationError) as both_exc:
        load_workflow(harness_dir)
    assert "agent" in str(both_exc.value).lower() or "pipeline" in str(both_exc.value).lower()


def test_e2_s07_ac3_unknown_agent_ref_fails(tmp_path: Path) -> None:
    """AC-3: every agent ref resolves to agents/<name>/agent.yaml."""
    harness_dir = _harness(
        tmp_path,
        workflow={
            "entry": "missing-agent",
            "stages": [{"agent": "researcher"}],
        },
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_workflow(harness_dir)

    message = str(exc_info.value)
    assert "missing-agent" in message
    assert "agents" in message


def test_e2_s07_ac4_unique_agent_names(tmp_path: Path) -> None:
    """AC-4: agent names unique within harness; folder matches agent.yaml name."""
    harness_dir = _harness(
        tmp_path,
        agents={
            "researcher": {"name": "reviewer"},
            "reviewer": {"name": "reviewer"},
        },
    )

    with pytest.raises(ConfigValidationError) as mismatch_exc:
        load_workflow(harness_dir)
    mismatch_msg = str(mismatch_exc.value)
    assert "folder" in mismatch_msg.lower() or "name" in mismatch_msg.lower()

    harness_dir = _harness(
        tmp_path / "dup",
        agents={
            "alpha": {"name": "alpha"},
            "beta": {"name": "alpha"},
        },
    )
    with pytest.raises(ConfigValidationError) as dup_exc:
        load_workflow(harness_dir)
    assert "duplicate" in str(dup_exc.value).lower()


def test_e2_s07_ac5_parallelism_phase_hint(tmp_path: Path) -> None:
    """AC-5: parallelism field fails in Phase 1 with phase hint."""
    harness_dir = _harness(
        tmp_path,
        workflow={
            "entry": "researcher",
            "stages": [{"agent": "researcher", "parallelism": 4}],
        },
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_workflow(harness_dir)

    message = str(exc_info.value)
    assert "parallelism" in message
    assert "Phase 2" in message


def test_e2_s07_ac6_example_workflow_valid(tmp_path: Path) -> None:
    """AC-6: example harness workflow.yaml from §6.6 passes validation."""
    harness_dir = _harness(
        tmp_path,
        workflow=EXAMPLE_WORKFLOW,
        agents={
            "researcher": {
                "name": "researcher",
                "default_model_id": "mock",
                "agent": {"system_prompt": "prompts/system.md"},
                "tools": {"builtin": ["web_fetch"]},
            },
        },
    )

    workflow = load_workflow(harness_dir)

    assert isinstance(workflow, WorkflowConfig)
    assert workflow.entry == "researcher"
    assert len(workflow.stages) == 1
    assert workflow.stages[0].agent == "researcher"
