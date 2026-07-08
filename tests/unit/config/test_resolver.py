# Story: E2-S03 / E2.3
"""E2-S03 — Runtime agent resolution rules."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zaumzeug.config.resolver import (
    ARTIFACT_MANIFEST,
    AgentResolutionError,
    RuntimeSource,
    resolve_agent_compile,
    resolve_agent_serve,
    resolve_serve_entry,
)


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _layout(
    tmp_path: Path,
    *,
    agent_name: str = "researcher",
    agent_yaml: dict,
    workflow: dict | None = None,
    harness_name: str = "example",
) -> tuple[Path, Path]:
    harness_dir = tmp_path / "usr-harnesses" / harness_name
    agent_dir = harness_dir / "agents" / agent_name
    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    if workflow is not None:
        _write_yaml(harness_dir / "workflow.yaml", workflow)
    return harness_dir, agent_dir


def test_e2_s03_ac1_serve_artifact_over_system_prompt(tmp_path: Path) -> None:
    """AC-1: serve prefers artifact over system_prompt when manifest is valid."""
    harness_dir, agent_dir = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "agent": {
                "artifact": "artifacts/current",
                "system_prompt": "prompts/system.md",
            },
        },
    )
    artifact_dir = agent_dir / "artifacts" / "current"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / ARTIFACT_MANIFEST).write_text("{}", encoding="utf-8")
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("hand-authored", encoding="utf-8")

    result = resolve_agent_serve(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
    )

    assert result.source is RuntimeSource.ARTIFACT
    assert result.path == artifact_dir.resolve()
    assert result.agent_name == "researcher"
    assert result.harness_name == "example"


def test_e2_s03_ac1_serve_system_prompt_fallback(tmp_path: Path) -> None:
    """AC-1: serve falls back to system_prompt when no artifact is configured."""
    harness_dir, agent_dir = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "agent": {
                "system_prompt": "prompts/system.md",
            },
        },
    )
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("You are a researcher.", encoding="utf-8")

    result = resolve_agent_serve(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
    )

    assert result.source is RuntimeSource.SYSTEM_PROMPT
    assert result.path == prompt_path.resolve()


def test_e2_s03_ac1_serve_both_missing_actionable_error(tmp_path: Path) -> None:
    """AC-1: serve fails with actionable error when artifact and prompt are absent."""
    harness_dir, _ = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "tools": {"builtin": ["web_fetch"]},
        },
    )

    with pytest.raises(AgentResolutionError) as exc_info:
        resolve_agent_serve(
            harness_dir,
            harness_name="example",
            agent_name="researcher",
        )

    err = exc_info.value
    assert err.harness_name == "example"
    assert err.agent_name == "researcher"
    assert "runtime path" in str(err).lower()
    assert err.suggestion is not None
    assert "compile" in err.suggestion or "system_prompt" in err.suggestion


def test_e2_s03_ac2_compile_requires_module(tmp_path: Path) -> None:
    """AC-2: compile requires compile.module in agent.yaml."""
    harness_dir, _ = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
        },
    )

    with pytest.raises(AgentResolutionError) as exc_info:
        resolve_agent_compile(
            harness_dir,
            harness_name="example",
            agent_name="researcher",
        )

    assert "compile.module" in str(exc_info.value)

    harness_dir2, _ = _layout(
        tmp_path / "with-module",
        agent_yaml={
            "name": "researcher",
            "compile": {"module": "modules.researcher:ResearchModule"},
        },
    )
    result = resolve_agent_compile(
        harness_dir2,
        harness_name="example",
        agent_name="researcher",
    )
    assert result.compile_module == "modules.researcher:ResearchModule"


def test_e2_s03_ac3_serve_entry_from_workflow(tmp_path: Path) -> None:
    """AC-3: interactive serve resolves the workflow entry agent."""
    harness_dir, agent_dir = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
        },
        workflow={
            "entry": "researcher",
            "stages": [{"agent": "researcher"}],
        },
    )
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("entry agent prompt", encoding="utf-8")

    result = resolve_serve_entry(harness_dir, harness_name="example")

    assert result.agent_name == "researcher"
    assert result.source is RuntimeSource.SYSTEM_PROMPT
    assert result.path == prompt_path.resolve()


def test_e2_s03_ac4_error_names_path_and_suggests_fix(tmp_path: Path) -> None:
    """AC-4: errors name the missing path and suggest a fix."""
    harness_dir, agent_dir = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "agent": {
                "artifact": "artifacts/current",
            },
        },
    )
    (agent_dir / "artifacts" / "current").mkdir(parents=True)

    with pytest.raises(AgentResolutionError) as exc_info:
        resolve_agent_serve(
            harness_dir,
            harness_name="example",
            agent_name="researcher",
        )

    message = str(exc_info.value)
    err = exc_info.value
    manifest_path = agent_dir / "artifacts" / "current" / ARTIFACT_MANIFEST
    assert str(manifest_path) in message or ARTIFACT_MANIFEST in message
    assert str(agent_dir / "agent.yaml") in message
    assert err.suggestion is not None
    assert "compile" in err.suggestion.lower()
