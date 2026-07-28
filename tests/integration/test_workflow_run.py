# Story: E3-S08 / E3.6
"""E3-S08 — ``zaumzeug run`` serial workflow integration tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from haystack.dataclasses import ChatMessage

from zaumzeug.cli import main
from zaumzeug.runtime.workflow import (
    WorkflowError,
    build_stage_messages,
    run_workflow,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_RESEARCHER = (
    "Mock harness fixture response for deterministic CI and local serve smoke tests."
)
FIXTURE_REVIEWER = (
    "Alternate mock fixture response for ModelRouter model_id override contract tests."
)


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_agent(
    harness_dir: Path,
    *,
    name: str,
    model: str = "harness-fixture",
    prompt: str | None = None,
    missing_prompt: bool = False,
) -> Path:
    agent_dir = harness_dir / "agents" / name
    agent_yaml: dict[str, Any] = {
        "name": name,
        "default_model_id": "mock",
        "agent": {"system_prompt": "prompts/system.md"},
    }
    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    if not missing_prompt:
        prompt_path = agent_dir / "prompts" / "system.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(
            prompt or f"You are {name}.",
            encoding="utf-8",
        )
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": model},
            },
        },
    )
    return agent_dir


def _two_agent_harness(
    project_root: Path,
    *,
    stages: list[dict[str, str]] | None = None,
    missing_reviewer_prompt: bool = False,
) -> Path:
    """Scaffold a two-agent serial harness under *project_root*."""
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {
            "entry": "researcher",
            "stages": stages
            or [
                {"agent": "researcher"},
                {"agent": "reviewer"},
            ],
        },
    )
    _write_agent(harness_dir, name="researcher", model="harness-fixture")
    _write_agent(
        harness_dir,
        name="reviewer",
        model="alt-fixture",
        missing_prompt=missing_reviewer_prompt,
    )
    # Point mock fixtures at the real repo fixture directory.
    fixtures = project_root / "tests" / "fixtures" / "responses"
    fixtures.mkdir(parents=True)
    for name in ("harness-fixture.txt", "alt-fixture.txt"):
        src = REPO_ROOT / "tests" / "fixtures" / "responses" / name
        (fixtures / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return harness_dir


def test_e3_s08_ac1_serial_stage_order(tmp_path: Path) -> None:
    """AC-1: Executes workflow.yaml stages in order (serial only)."""
    project_root = tmp_path / "project"
    _two_agent_harness(project_root)

    result = run_workflow(
        "example",
        user_input="research topic",
        project_root=project_root,
    )

    assert [stage.stage_id for stage in result.stages] == ["researcher", "reviewer"]
    assert [stage.kind for stage in result.stages] == ["agent", "agent"]
    assert result.stages[0].output == FIXTURE_RESEARCHER
    assert result.stages[1].output == FIXTURE_REVIEWER
    assert result.final_output == FIXTURE_REVIEWER


def test_e3_s08_ac2_per_agent_models_registry(tmp_path: Path) -> None:
    """AC-2: Each agent stage loads its own merged agents-models.yaml."""
    project_root = tmp_path / "project"
    _two_agent_harness(project_root)

    result = run_workflow(
        "example",
        user_input="topic",
        project_root=project_root,
    )

    assert result.stages[0].model_id == "mock"
    assert result.stages[1].model_id == "mock"
    # Distinct fixture models prove per-agent registry resolution.
    assert result.stages[0].output == FIXTURE_RESEARCHER
    assert result.stages[1].output == FIXTURE_REVIEWER
    assert result.stages[0].output != result.stages[1].output


def test_e3_s08_ac3_stage_output_forwarded(tmp_path: Path) -> None:
    """AC-3: Prior stage output is prepended as a user message before workflow input."""
    project_root = tmp_path / "project"
    _two_agent_harness(project_root)

    # Unit shape from the story sketch.
    messages = build_stage_messages(
        "workflow input",
        prior_output="prior assistant text",
    )
    assert messages == [
        {"role": "user", "content": "prior assistant text"},
        {"role": "user", "content": "workflow input"},
    ]

    captured: list[list[ChatMessage]] = []
    import zaumzeug.runtime.workflow as workflow_mod

    original_build = workflow_mod.build_agent_bundle

    def _tracking_build(*args: Any, **kwargs: Any) -> Any:
        built = original_build(*args, **kwargs)
        original_run = built.agent.run

        def _tracked_run(messages: list[ChatMessage], **run_kwargs: Any) -> Any:
            captured.append(list(messages))
            return original_run(messages, **run_kwargs)

        built.agent.run = _tracked_run  # type: ignore[method-assign]
        return built

    with patch.object(workflow_mod, "build_agent_bundle", _tracking_build):
        run_workflow(
            "example",
            user_input="workflow input",
            project_root=project_root,
        )

    assert len(captured) == 2
    # First stage: only the workflow input.
    assert [m.text for m in captured[0] if m.is_from("user")] == ["workflow input"]
    # Second stage: prior assistant output prepended, then workflow input.
    user_texts = [m.text for m in captured[1] if m.is_from("user")]
    assert user_texts == [FIXTURE_RESEARCHER, "workflow input"]


def test_e3_s08_ac5_from_stage_partial_run(tmp_path: Path) -> None:
    """AC-5: --from <stage> runs the partial workflow from that stage."""
    project_root = tmp_path / "project"
    _two_agent_harness(project_root)

    result = run_workflow(
        "example",
        user_input="topic",
        from_stage="reviewer",
        project_root=project_root,
    )

    assert [stage.stage_id for stage in result.stages] == ["reviewer"]
    assert result.final_output == FIXTURE_REVIEWER


def test_e3_s08_ac6_actionable_agent_error(tmp_path: Path) -> None:
    """AC-6: Resolution errors fail fast with harness + agent name."""
    project_root = tmp_path / "project"
    _two_agent_harness(project_root, missing_reviewer_prompt=True)

    with pytest.raises(WorkflowError) as excinfo:
        run_workflow(
            "example",
            user_input="topic",
            project_root=project_root,
        )

    message = str(excinfo.value)
    assert "example" in message
    assert "reviewer" in message
    assert excinfo.value.harness_name == "example"
    assert excinfo.value.agent_name == "reviewer"


def test_e3_s08_ac7_two_agent_mock_workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-7: Integration — two-agent serial workflow with mock models via CLI."""
    project_root = tmp_path / "project"
    _two_agent_harness(project_root)
    monkeypatch.chdir(project_root)
    monkeypatch.setattr(
        "zaumzeug.runtime.workflow.find_project_root",
        lambda start=None: project_root,
    )

    with pytest.raises(SystemExit) as excinfo:
        main(["run", "example", "--input", "research the topic"])
    assert excinfo.value.code == 0


def test_e3_s08_dod_example_single_stage(tmp_path: Path) -> None:
    """DoD: zaumzeug run example works with a single-stage workflow."""
    project_root = tmp_path / "project"
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    _write_agent(harness_dir, name="researcher", model="harness-fixture")
    fixtures = project_root / "tests" / "fixtures" / "responses"
    fixtures.mkdir(parents=True)
    src = REPO_ROOT / "tests" / "fixtures" / "responses" / "harness-fixture.txt"
    (fixtures / "harness-fixture.txt").write_text(
        src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = run_workflow(
        "example",
        user_input="hello",
        project_root=project_root,
    )
    assert len(result.stages) == 1
    assert result.stages[0].stage_id == "researcher"
    assert result.final_output == FIXTURE_RESEARCHER
