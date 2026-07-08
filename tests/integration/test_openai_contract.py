# Story: E3-S01 / E3.1
# Story: E3-S07 (partial — full HTTP contract lands with zaumzeug serve)
"""OpenAI REST contract routing helpers (E3-S01 AC-8)."""

from __future__ import annotations

from pathlib import Path

from haystack.dataclasses import ChatMessage

from zaumzeug.config.models import AgentModelsConfig
from zaumzeug.runtime.model_router import ModelRouter

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "responses"


def resolve_chat_completion_model_id(
    *,
    harness_name: str,
    request_model: str | None,
    request_model_id: str | None,
    router: ModelRouter,
) -> str:
    """Resolve registry model_id for an OpenAI-shaped chat completion request.

    The OpenAI ``model`` field carries the harness/agent identity for clients.
    An optional ``model_id`` extension selects the LLM from the agent registry.
    """
    del harness_name, request_model
    return router.resolve_model_id(request_model_id)


def test_e3_s01_ac8_request_model_id_override() -> None:
    """AC-8: optional request model_id selects LLM; harness name is not the registry key."""
    registry = AgentModelsConfig.model_validate(
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
    router = ModelRouter(registry, fixture_dir=FIXTURE_DIR)
    harness_name = "example-researcher"

    resolved = resolve_chat_completion_model_id(
        harness_name=harness_name,
        request_model=harness_name,
        request_model_id="alt",
        router=router,
    )
    assert resolved == "alt"
    assert harness_name != resolved

    entry = router.get_entry(resolved)
    result = router.run([ChatMessage.from_user("contract smoke")], model_id=resolved)
    assert entry.provider == "mock"
    assert result["replies"][0].text

    default_resolved = resolve_chat_completion_model_id(
        harness_name=harness_name,
        request_model=harness_name,
        request_model_id=None,
        router=router,
    )
    assert default_resolved == "mock"
