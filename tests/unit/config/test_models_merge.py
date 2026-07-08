# Story: E2-S02 / E2.2
"""E2-S02 — models.yaml three-tier deep merge."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from zaumzeug.config import ConfigValidationError, load_harness
from zaumzeug.config.models import (
    AgentModelsConfig,
    deep_merge,
    load_merged_agent_models,
    merge_model_registries,
)


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _layout(
    tmp_path: Path,
    *,
    global_models: dict | None = None,
    harness_models: dict | None = None,
    agent_models: dict,
    agent_name: str = "researcher",
    with_harness_ref: bool = True,
) -> tuple[Path, Path]:
    """Create project_root + harness_dir with optional global/harness/agent YAML."""
    project_root = tmp_path / "project"
    harness_dir = project_root / "usr-harnesses" / "example"
    harness_dir.mkdir(parents=True)

    if global_models is not None:
        _write_yaml(project_root / "config" / "models.yaml", global_models)

    if harness_models is not None:
        _write_yaml(harness_dir / "models.yaml", harness_models)

    harness_data: dict = {"name": "example"}
    if with_harness_ref and harness_models is not None:
        harness_data["models"] = "models.yaml"
    _write_yaml(harness_dir / "harness.yaml", harness_data)

    _write_yaml(
        harness_dir / "agents" / agent_name / "agents-models.yaml",
        agent_models,
    )
    return project_root, harness_dir


def test_e2_s02_ac1_global_harness_deep_merge(tmp_path: Path) -> None:
    """AC-1: Global config/models.yaml deep-merges with harness models.yaml."""
    project_root, harness_dir = _layout(
        tmp_path,
        global_models={
            "default_model_id": "default",
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
                "shared": {
                    "provider": "anthropic",
                    "model": "claude-3-haiku",
                },
            },
        },
        harness_models={
            "models": {
                "default": {
                    "generation_kwargs": {"temperature": 0.2},
                },
                "harness-only": {
                    "provider": "openai",
                    "model": "gpt-4o",
                },
            },
        },
        agent_models={
            "default_model_id": "default",
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "generation_kwargs": {"temperature": 0.2},
                },
                "harness-only": {
                    "provider": "openai",
                    "model": "gpt-4o",
                },
            },
        },
    )

    harness = load_harness(harness_dir / "harness.yaml")
    merged = load_merged_agent_models(
        project_root=project_root,
        harness_dir=harness_dir,
        harness_models_path=harness.models,
        agent_name="researcher",
    )

    assert merged.default_model_id == "default"
    assert "shared" in merged.models
    assert merged.models["shared"].provider == "anthropic"
    assert "harness-only" in merged.models
    assert merged.models["default"].generation_kwargs == {"temperature": 0.2}


def test_e2_s02_ac2_nested_dict_harness_wins(tmp_path: Path) -> None:
    """AC-2: Per-agent agents-models.yaml deep-merges over harness + global."""
    project_root, harness_dir = _layout(
        tmp_path,
        global_models={
            "default_model_id": "default",
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "generation_kwargs": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    },
                },
            },
        },
        harness_models={
            "models": {
                "default": {
                    "generation_kwargs": {
                        "temperature": 0.5,
                    },
                },
            },
        },
        agent_models={
            "default_model_id": "default",
            "models": {
                "default": {
                    "generation_kwargs": {
                        "temperature": 0.1,
                    },
                },
            },
        },
    )

    harness = load_harness(harness_dir / "harness.yaml")
    merged = load_merged_agent_models(
        project_root=project_root,
        harness_dir=harness_dir,
        harness_models_path=harness.models,
        agent_name="researcher",
    )

    kwargs = merged.models["default"].generation_kwargs
    assert kwargs is not None
    assert kwargs["temperature"] == 0.1
    assert kwargs["top_p"] == 0.9
    assert merged.models["default"].provider == "openai"
    assert merged.models["default"].model == "gpt-4o-mini"


def test_e2_s02_ac3_list_replace_not_append() -> None:
    """AC-3: Nested dicts merge recursively; lists in child replace parent lists."""
    base = {
        "models": {
            "default": {
                "generation_kwargs": {
                    "stop": ["\n", "END"],
                    "tags": ["alpha", "beta"],
                },
            },
        },
    }
    override = {
        "models": {
            "default": {
                "generation_kwargs": {
                    "stop": ["<|end|>"],
                },
            },
        },
    }

    merged = merge_model_registries(base, override)
    kwargs = merged["models"]["default"]["generation_kwargs"]
    assert kwargs["stop"] == ["<|end|>"]
    assert kwargs["tags"] == ["alpha", "beta"]

    # Harness-level nested dict wins over global for the same key path.
    global_layer = {
        "models": {
            "default": {
                "generation_kwargs": {"temperature": 0.7, "stop": ["\n"]},
            },
        },
    }
    harness_layer = {
        "models": {
            "default": {
                "generation_kwargs": {"temperature": 0.5},
            },
        },
    }
    tiered = merge_model_registries(global_layer, harness_layer)
    assert tiered["models"]["default"]["generation_kwargs"]["temperature"] == 0.5
    assert tiered["models"]["default"]["generation_kwargs"]["stop"] == ["\n"]


def test_e2_s02_ac4_same_model_id_override(tmp_path: Path) -> None:
    """AC-4: Child registry overrides parent for the same model_id key."""
    project_root, harness_dir = _layout(
        tmp_path,
        global_models={
            "default_model_id": "default",
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
        },
        harness_models={
            "models": {
                "default": {
                    "model": "gpt-4o",
                },
            },
        },
        agent_models={
            "default_model_id": "special",
            "models": {
                "default": {
                    "provider": "anthropic",
                },
                "special": {
                    "provider": "mock",
                    "model": "harness-fixture",
                },
            },
        },
    )

    harness = load_harness(harness_dir / "harness.yaml")
    merged = load_merged_agent_models(
        project_root=project_root,
        harness_dir=harness_dir,
        harness_models_path=harness.models,
        agent_name="researcher",
    )

    entry = merged.models["default"]
    assert entry.provider == "anthropic"
    assert entry.model == "gpt-4o"
    assert merged.default_model_id == "special"


def test_e2_s02_ac5_missing_default_model_id_fails(tmp_path: Path) -> None:
    """AC-5: default_model_id must exist in the agent's merged registry."""
    project_root, harness_dir = _layout(
        tmp_path,
        global_models={
            "default_model_id": "default",
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
        },
        harness_models=None,
        with_harness_ref=False,
        agent_models={
            "default_model_id": "missing-model",
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
        },
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_merged_agent_models(
            project_root=project_root,
            harness_dir=harness_dir,
            harness_models_path=None,
            agent_name="researcher",
        )

    message = str(exc_info.value)
    assert "missing-model" in message
    assert exc_info.value.field == "default_model_id"


def test_deep_merge_explicit_empty_dict_replaces() -> None:
    """Explicit empty dict in child replaces parent nested mapping."""
    base = {"generation_kwargs": {"temperature": 0.5, "top_p": 0.9}}
    override = {"generation_kwargs": {}}
    assert deep_merge(base, override) == {"generation_kwargs": {}}


def test_agent_models_config_rejects_secrets_in_yaml() -> None:
    """Secrets never loaded from YAML — .env only (story DoD)."""
    with pytest.raises(ValidationError):
        AgentModelsConfig.model_validate(
            {
                "default_model_id": "default",
                "models": {
                    "default": {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "api_key": "sk-secret",
                    },
                },
            }
        )
