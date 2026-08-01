# Story: E8-S07 / E8.7
"""E8-S07 — Workflow run reliability integration (mock provider)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from zaumzeug.runtime.workflow import run_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _scaffold(project_root: Path) -> Path:
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": "example",
            "serve": {"hayhooks": {"port": 1416}},
            "runtime": {
                "retry": {
                    "max_attempts": 3,
                    "initial_delay_s": 0.01,
                    "backoff": 2.0,
                }
            },
        },
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"system_prompt": "prompts/system.md"},
        },
    )
    prompt = agent_dir / "prompts" / "system.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("You are a researcher.", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    fixtures = project_root / "tests" / "fixtures" / "responses"
    fixtures.mkdir(parents=True)
    src = REPO_ROOT / "tests" / "fixtures" / "responses" / "harness-fixture.txt"
    (fixtures / "harness-fixture.txt").write_text(
        src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return harness_dir


def test_e8_s07_ac2_fail_once_then_succeed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: first Agent.run fails, second succeeds (mock sleep)."""
    project_root = tmp_path / "project"
    _scaffold(project_root)
    sleeps: list[float] = []
    monkeypatch.setattr(
        "zaumzeug.runtime.workflow.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    import zaumzeug.runtime.workflow as workflow_mod

    original_build = workflow_mod.build_agent_bundle
    calls = {"n": 0}

    def _tracking_build(*args: Any, **kwargs: Any) -> Any:
        built = original_build(*args, **kwargs)
        original_run = built.agent.run

        def _flaky_run(messages: Any, **run_kwargs: Any) -> Any:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient provider error")
            return original_run(messages, **run_kwargs)

        built.agent.run = _flaky_run  # type: ignore[method-assign]
        return built

    with patch.object(workflow_mod, "build_agent_bundle", _tracking_build):
        result = run_workflow(
            "example",
            user_input="research topic",
            project_root=project_root,
        )

    assert calls["n"] == 2
    assert sleeps == [0.01]
    assert result.final_output
    assert result.stages[0].stage_id == "researcher"
