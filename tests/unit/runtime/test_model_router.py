# Story: E3-S05 / E3.5
"""E3-S05 — Mock model profile."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from haystack.dataclasses import ChatMessage

from zaumzeug.config.models import AgentModelsConfig
from zaumzeug.integrations.mock import MockChatGenerator, load_fixture_response
from zaumzeug.runtime.model_router import PROVIDERS, ModelRouter

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "responses"
MODELS_EXAMPLE = (
    REPO_ROOT / "install" / "templates" / "config" / "models.example.yaml"
)

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

_LIVE_LLM_ENV_VARS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "HARNESS_LIVE_LLM",
)


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
