# Story: E3-S01 / E3.1
# Story: E3-S02 / E3.2 (AC-4 chat completions shape)
# Story: E3-S07 / OpenAI REST contract
"""OpenAI REST contract helpers and HTTP contract tests (E3-S01 AC-8, E3-S02 AC-4, E3-S07)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from haystack.dataclasses import ChatMessage

from zaumzeug.config.models import AgentModelsConfig
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.runtime.tools.web_fetch import fetch_url
from zaumzeug.serve.runner import prepare_serve

from .conftest import write_contract_harness

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "responses"

_ALT_MODELS = {
    "default_model_id": "mock",
    "models": {
        "mock": {"provider": "mock", "model": "harness-fixture"},
        "alt": {"provider": "mock", "model": "alt-fixture"},
    },
}


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


def _contract_harness(project_root: Path) -> Path:
    """Legacy helper for E3-S02 TestClient smoke (port from yaml unused in-process)."""
    return write_contract_harness(project_root, port=1416)


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


def test_e3_s07_ac1_chat_completions_openai_shape(ephemeral_serve_url: str) -> None:
    """AC-1: ephemeral serve POST ``/v1/chat/completions`` returns OpenAI JSON shape."""
    response = httpx.post(
        f"{ephemeral_serve_url}/v1/chat/completions",
        json={
            "model": "example",
            "messages": [{"role": "user", "content": "hi"}],
        },
        timeout=10.0,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "choices" in payload
    assert payload["choices"]
    message = payload["choices"][0]["message"]
    assert message["role"] == "assistant"
    assert isinstance(message["content"], str)
    assert message["content"]


@pytest.mark.parametrize(
    "ephemeral_serve_url",
    [{"models": _ALT_MODELS}],
    indirect=True,
)
def test_e3_s07_ac2_request_model_id_override(ephemeral_serve_url: str) -> None:
    """AC-2: optional request ``model_id`` selects the ModelRouter registry entry."""
    default_response = httpx.post(
        f"{ephemeral_serve_url}/v1/chat/completions",
        json={
            "model": "example",
            "messages": [{"role": "user", "content": "default"}],
        },
        timeout=10.0,
    )
    assert default_response.status_code == 200
    default_content = default_response.json()["choices"][0]["message"]["content"]

    override_response = httpx.post(
        f"{ephemeral_serve_url}/v1/chat/completions",
        json={
            "model": "example",
            "model_id": "alt",
            "messages": [{"role": "user", "content": "override"}],
        },
        timeout=10.0,
    )
    assert override_response.status_code == 200
    override_payload = override_response.json()
    assert override_payload["model"] == "example"
    override_content = override_payload["choices"][0]["message"]["content"]

    assert "Alternate mock fixture" in override_content
    assert override_content != default_content
    assert "Mock harness fixture" in default_content


@pytest.mark.parametrize(
    "ephemeral_serve_url",
    [{"with_web_fetch": True}],
    indirect=True,
)
def test_e3_s07_ac3_no_network_mock_and_stub_fetch(ephemeral_serve_url: str) -> None:
    """AC-3: contract path uses mock LLM; stub ``web_fetch`` HTTP when tool invoked."""
    response = httpx.post(
        f"{ephemeral_serve_url}/v1/chat/completions",
        json={
            "model": "example",
            "messages": [{"role": "user", "content": "hi"}],
        },
        timeout=10.0,
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert isinstance(content, str)
    assert content

    with patch("zaumzeug.runtime.tools.web_fetch.is_public_host", return_value=True):
        with respx.mock(assert_all_called=True) as router:
            route = router.get("https://example.com/contract").mock(
                return_value=httpx.Response(200, text="stubbed-page")
            )
            fetched = fetch_url("https://example.com/contract")

    assert fetched == "stubbed-page"
    assert route.call_count == 1
