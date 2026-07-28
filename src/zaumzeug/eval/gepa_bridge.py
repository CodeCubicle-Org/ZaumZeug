"""GEPA ↔ DeepEval bridge (E6-S07 / E6.7).

Closed loop: ``zaumzeug compile`` → ``zaumzeug eval`` → append failures to
train → ``zaumzeug compile`` again. DeepEval is optional — GEPA metrics may
delegate to ``.measure()`` when the ``[eval]`` extra is installed.

JSONL schemas
-------------

**Compile train** (``agents/<agent>/data/train.jsonl``)::

    {"question": "<user turn>", "answer": "<expected keyword or gold>"}

**Shared val** (``compile.valset`` and/or ``eval.valset`` — same file OK)::

    # Eval-native (``zaumzeug eval``)
    {"input": "...", "expected_output": "...", "retrieval_context": ["..."]}

    # GEPA-native (``zaumzeug compile``)
    {"question": "...", "answer": "..."}

Field aliases (normalized by bridge helpers and loaders):

| Eval field         | Compile / GEPA field |
|--------------------|----------------------|
| ``input``          | ``question``         |
| ``expected_output``| ``answer``           |

Failed eval rows append to train as ``{question, answer}`` using ``input`` and
``expected_output`` (rows without ``expected_output`` are skipped).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from zaumzeug.eval.runner import EvalCaseResult, EvalResult

__all__ = [
    "COMPILE_TRAIN_SCHEMA",
    "SHARED_VAL_SCHEMA",
    "GepaBridgeError",
    "append_failed_eval_to_train",
    "deepeval_gepa_metric",
    "eval_case_to_train_row",
    "eval_row_to_train_row",
    "load_modules_gepa_metric",
    "normalize_val_row_for_compile",
    "normalize_val_row_for_eval",
]

# Documented schemas (AC docs / Journey C).
COMPILE_TRAIN_SCHEMA = {
    "required": ("question", "answer"),
    "description": "One GEPA training example per JSONL line.",
}

SHARED_VAL_SCHEMA = {
    "aliases": {
        "input": "question",
        "expected_output": "answer",
    },
    "optional": ("retrieval_context",),
    "description": (
        "Shared valset for compile and eval — either naming convention, "
        "or both fields present."
    ),
}


class GepaBridgeError(RuntimeError):
    """GEPA ↔ DeepEval bridge failed with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.suggestion = suggestion
        super().__init__(message)


def normalize_val_row_for_eval(row: Mapping[str, Any]) -> dict[str, Any]:
    """Map a shared val row to eval fields (``input``, ``expected_output``)."""
    if "input" in row:
        user_input = row["input"]
    elif "question" in row:
        user_input = row["question"]
    else:
        raise GepaBridgeError(
            "Valset row missing `input` / `question`",
            suggestion="Add input (eval) or question (compile) to each JSONL row",
        )
    out: dict[str, Any] = {"input": str(user_input)}
    if "expected_output" in row and row["expected_output"] is not None:
        out["expected_output"] = str(row["expected_output"])
    elif "answer" in row and row["answer"] is not None:
        out["expected_output"] = str(row["answer"])
    retrieval = row.get("retrieval_context")
    if retrieval is not None:
        out["retrieval_context"] = retrieval
    return out


def normalize_val_row_for_compile(row: Mapping[str, Any]) -> dict[str, Any]:
    """Map a shared val row to GEPA fields (``question``, ``answer``)."""
    if "question" in row:
        question = row["question"]
    elif "input" in row:
        question = row["input"]
    else:
        raise GepaBridgeError(
            "Valset row missing `question` / `input`",
            suggestion="Add question (compile) or input (eval) to each JSONL row",
        )
    out: dict[str, Any] = {"question": str(question)}
    if "answer" in row and row["answer"] is not None:
        out["answer"] = str(row["answer"])
    elif "expected_output" in row and row["expected_output"] is not None:
        out["answer"] = str(row["expected_output"])
    return out


def eval_row_to_train_row(row: Mapping[str, Any]) -> dict[str, str] | None:
    """Convert an eval/valset-shaped row to a compile train row.

    Returns ``None`` when there is no expected answer to train on.
    """
    normalized = normalize_val_row_for_eval(row)
    expected = normalized.get("expected_output")
    if expected is None:
        return None
    return {
        "question": str(normalized["input"]),
        "answer": str(expected),
    }


def eval_case_to_train_row(case: EvalCaseResult) -> dict[str, str] | None:
    """Convert one :class:`EvalCaseResult` to a compile train row."""
    if case.expected_output is None:
        return None
    return {
        "question": str(case.input),
        "answer": str(case.expected_output),
    }


def _failed_cases(
    source: EvalResult | Sequence[EvalCaseResult],
) -> list[EvalCaseResult]:
    if isinstance(source, EvalResult):
        return [case for case in source.cases if not case.passed]
    return [case for case in source if not case.passed]


def append_failed_eval_to_train(
    source: EvalResult | Sequence[EvalCaseResult],
    train_path: Path | str,
    *,
    skip_without_expected: bool = True,
) -> int:
    """Append failed eval cases to ``data/train.jsonl`` (AC-1).

    Each appended line is ``{"question": ..., "answer": ...}``. Cases without
    ``expected_output`` are skipped when *skip_without_expected* is true
    (default); otherwise a :class:`GepaBridgeError` is raised.

    Returns the number of rows appended.
    """
    path = Path(train_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for case in _failed_cases(source):
        row = eval_case_to_train_row(case)
        if row is None:
            if skip_without_expected:
                continue
            raise GepaBridgeError(
                f"Failed eval case {case.index} has no expected_output; "
                "cannot append to train.jsonl",
                path=path,
                suggestion=(
                    "Set expected_output on the valset row, or call with "
                    "skip_without_expected=True"
                ),
            )
        lines.append(json.dumps(row, ensure_ascii=False))

    if not lines:
        return 0

    prefix = ""
    if path.is_file() and path.stat().st_size > 0:
        existing = path.read_text(encoding="utf-8")
        if not existing.endswith("\n"):
            prefix = "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + "\n".join(lines) + "\n")
    return len(lines)


def deepeval_gepa_metric(
    deepeval_metric: Any | None = None,
    *,
    enabled: bool = True,
    fallback: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Build a GEPA metric that optionally delegates to DeepEval ``.measure()``.

    When *enabled* is false, or ``deepeval`` / *deepeval_metric* is unavailable,
    falls back to :func:`zaumzeug.compile.gepa_runner.default_gepa_metric`
    (or *fallback* when provided). DeepEval is never imported unless *enabled*
    and a metric instance (or factory) is supplied (AC-3, AC-4).
    """

    def _metric(
        example: Any,
        pred: Any,
        trace: Any = None,
        pred_name: str | None = None,
        pred_trace: Any = None,
    ) -> Any:
        from zaumzeug.compile.gepa_runner import default_gepa_metric

        fallback_fn = fallback or default_gepa_metric

        if not enabled or deepeval_metric is None:
            return fallback_fn(
                example, pred, trace, pred_name=pred_name, pred_trace=pred_trace
            )

        try:
            from deepeval.test_case import LLMTestCase
        except ImportError:
            return fallback_fn(
                example, pred, trace, pred_name=pred_name, pred_trace=pred_trace
            )

        import dspy

        question = _field(example, "question") or _field(example, "input") or ""
        expected = (
            _field(example, "answer")
            or _field(example, "expected")
            or _field(example, "expected_output")
            or ""
        )
        answer = getattr(pred, "answer", None)
        if answer is None and isinstance(pred, dict):
            answer = pred.get("answer", "")
        actual = "" if answer is None else str(answer)

        kwargs: dict[str, Any] = {
            "input": str(question),
            "actual_output": actual,
        }
        if expected:
            kwargs["expected_output"] = str(expected)

        # Factories vs instances: prefer objects that already expose measure.
        if hasattr(deepeval_metric, "measure"):
            metric_obj = deepeval_metric
        elif callable(deepeval_metric):
            metric_obj = deepeval_metric()
        else:
            return fallback_fn(
                example, pred, trace, pred_name=pred_name, pred_trace=pred_trace
            )

        try:
            test_case = LLMTestCase(**kwargs)
            metric_obj.measure(test_case)
            score = getattr(metric_obj, "score", None)
            if score is None:
                score = 0.0
            score_f = float(score)
            reason = getattr(metric_obj, "reason", None)
            if reason:
                feedback = str(reason)
            elif score_f >= float(getattr(metric_obj, "threshold", 0.5)):
                feedback = "Good."
            else:
                feedback = (
                    f"DeepEval {type(metric_obj).__name__} scored {score_f}; "
                    f"expected keyword {expected!r}."
                    if expected
                    else f"DeepEval {type(metric_obj).__name__} scored {score_f}."
                )
            return dspy.Prediction(score=score_f, feedback=feedback)
        except Exception as exc:  # noqa: BLE001 — fall back on metric failures
            fallback_out = fallback_fn(
                example, pred, trace, pred_name=pred_name, pred_trace=pred_trace
            )
            # Prefer DeepEval error context when fallback also scores low.
            fb_score = float(getattr(fallback_out, "score", 0.0) or 0.0)
            if fb_score < 1.0:
                return dspy.Prediction(
                    score=fb_score,
                    feedback=f"DeepEval measure failed ({exc}); {getattr(fallback_out, 'feedback', '')}",
                )
            return fallback_out

    return _metric


def load_modules_gepa_metric(agent_dir: Path | str) -> Callable[..., Any] | None:
    """Load ``metric`` / ``gepa_metric`` from ``agents/<agent>/modules/metrics.py``.

    Returns ``None`` when the file or attribute is absent (compile keeps the
    default GEPA metric).
    """
    agent_path = Path(agent_dir).resolve()
    metrics_file = agent_path / "modules" / "metrics.py"
    if not metrics_file.is_file():
        return None

    modules_dir = str(agent_path)
    inserted = False
    if modules_dir not in sys.path:
        sys.path.insert(0, modules_dir)
        inserted = True
    try:
        spec = importlib.util.spec_from_file_location(
            f"zaumzeug_agent_metrics_{agent_path.name}",
            metrics_file,
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        candidate = getattr(module, "metric", None) or getattr(
            module, "gepa_metric", None
        )
        if candidate is None or not callable(candidate):
            return None
        return candidate
    except Exception as exc:  # noqa: BLE001
        raise GepaBridgeError(
            f"Failed to load modules/metrics.py from {metrics_file}: {exc}",
            path=metrics_file,
            suggestion=(
                "Fix agents/<agent>/modules/metrics.py or remove it to use "
                "the default GEPA metric"
            ),
        ) from exc
    finally:
        if inserted:
            try:
                sys.path.remove(modules_dir)
            except ValueError:
                pass


def _field(obj: Any, name: str) -> Any:
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, Mapping):
        return obj.get(name)
    get = getattr(obj, "get", None)
    if callable(get):
        return get(name)
    return None
