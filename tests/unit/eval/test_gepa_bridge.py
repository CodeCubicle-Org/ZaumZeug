# Story: E6-S07 / E6.7
"""E6-S07 — GEPA ↔ DeepEval bridge (failed eval → train, shared val, metric)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import dspy
import pytest


from zaumzeug.compile.gepa_runner import _read_jsonl_examples, default_gepa_metric
from zaumzeug.eval.gepa_bridge import (
    COMPILE_TRAIN_SCHEMA,
    SHARED_VAL_SCHEMA,
    append_failed_eval_to_train,
    deepeval_gepa_metric,
    eval_case_to_train_row,
    load_modules_gepa_metric,
    normalize_val_row_for_compile,
    normalize_val_row_for_eval,
)
from zaumzeug.eval.runner import EvalCaseResult, EvalResult, load_valset_jsonl


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_e6_s07_ac1_failed_rows_append_train_jsonl(tmp_path: Path) -> None:
    """AC-1: Failed eval rows can append to data/train.jsonl."""
    train = tmp_path / "data" / "train.jsonl"
    _write_jsonl(
        train,
        [{"question": "seed", "answer": "ok"}],
    )
    result = EvalResult(
        harness_name="example",
        harness_dir=tmp_path,
        framework="builtin",
        agent_name="researcher",
        cases=[
            EvalCaseResult(
                index=0,
                input="What optimizes prompts?",
                expected_output="GEPA",
                actual_output="something else",
                passed=False,
                detail="mismatch",
            ),
            EvalCaseResult(
                index=1,
                input="passed case",
                expected_output="yes",
                actual_output="yes",
                passed=True,
            ),
            EvalCaseResult(
                index=2,
                input="no gold",
                expected_output=None,
                actual_output="x",
                passed=False,
            ),
        ],
        passed=1,
        failed=2,
    )

    appended = append_failed_eval_to_train(result, train)
    assert appended == 1

    lines = [
        json.loads(line)
        for line in train.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines[0] == {"question": "seed", "answer": "ok"}
    assert lines[1] == {
        "question": "What optimizes prompts?",
        "answer": "GEPA",
    }
    assert COMPILE_TRAIN_SCHEMA["required"] == ("question", "answer")
    assert eval_case_to_train_row(result.cases[0]) == lines[1]


def test_e6_s07_ac2_shared_val_jsonl(tmp_path: Path) -> None:
    """AC-2: Shared data/val.jsonl for compile and eval (aliases both ways)."""
    assert "input" in SHARED_VAL_SCHEMA["aliases"]

    # Eval-native rows are readable by compile.
    eval_native = tmp_path / "val_eval.jsonl"
    _write_jsonl(
        eval_native,
        [
            {
                "input": "What does zaumzeug compile run?",
                "expected_output": "GEPA",
            }
        ],
    )
    eval_rows = load_valset_jsonl(eval_native)
    assert eval_rows[0]["input"] == "What does zaumzeug compile run?"
    assert eval_rows[0]["expected_output"] == "GEPA"

    compile_examples = _read_jsonl_examples(eval_native)
    assert len(compile_examples) == 1
    assert compile_examples[0].question == "What does zaumzeug compile run?"
    assert compile_examples[0].answer == "GEPA"

    # GEPA-native rows are readable by eval.
    gepa_native = tmp_path / "val_gepa.jsonl"
    _write_jsonl(
        gepa_native,
        [{"question": "Where do artifacts land?", "answer": "artifacts"}],
    )
    eval_from_gepa = load_valset_jsonl(gepa_native)
    assert eval_from_gepa[0]["input"] == "Where do artifacts land?"
    assert eval_from_gepa[0]["expected_output"] == "artifacts"

    normalized_eval = normalize_val_row_for_eval(
        {"question": "q", "answer": "a"}
    )
    assert normalized_eval == {"input": "q", "expected_output": "a"}
    normalized_compile = normalize_val_row_for_compile(
        {"input": "q", "expected_output": "a"}
    )
    assert normalized_compile == {"question": "q", "answer": "a"}


def test_e6_s07_ac3_gepa_metric_delegates_deepeval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: GEPA custom metric may delegate to DeepEval .measure()."""

    class _FakeTestCase:
        def __init__(self, **kwargs: Any) -> None:
            self.input = kwargs.get("input")
            self.actual_output = kwargs.get("actual_output")
            self.expected_output = kwargs.get("expected_output")

    class _FakeMetric:
        threshold = 1.0

        def __init__(self) -> None:
            self.score: float | None = None
            self.reason: str | None = None
            self.measure_calls = 0

        def measure(self, test_case: Any) -> float:
            self.measure_calls += 1
            expected = test_case.expected_output or ""
            actual = test_case.actual_output or ""
            self.score = 1.0 if expected and expected in actual else 0.0
            self.reason = "Good." if self.score >= 1.0 else f"missing {expected!r}"
            return self.score

    fake_deepeval_tc = SimpleNamespace(LLMTestCase=_FakeTestCase)
    monkeypatch.setitem(sys.modules, "deepeval", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "deepeval.test_case", fake_deepeval_tc)

    fake = _FakeMetric()
    metric = deepeval_gepa_metric(fake, enabled=True)

    example = dspy.Example(question="q", answer="GEPA").with_inputs("question")
    good = dspy.Prediction(answer="… GEPA …")
    bad = dspy.Prediction(answer="nope")

    good_out = metric(example, good)
    bad_out = metric(example, bad)

    assert fake.measure_calls == 2
    assert isinstance(good_out, dspy.Prediction)
    assert float(good_out.score) == 1.0
    assert str(good_out.feedback)
    assert float(bad_out.score) == 0.0
    assert "GEPA" in str(bad_out.feedback) or "missing" in str(bad_out.feedback).lower()


def test_e6_s07_ac4_optional_deepeval_measure() -> None:
    """AC-4: DeepEval delegation is optional — disabled / missing falls back."""
    example = dspy.Example(question="q", answer="expected").with_inputs("question")
    good = dspy.Prediction(answer="… expected …")
    bad = dspy.Prediction(answer="nope")

    # Disabled: never calls DeepEval; matches default_gepa_metric.
    disabled = deepeval_gepa_metric(object(), enabled=False)
    assert float(disabled(example, good).score) == float(
        default_gepa_metric(example, good).score
    )
    assert float(disabled(example, bad).score) == float(
        default_gepa_metric(example, bad).score
    )

    # No metric instance: same fallback.
    none_metric = deepeval_gepa_metric(None, enabled=True)
    assert float(none_metric(example, good).score) == 1.0
    assert float(none_metric(example, bad).score) == 0.0

    # Template modules/metrics.py loads and stays optional.
    repo = Path(__file__).resolve().parents[3]
    agent_dir = repo / "usr-harnesses" / "example" / "agents" / "researcher"
    loaded = load_modules_gepa_metric(agent_dir)
    assert loaded is not None
    out = loaded(example, good)
    assert hasattr(out, "score") and hasattr(out, "feedback")
