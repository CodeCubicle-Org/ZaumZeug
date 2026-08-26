# Story: E8-S06 / E8.6
"""E8-S06 — DeepEval production observe (opt-in Mode B)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import zaumzeug.eval.observe as observe_mod
from zaumzeug.eval.observe import (
    ProductionObserveHook,
    install_production_observe_hook,
    observe_enabled,
)


class _FakeAgent:
    def __init__(self, text: str = "observed reply") -> None:
        self._text = text
        self.run_calls = 0

    def run(self, messages: list[Any] | None = None, **kwargs: object) -> dict:
        del kwargs
        self.run_calls += 1
        last = SimpleNamespace(text=self._text, role="assistant")
        return {"last_message": last, "messages": [last]}


def test_e8_s06_ac1_observe_off_by_default() -> None:
    """AC-1: Production observe is opt-in only — not default for production."""
    assert observe_enabled(None) is False
    assert observe_enabled(SimpleNamespace(confident_ai=None)) is False
    assert (
        observe_enabled(
            SimpleNamespace(confident_ai=SimpleNamespace(enabled=False))
        )
        is False
    )
    assert (
        observe_enabled(SimpleNamespace(confident_ai=SimpleNamespace())) is False
    )


def test_e8_s06_ac2_observe_when_confident_ai_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: ``@observe`` wraps Agent.run when ``eval.confident_ai.enabled``."""
    assert (
        observe_enabled(
            SimpleNamespace(confident_ai=SimpleNamespace(enabled=True))
        )
        is True
    )

    observe_calls: list[dict[str, Any]] = []
    span_updates: list[Any] = []

    def fake_observe(*, name: str | None = None, **kwargs: object):
        del kwargs

        def decorator(fn):  # noqa: ANN001
            observe_calls.append({"name": name, "fn": fn})
            return fn

        return decorator

    def fake_update_current_span(**kwargs: object) -> None:
        span_updates.append(kwargs)

    class _FakeLLMTestCase:
        def __init__(self, *, input: str, actual_output: str) -> None:  # noqa: A002
            self.input = input
            self.actual_output = actual_output

    monkeypatch.setattr(
        observe_mod,
        "_load_observe_api",
        lambda: (fake_observe, fake_update_current_span, _FakeLLMTestCase),
    )

    agent = _FakeAgent()
    hook = install_production_observe_hook(agent, agent_name="researcher")
    assert hook.installed is True
    assert len(observe_calls) == 1
    assert observe_calls[0]["name"] == "researcher"

    user = SimpleNamespace(text="hello production", role="user")
    result = agent.run(messages=[user])
    assert result["last_message"].text == "observed reply"
    assert agent.run_calls == 1
    assert len(span_updates) == 1
    case = span_updates[0]["test_case"]
    assert case.input == "hello production"
    assert case.actual_output == "observed reply"


def test_e8_s06_observe_hook_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Installing the same hook twice does not double-wrap."""

    def fake_observe(*, name: str | None = None, **kwargs: object):
        del name, kwargs

        def decorator(fn):  # noqa: ANN001
            return fn

        return decorator

    monkeypatch.setattr(
        observe_mod,
        "_load_observe_api",
        lambda: (fake_observe, lambda **_: None, object),
    )

    agent = _FakeAgent()
    hook = ProductionObserveHook(agent="researcher")
    hook.install(agent)
    first = agent.run
    hook.install(agent)
    assert agent.run is first
