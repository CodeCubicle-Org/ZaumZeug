# Story: E3-S01 / E3.1
# Story: E3-S02 / E3.2 (AC-4 chat completions shape)
# Story: E3-S07 (partial — full HTTP contract lands with zaumzeug serve)
"""OpenAI REST contract helpers and serve smoke (E3-S01 AC-8, E3-S02 AC-4)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from haystack.dataclasses import ChatMessage

from zaumzeug.config.models import AgentModelsConfig
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.serve.runner import prepare_serve

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


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _contract_harness(project_root: Path) -> Path:
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
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
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("You are a researcher.", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    return harness_dir


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


def test_e3_s02_ac4_chat_completions_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: ``POST /v1/chat/completions`` returns OpenAI-shaped JSON."""
    project_root = tmp_path / "project"
    _contract_harness(project_root)
    monkeypatch.setattr(
        "zaumzeug.serve.validate.find_project_root",
        lambda start=None: project_root,
    )

    prepared = prepare_serve("example", project_root=project_root)
    client = TestClient(prepared.app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "example",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["model"] == "example"
    assert payload["choices"]
    message = payload["choices"][0]["message"]
    assert message["role"] == "assistant"
    assert isinstance(message["content"], str)
    assert message["content"]
