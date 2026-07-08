# Story: E3-S01 / E3.1
# Story: E3-S05 / E3.5
"""E3-S01 ModelRouter and E3-S05 mock model profile."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml
from haystack.dataclasses import ChatMessage

from zaumzeug.config.models import AgentModelsConfig, load_merged_agent_models
from zaumzeug.integrations.haystack import PROVIDERS as HAYSTACK_PROVIDERS
from zaumzeug.integrations.mock import MockChatGenerator, load_fixture_response
from zaumzeug.runtime.model_router import PROVIDERS, ModelRouter, ModelRouterError

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "responses"
MODELS_EXAMPLE = (
    REPO_ROOT / "install" / "templates" / "config" / "models.example.yaml"
)
SDK_SRC = REPO_ROOT / "src" / "zaumzeug"

MOCK_REGISTRY = AgentModelsConfig.model_validate(
    {
        "default_model_id": "mock",
        "models": {
            "mock": {
                "provider": "mock",
                "model": "harness-fixture",
            },
        },
    }
)

MULTI_MODEL_REGISTRY = AgentModelsConfig.model_validate(
    {
        "default_model_id": "mock",
        "models": {
            "mock": {
                "provider": "mock",
                "model": "harness-fixture",
            },
            "alt": {
                "provider": "mock",
                "model": "harness-fixture",
            },
        },
    }
)

_LIVE_LLM_ENV_VARS = (
    "OPENAI_API_KEY",
    "OPENAI_API_BASE",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "HARNESS_LIVE_LLM",
)

_FORBIDDEN_MODEL_NAME_FRAGMENTS = (
    "gpt-4",
    "gpt-3",
    "claude-",
    "claude_",
    "gemini-",
)


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _merged_registry_layout(tmp_path: Path) -> tuple[Path, Path]:
    project_root = tmp_path / "project"
    harness_dir = project_root / "usr-harnesses" / "example"
    harness_dir.mkdir(parents=True)

    _write_yaml(
        project_root / "config" / "models.yaml",
        {
            "default_model_id": "default",
            "models": {
                "default": {
                    "provider": "mock",
                    "model": "harness-fixture",
                },
            },
        },
    )
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "models": "models.yaml"},
    )
    _write_yaml(
        harness_dir / "models.yaml",
        {
            "models": {
                "fast": {
                    "provider": "mock",
                    "model": "harness-fixture",
                },
            },
        },
    )
    agent_dir = harness_dir / "agents" / "researcher"
    agent_dir.mkdir(parents=True)
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "fast",
            "models": {
                "fast": {
                    "provider": "mock",
                    "model": "harness-fixture",
                },
            },
        },
    )
    return project_root, harness_dir


# --- E3-S01 -----------------------------------------------------------------


def test_e3_s01_ac1_config_model_id_and_request_override(tmp_path: Path) -> None:
    """AC-1: router reads merged agents-models.yaml; request model_id overrides default."""
    project_root, harness_dir = _merged_registry_layout(tmp_path)
    merged = load_merged_agent_models(
        project_root=project_root,
        harness_dir=harness_dir,
        harness_models_path=harness_dir / "models.yaml",
        agent_name="researcher",
    )
    router = ModelRouter(merged, fixture_dir=FIXTURE_DIR)

    assert router.resolve_model_id() == "fast"
    assert router.get_entry().provider == "mock"

    assert router.resolve_model_id("default") == "default"
    assert router.get_entry("default").model == "harness-fixture"

    result = router.run([ChatMessage.from_user("hello")], model_id="fast")
    assert result["replies"][0].text


def test_e3_s01_ac2_lazy_build_generator() -> None:
    """AC-2: ChatGenerator is built only on first use."""
    build_calls: list[str] = []

    def _tracking_build(entry: Any, **kwargs: Any) -> MockChatGenerator:
        build_calls.append(entry.model)
        return MockChatGenerator(entry.model, fixture_dir=FIXTURE_DIR)

    router = ModelRouter(MOCK_REGISTRY, fixture_dir=FIXTURE_DIR)
    with patch(
        "zaumzeug.runtime.model_router.build_chat_generator",
        side_effect=_tracking_build,
    ):
        assert not build_calls
        gen_a = router.build_generator("mock")
        gen_b = router.build_generator("mock")

    assert len(build_calls) == 1
    assert gen_a is gen_b


def test_e3_s01_ac3_openrouter_provider_path() -> None:
    """AC-3: openrouter resolves to OpenRouterChatGenerator import path."""
    registry = AgentModelsConfig.model_validate(
        {
            "default_model_id": "cloud",
            "models": {
                "cloud": {
                    "provider": "openrouter",
                    "model": "anthropic/claude-sonnet-4",
                },
            },
        }
    )
    fake_generator = MagicMock(name="OpenRouterChatGenerator")
    fake_module = MagicMock()
    fake_module.OpenRouterChatGenerator.return_value = fake_generator

    router = ModelRouter(registry)
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=False):
        with patch("importlib.import_module", return_value=fake_module) as import_mock:
            generator = router.build_generator("cloud")

    import_mock.assert_called_once_with(
        "haystack_integrations.components.generators.openrouter"
    )
    fake_module.OpenRouterChatGenerator.assert_called_once()
    call_kwargs = fake_module.OpenRouterChatGenerator.call_args.kwargs
    assert call_kwargs["model"] == "anthropic/claude-sonnet-4"
    assert generator is fake_generator


def test_e3_s01_ac4_openai_compatible_local_provider_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: openai_compatible uses OpenAIChatGenerator with api_base_url."""
    registry = AgentModelsConfig.model_validate(
        {
            "default_model_id": "local",
            "models": {
                "local": {
                    "provider": "openai_compatible",
                    "model": "loaded-local-model",
                    "api_base_url": "http://localhost:1234/v1",
                },
            },
        }
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    router = ModelRouter(registry)
    generator = router.build_generator("local")

    from haystack.components.generators.chat import OpenAIChatGenerator

    assert isinstance(generator, OpenAIChatGenerator)
    assert generator.model == "loaded-local-model"
    assert generator.api_base_url == "http://localhost:1234/v1"


def test_e3_s01_ac4_openai_compatible_env_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: OPENAI_API_BASE in .env can supply api_base_url."""
    registry = AgentModelsConfig.model_validate(
        {
            "default_model_id": "local",
            "models": {
                "local": {
                    "provider": "openai_compatible",
                    "model": "loaded-local-model",
                },
            },
        }
    )
    monkeypatch.setenv("OPENAI_API_BASE", "http://localhost:1234/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    router = ModelRouter(registry)
    generator = router.build_generator("local")

    assert generator.api_base_url == "http://localhost:1234/v1"


def test_e3_s01_ac4_openai_compatible_requires_base_url() -> None:
    """AC-4: openai_compatible fails fast without api_base_url."""
    registry = AgentModelsConfig.model_validate(
        {
            "default_model_id": "local",
            "models": {
                "local": {
                    "provider": "openai_compatible",
                    "model": "loaded-local-model",
                },
            },
        }
    )
    router = ModelRouter(registry)
    with pytest.raises(ModelRouterError, match="api_base_url"):
        router.build_generator("local")


def test_e3_s01_ac5_generator_cache_per_provider_endpoint() -> None:
    """AC-5: distinct api_base_url values do not share a cache entry."""
    registry = AgentModelsConfig.model_validate(
        {
            "default_model_id": "a",
            "models": {
                "a": {
                    "provider": "openai_compatible",
                    "model": "same-model",
                    "api_base_url": "http://localhost:1234/v1",
                },
                "b": {
                    "provider": "openai_compatible",
                    "model": "same-model",
                    "api_base_url": "http://localhost:11434/v1",
                },
            },
        }
    )
    router = ModelRouter(registry)
    gen_a = router.build_generator("a")
    gen_b = router.build_generator("b")

    assert gen_a is not gen_b
    assert len(router._generator_cache) == 2

    gen_a_again = router.build_generator("a")
    assert gen_a_again is gen_a


def test_e3_s01_ac6_missing_package_install_hint() -> None:
    """AC-6: missing provider package yields pip install hint."""
    registry = AgentModelsConfig.model_validate(
        {
            "default_model_id": "cloud",
            "models": {
                "cloud": {
                    "provider": "openrouter",
                    "model": "anthropic/claude-sonnet-4",
                },
            },
        }
    )
    router = ModelRouter(registry)
    with patch(
        "importlib.import_module",
        side_effect=ImportError("No module named 'haystack_integrations'"),
    ):
        with pytest.raises(ModelRouterError, match="pip install openrouter-haystack"):
            router.build_generator("cloud")


def test_e3_s01_ac6_phase_gated_native_provider() -> None:
    """AC-6: native cloud providers fail with Phase 2 hint in Phase 1."""
    registry = AgentModelsConfig.model_validate(
        {
            "default_model_id": "cloud",
            "models": {
                "cloud": {
                    "provider": "openai",
                    "model": "configured-model",
                },
            },
        }
    )
    router = ModelRouter(registry)
    with pytest.raises(ModelRouterError, match="Phase 2"):
        router.build_generator("cloud")


def test_e3_s01_ac7_no_hardcoded_model_names() -> None:
    """AC-7: SDK source does not hardcode commercial model names."""
    scanned_files = [
        SDK_SRC / "runtime" / "model_router.py",
        SDK_SRC / "integrations" / "haystack.py",
    ]
    for path in scanned_files:
        source = path.read_text(encoding="utf-8").lower()
        for fragment in _FORBIDDEN_MODEL_NAME_FRAGMENTS:
            assert fragment not in source, f"{path.name} must not hardcode {fragment!r}"

    assert "mock" in PROVIDERS
    assert PROVIDERS == HAYSTACK_PROVIDERS


# --- E3-S05 -----------------------------------------------------------------


def test_e3_s05_ac1_mock_provider_in_registry() -> None:
    """AC-1: models.yaml defines mock provider per Architecture §6.6."""
    assert MODELS_EXAMPLE.is_file(), "install/templates/config/models.example.yaml must exist"

    data = yaml.safe_load(MODELS_EXAMPLE.read_text(encoding="utf-8"))
    assert data["default_model_id"] == "mock"
    assert data["models"]["mock"]["provider"] == "mock"
    assert data["models"]["mock"]["model"] == "harness-fixture"

    assert "mock" in PROVIDERS
    assert PROVIDERS["mock"] == ("zaumzeug.integrations.mock", "MockChatGenerator")

    router = ModelRouter(MOCK_REGISTRY, fixture_dir=FIXTURE_DIR)
    entry = router.get_entry("mock")
    assert entry.provider == "mock"
    assert entry.model == "harness-fixture"


def test_e3_s05_ac2_returns_fixture_response() -> None:
    """AC-2: canned responses from tests/fixtures/responses/."""
    expected = load_fixture_response("harness-fixture", fixture_dir=FIXTURE_DIR)

    router = ModelRouter(MOCK_REGISTRY, fixture_dir=FIXTURE_DIR)
    result = router.run([ChatMessage.from_user("hello")], model_id="mock")

    replies = result["replies"]
    assert len(replies) == 1
    assert replies[0].text == expected
    assert "Mock harness fixture response" in replies[0].text

    generator = MockChatGenerator("harness-fixture", fixture_dir=FIXTURE_DIR)
    direct = generator.run("ping")
    assert direct["replies"][0].text == expected


def test_e3_s05_ac3_ci_uses_mock_exclusively(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-3: default CI contract uses mock exclusively — no live API keys required."""
    for name in _LIVE_LLM_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    data = yaml.safe_load(MODELS_EXAMPLE.read_text(encoding="utf-8"))
    assert data["default_model_id"] == "mock"
    providers = {entry["provider"] for entry in data["models"].values()}
    assert providers == {"mock"}, "shipped models.example.yaml must be mock-only for CI"

    router = ModelRouter(MOCK_REGISTRY, fixture_dir=FIXTURE_DIR)
    result = router.run([ChatMessage.from_user("ci smoke")])
    assert result["replies"][0].text

    workflows_dir = REPO_ROOT / ".github" / "workflows"
    if workflows_dir.is_dir():
        for workflow in workflows_dir.glob("*.yml"):
            content = workflow.read_text(encoding="utf-8")
            assert "HARNESS_LIVE_LLM=1" not in content, (
                f"{workflow.name} must not enable live LLM e2e in default CI"
            )


def test_e3_s05_ac4_no_provider_package_required() -> None:
    """AC-4: mock works without provider Haystack integration packages."""
    module_path, class_name = PROVIDERS["mock"]
    assert module_path.startswith("zaumzeug.")
    assert "haystack_integrations" not in module_path

    router = ModelRouter(MOCK_REGISTRY, fixture_dir=FIXTURE_DIR)
    generator = router.build_generator("mock")
    assert type(generator).__name__ == class_name
    assert type(generator).__module__ == module_path

    result = router.run([ChatMessage.from_user("no keys needed")])
    assert result["replies"][0].text
