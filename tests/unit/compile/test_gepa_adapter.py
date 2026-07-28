# Story: E4-S04 / E4.4
"""E4-S04 — Haystack GEPA evaluator wrapper (Pattern B / optimize_anything)."""

from __future__ import annotations

from typing import Any

import pytest

from zaumzeug.compile.gepa_adapter import (
    GepaAdapterError,
    HaystackDataInst,
    HaystackGepaAdapter,
    infer_optimize_mode,
    is_optimize_anything_optimizer,
    optimize_haystack_artifact,
    resolve_optimize_mode,
    validate_mode_datasets,
)
from zaumzeug.config.schemas import CompileConfig


def _fake_agent_run(candidate: dict[str, str], example: HaystackDataInst) -> dict[str, Any]:
    """Simulate Haystack Agent.run — uses seed artifact text + expected keyword."""
    artifact = next(iter(candidate.values()), "")
    answer = str(example.get("answer") or example.get("expected") or "ok")
    # Include expected answer when the artifact mentions "helpful".
    text = f"{answer} via {artifact}" if "helpful" in artifact.lower() else f"miss: {artifact}"
    return {"messages": [{"role": "assistant", "content": text}], "output_text": text}


def test_e4_s04_ac1_optimize_anything_pattern() -> None:
    """AC-1: Evaluator wrapper supports the optimize_anything pattern."""
    assert is_optimize_anything_optimizer("optimize_anything")
    assert is_optimize_anything_optimizer("gepa.optimize_anything")
    assert not is_optimize_anything_optimizer("dspy.GEPA")

    seed = {"system_prompt": "Be helpful and concise."}
    dataset = [
        HaystackDataInst(input="What is ZaumZeug?", answer="harness"),
    ]

    captured: dict[str, Any] = {}

    def fake_optimize(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return type("R", (), {"best_candidate": {"system_prompt": "Be helpful."}})()

    result = optimize_haystack_artifact(
        seed_candidate=seed,
        run_agent=_fake_agent_run,
        mode="multi-task",
        dataset=dataset,
        optimize_fn=fake_optimize,
    )

    assert result.mode == "multi-task"
    assert result.stubbed is False
    assert "helpful" in result.best_candidate["system_prompt"]
    assert captured["adapter"] is not None
    assert captured["trainset"] == dataset
    assert captured["seed_candidate"] == seed


def test_e4_s04_ac1_stub_path_exercises_evaluator() -> None:
    """AC-1 (CI): stub optimize path still runs Haystack evaluator + returns seed."""
    result = optimize_haystack_artifact(
        seed_candidate="Be helpful.",
        run_agent=_fake_agent_run,
        mode="single-task",
        stub=True,
    )
    assert result.stubbed is True
    assert result.best_candidate == {"artifact": "Be helpful."}
    assert result.extras["trace_count"] == 1
    assert result.extras["scores"]


def test_e4_s04_ac2_modes_single_multi_generalization() -> None:
    """AC-2: Modes single-task, multi-task, and generalization are enforced."""
    assert infer_optimize_mode(dataset=None, valset=None) == "single-task"
    assert infer_optimize_mode(dataset=[{"input": "a"}], valset=None) == "multi-task"
    assert (
        infer_optimize_mode(dataset=[{"input": "a"}], valset=[{"input": "b"}])
        == "generalization"
    )
    assert resolve_optimize_mode("single_task") == "single-task"

    train = [HaystackDataInst(input="t", answer="a")]
    val = [HaystackDataInst(input="v", answer="a")]

    validate_mode_datasets("single-task", dataset=None, valset=None)
    validate_mode_datasets("multi-task", dataset=train, valset=None)
    validate_mode_datasets("generalization", dataset=train, valset=val)

    with pytest.raises(GepaAdapterError, match="validation set"):
        validate_mode_datasets("single-task", dataset=None, valset=val)
    with pytest.raises(GepaAdapterError, match="requires a dataset"):
        validate_mode_datasets("multi-task", dataset=None, valset=None)
    with pytest.raises(GepaAdapterError, match="validation set"):
        validate_mode_datasets("generalization", dataset=train, valset=None)

    r_single = optimize_haystack_artifact(
        seed_candidate="seed",
        run_agent=_fake_agent_run,
        mode="single-task",
        stub=True,
    )
    r_multi = optimize_haystack_artifact(
        seed_candidate="seed",
        run_agent=_fake_agent_run,
        mode="multi-task",
        dataset=train,
        stub=True,
    )
    r_gen = optimize_haystack_artifact(
        seed_candidate="seed",
        run_agent=_fake_agent_run,
        mode="generalization",
        dataset=train,
        valset=val,
        stub=True,
    )
    assert r_single.mode == "single-task"
    assert r_multi.mode == "multi-task"
    assert r_gen.mode == "generalization"


def test_e4_s04_ac2_compile_schema_mode_selection() -> None:
    """AC-2 / schema: mode selection documented and validated on CompileConfig."""
    pattern_b = CompileConfig.model_validate(
        {
            "optimizer": "optimize_anything",
            "mode": "generalization",
            "seed_artifact": "prompts/system.md",
            "trainset": "data/train.jsonl",
            "valset": "data/val.jsonl",
            "auto": "light",
        }
    )
    assert pattern_b.module is None
    assert pattern_b.mode == "generalization"
    assert pattern_b.seed_artifact == "prompts/system.md"

    with pytest.raises(Exception, match="mode"):
        CompileConfig.model_validate(
            {
                "optimizer": "optimize_anything",
                "seed_artifact": "prompts/system.md",
            }
        )

    with pytest.raises(Exception, match="seed_artifact"):
        CompileConfig.model_validate(
            {
                "optimizer": "optimize_anything",
                "mode": "single-task",
            }
        )

    with pytest.raises(Exception, match="only valid with optimizer"):
        CompileConfig.model_validate(
            {
                "module": "modules.x:Y",
                "mode": "single-task",
            }
        )

    # Pattern A still requires module.
    pattern_a = CompileConfig.model_validate({"module": "modules.x:Y"})
    assert pattern_a.optimizer == "dspy.GEPA"
    assert pattern_a.mode is None


def test_e4_s04_ac3_haystack_agent_trace_collection() -> None:
    """AC-3: Integrates with Haystack agent execution for trace collection."""
    calls: list[tuple[dict[str, str], HaystackDataInst]] = []

    def run_agent(candidate: dict[str, str], example: HaystackDataInst) -> dict[str, Any]:
        calls.append((candidate, example))
        return _fake_agent_run(candidate, example)

    adapter = HaystackGepaAdapter(run_agent=run_agent, component_key="system_prompt")
    batch = [
        HaystackDataInst(input="What is ZaumZeug?", answer="harness"),
        HaystackDataInst(input="Runtime?", answer="Haystack"),
    ]
    candidate = {"system_prompt": "Be helpful."}

    eval_batch = adapter.evaluate(batch, candidate, capture_traces=True)

    assert len(calls) == 2
    assert len(eval_batch.scores) == 2
    assert eval_batch.trajectories is not None
    assert len(eval_batch.trajectories) == 2
    assert eval_batch.trajectories[0]["data"]["input"] == "What is ZaumZeug?"
    assert eval_batch.trajectories[0]["candidate"] == candidate
    assert "harness" in eval_batch.trajectories[0]["output_text"]
    assert eval_batch.trajectories[0]["feedback"]

    reflective = adapter.make_reflective_dataset(
        candidate,
        eval_batch,
        components_to_update=["system_prompt"],
    )
    assert "system_prompt" in reflective
    assert reflective["system_prompt"][0]["Inputs"] == "What is ZaumZeug?"
    assert reflective["system_prompt"][0]["Feedback"]
