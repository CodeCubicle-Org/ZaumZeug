# Story: E4-S02b / E4.2
"""E4-S02b — GEPA runner unit tests (metric, LMs, budget).

Also retains E4-S02a AC-4 preflight coverage.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zaumzeug.compile.gepa_runner import (
    CompileLmPlan,
    GepaPreflightError,
    StubGEPA,
    default_gepa_metric,
    gepa_budget_kwargs,
    invoke_gepa,
    model_entry_to_litellm,
    module_has_input_rewrite,
    preflight_compile_lms,
)
from zaumzeug.config.models import AgentModelsConfig, ModelEntryConfig
from zaumzeug.config.resolver import resolve_agent_compile
from zaumzeug.config.schemas import CompileConfig


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
    """AC-4 (E4-S02a): Missing registry ids or .env keys fail with actionable errors (no GEPA)."""
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


def test_e4_s02_ac3_metric_returns_textual_feedback() -> None:
    """AC-3: Custom metrics return textual feedback, not scalar-only."""
    import dspy

    example = dspy.Example(question="q", answer="expected").with_inputs("question")
    good = dspy.Prediction(answer="… expected …")
    bad = dspy.Prediction(answer="nope")

    good_out = default_gepa_metric(example, good)
    bad_out = default_gepa_metric(example, bad)

    assert isinstance(good_out, dspy.Prediction)
    assert isinstance(bad_out, dspy.Prediction)
    assert hasattr(good_out, "score") and hasattr(good_out, "feedback")
    assert hasattr(bad_out, "score") and hasattr(bad_out, "feedback")
    assert float(good_out.score) == 1.0
    assert str(good_out.feedback)
    assert float(bad_out.score) == 0.0
    assert "expected" in str(bad_out.feedback).lower() or "Include" in str(bad_out.feedback)


def test_e4_s02_ac5_task_and_reflection_lm_from_registry() -> None:
    """AC-5: Task and reflection LMs resolve to LiteLLM strings from the registry."""
    task = ModelEntryConfig(provider="openai", model="gpt-4o-mini")
    reflection = ModelEntryConfig(provider="anthropic", model="claude-sonnet-4-5")
    compatible = ModelEntryConfig(
        provider="openai_compatible",
        model="local-model",
        api_base_url="http://localhost:1234/v1",
    )

    assert model_entry_to_litellm(task) == "openai/gpt-4o-mini"
    assert model_entry_to_litellm(reflection) == "anthropic/claude-sonnet-4-5"
    assert model_entry_to_litellm(compatible) == "openai/local-model"

    plan = CompileLmPlan(
        task_model_id="task",
        reflection_model_id="reflect",
        task_entry=task,
        reflection_entry=reflection,
    )
    assert plan.task_litellm == "openai/gpt-4o-mini"
    assert plan.reflection_litellm == "anthropic/claude-sonnet-4-5"


def test_e4_s02_ac6_respects_gepa_budget(tmp_path: Path) -> None:
    """AC-6: GEPA budget from compile config (`auto` or `max_metric_calls`)."""
    auto_cfg = CompileConfig.model_validate(
        {"module": "modules.x:Y", "auto": "medium"}
    )
    calls_cfg = CompileConfig.model_validate(
        {"module": "modules.x:Y", "max_metric_calls": 42}
    )
    default_cfg = CompileConfig.model_validate({"module": "modules.x:Y"})

    assert gepa_budget_kwargs(auto_cfg) == {"auto": "medium"}
    assert gepa_budget_kwargs(calls_cfg) == {"max_metric_calls": 42}
    assert gepa_budget_kwargs(default_cfg) == {"auto": "light"}

    import dspy

    class Tiny(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.respond = dspy.Predict("question -> answer")

        def forward(self, question: str) -> dspy.Prediction:
            return dspy.Prediction(answer="harness")

    harness_dir, agent_dir = _layout(
        tmp_path,
        agent_yaml={
            "name": "researcher",
            "default_model_id": "mock",
            "compile": {
                "module": "modules.researcher:ResearchModule",
                "task_model_id": "mock",
                "reflection_model_id": "mock",
                "max_metric_calls": 7,
            },
        },
        models={
            "default_model_id": "mock",
            "models": {"mock": {"provider": "mock", "model": "harness-fixture"}},
        },
    )
    resolution = resolve_agent_compile(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
    )
    plan = CompileLmPlan(
        task_model_id="mock",
        reflection_model_id="mock",
        task_entry=ModelEntryConfig(provider="mock", model="harness-fixture"),
        reflection_entry=ModelEntryConfig(provider="mock", model="harness-fixture"),
    )

    captured: dict[str, object] = {}

    class CapturingGEPA(StubGEPA):
        def __init__(self, metric, **kwargs):  # noqa: ANN001
            captured.clear()
            captured.update(kwargs)
            super().__init__(metric, **kwargs)

    result = invoke_gepa(
        module=Tiny(),
        resolution=resolution,
        lm_plan=plan,
        agent_dir=agent_dir,
        gepa_cls=CapturingGEPA,
        stub=True,
        trainset=[
            dspy.Example(question="q", answer="harness").with_inputs("question"),
        ],
    )

    assert captured.get("max_metric_calls") == 7
    assert "auto" not in captured
    assert result.gepa_kwargs.get("max_metric_calls") == 7
    assert result.stubbed is True


def test_module_has_input_rewrite_detects_clarify_predictor() -> None:
    """Helper for AC-4: clarify/rewrite predictors are detected on the module."""
    import dspy

    class WithRewrite(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.input_rewrite = dspy.Predict("text -> rewritten")
            self.respond = dspy.Predict("question -> answer")

        def forward(self, question: str) -> dspy.Prediction:
            return self.respond(question=question)

    class Plain(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.respond = dspy.Predict("question -> answer")

        def forward(self, question: str) -> dspy.Prediction:
            return self.respond(question=question)

    assert module_has_input_rewrite(WithRewrite()) is True
    assert module_has_input_rewrite(Plain()) is False
