# Story: E4-S02a / E4.2
"""E4-S02a — Compile LM preflight before GEPA (no optimizer invocation)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zaumzeug.compile.gepa_runner import (
    GepaPreflightError,
    invoke_gepa,
    preflight_compile_lms,
)
from zaumzeug.config.models import AgentModelsConfig
from zaumzeug.config.resolver import resolve_agent_compile


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _layout(
    tmp_path: Path,
    *,
    agent_yaml: dict,
    models: dict,
    harness_name: str = "example",
    agent_name: str = "researcher",
) -> tuple[Path, Path]:
    harness_dir = tmp_path / "usr-harnesses" / harness_name
    agent_dir = harness_dir / "agents" / agent_name
    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    _write_yaml(agent_dir / "agents-models.yaml", models)
    return harness_dir, agent_dir


def test_e4_s02a_ac4_missing_lm_keys_actionable_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: Missing registry ids or .env keys fail with actionable errors (no GEPA)."""
    gepa_calls: list[object] = []

    def _gepa_spy(*args: object, **kwargs: object) -> None:
        gepa_calls.append((args, kwargs))
        raise AssertionError("GEPA must not run when LM preflight fails")

    monkeypatch.setattr(
        "zaumzeug.compile.gepa_runner.invoke_gepa",
        _gepa_spy,
    )

    # --- Missing model id from registry ---
    harness_dir, _ = _layout(
        tmp_path / "missing-id",
        agent_yaml={
            "name": "researcher",
            "default_model_id": "mock",
            "compile": {
                "module": "modules.researcher:ResearchModule",
                "task_model_id": "does-not-exist",
                "reflection_model_id": "mock",
            },
        },
        models={
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    resolution = resolve_agent_compile(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
    )
    registry = AgentModelsConfig.model_validate(
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        }
    )

    with pytest.raises(GepaPreflightError) as missing_id_info:
        preflight_compile_lms(
            resolution,
            registry=registry,
            project_root=tmp_path / "missing-id",
            environ={},
        )

    missing_msg = str(missing_id_info.value)
    assert "does-not-exist" in missing_msg
    assert "registry" in missing_msg.lower()
    assert missing_id_info.value.suggestion is not None
    assert gepa_calls == []

    # --- Live provider without API key ---
    harness_dir2, _ = _layout(
        tmp_path / "missing-key",
        agent_yaml={
            "name": "researcher",
            "default_model_id": "live",
            "compile": {
                "module": "modules.researcher:ResearchModule",
                "task_model_id": "live",
                "reflection_model_id": "live",
            },
        },
        models={
            "default_model_id": "live",
            "models": {
                "live": {"provider": "openai", "model": "gpt-4o-mini"},
            },
        },
    )
    resolution2 = resolve_agent_compile(
        harness_dir2,
        harness_name="example",
        agent_name="researcher",
    )
    registry2 = AgentModelsConfig.model_validate(
        {
            "default_model_id": "live",
            "models": {
                "live": {"provider": "openai", "model": "gpt-4o-mini"},
            },
        }
    )

    with pytest.raises(GepaPreflightError) as missing_key_info:
        preflight_compile_lms(
            resolution2,
            registry=registry2,
            project_root=tmp_path / "missing-key",
            environ={},
        )

    key_msg = str(missing_key_info.value)
    assert "OPENAI_API_KEY" in key_msg
    assert "live" in key_msg
    assert missing_key_info.value.suggestion is not None
    assert ".env" in missing_key_info.value.suggestion or "mock" in (
        missing_key_info.value.suggestion or ""
    ).lower()
    assert gepa_calls == []

    # Confirm invoke_gepa remains a hard no-op boundary for this story.
    with pytest.raises(RuntimeError, match="E4-S02b"):
        invoke_gepa()
    assert gepa_calls == []
