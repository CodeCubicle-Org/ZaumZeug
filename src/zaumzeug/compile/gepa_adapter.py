"""Haystack GEPA evaluator wrapper — Pattern B ``optimize_anything`` (E4-S04 / E4.4).

Optimizes Haystack-native text artifacts (system prompts, pipeline YAML, tool
descriptions) without a DSPy module path. The adapter runs ``Agent.run`` /
``Pipeline.run`` (via an injectable runner), captures traces, and returns
score + Actionable Side Information for GEPA reflection.

When ``gepa.optimize_anything`` is available it is preferred; otherwise the
wrapper maps modes onto ``gepa.optimize`` + :class:`HaystackGepaAdapter`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict, cast

__all__ = [
    "OPTIMIZE_ANYTHING_OPTIMIZERS",
    "DEFAULT_COMPONENT_KEY",
    "GepaAdapterError",
    "HaystackDataInst",
    "HaystackGepaAdapter",
    "HaystackRolloutOutput",
    "HaystackTrace",
    "OptimizeAnythingResult",
    "OptimizeMode",
    "default_haystack_score",
    "infer_optimize_mode",
    "is_optimize_anything_optimizer",
    "optimize_haystack_artifact",
    "resolve_optimize_mode",
    "validate_mode_datasets",
]

OptimizeMode = Literal["single-task", "multi-task", "generalization"]

OPTIMIZE_ANYTHING_OPTIMIZERS = frozenset(
    {
        "optimize_anything",
        "gepa.optimize_anything",
    }
)

DEFAULT_COMPONENT_KEY = "artifact"
_VALID_MODES: frozenset[str] = frozenset(
    {"single-task", "multi-task", "generalization"}
)


class GepaAdapterError(ValueError):
    """Invalid Pattern B config or optimize_anything invocation."""

    def __init__(self, message: str, *, suggestion: str | None = None) -> None:
        self.suggestion = suggestion
        super().__init__(message)


class HaystackDataInst(TypedDict, total=False):
    """One eval example for the Haystack GEPA adapter."""

    input: str
    question: str
    answer: str
    expected: str
    additional_context: dict[str, str]


class HaystackTrace(TypedDict):
    """Per-example execution trace captured for reflective feedback (AC-3)."""

    data: HaystackDataInst
    output_text: str
    feedback: str
    candidate: dict[str, str]
    raw_result: Any
    error: str | None


class HaystackRolloutOutput(TypedDict):
    """Opaque rollout payload returned to GEPA."""

    output_text: str


HaystackRunner = Callable[[dict[str, str], HaystackDataInst], Any]
HaystackScoreFn = Callable[
    [dict[str, str], HaystackDataInst, str, HaystackTrace | None],
    tuple[float, str],
]


@dataclass(slots=True)
class OptimizeAnythingResult:
    """Normalized outcome of a Pattern B optimize run."""

    best_candidate: dict[str, str]
    mode: OptimizeMode
    stubbed: bool = False
    raw: Any = None
    extras: dict[str, Any] = field(default_factory=dict)


def is_optimize_anything_optimizer(optimizer: str | None) -> bool:
    """True when ``compile.optimizer`` selects Pattern B."""
    if not optimizer:
        return False
    return optimizer.strip() in OPTIMIZE_ANYTHING_OPTIMIZERS


def infer_optimize_mode(
    *,
    dataset: Sequence[Any] | None,
    valset: Sequence[Any] | None,
) -> OptimizeMode:
    """Infer mode from dataset/valset presence (GEPA optimize_anything convention)."""
    has_data = bool(dataset)
    has_val = valset is not None and len(valset) > 0
    if has_data and has_val:
        return "generalization"
    if has_data:
        return "multi-task"
    return "single-task"


def resolve_optimize_mode(
    mode: OptimizeMode | str | None = None,
    *,
    dataset: Sequence[Any] | None = None,
    valset: Sequence[Any] | None = None,
) -> OptimizeMode:
    """Return an explicit mode, or infer from datasets when *mode* is omitted."""
    if mode is None:
        return infer_optimize_mode(dataset=dataset, valset=valset)
    normalized = str(mode).strip().lower().replace("_", "-")
    if normalized not in _VALID_MODES:
        raise GepaAdapterError(
            f"Unknown optimize mode {mode!r}; expected one of "
            f"{', '.join(sorted(_VALID_MODES))}",
            suggestion="Set compile.mode to single-task, multi-task, or generalization",
        )
    return cast(OptimizeMode, normalized)


def validate_mode_datasets(
    mode: OptimizeMode,
    *,
    dataset: Sequence[Any] | None,
    valset: Sequence[Any] | None,
) -> None:
    """Enforce dataset/valset requirements for each Pattern B mode (AC-2)."""
    has_data = bool(dataset)
    has_val = valset is not None and len(valset) > 0

    if mode == "single-task":
        if has_val:
            raise GepaAdapterError(
                "single-task mode must not set a validation set",
                suggestion="Omit valset/compile.valset for single-task, or use generalization",
            )
        return

    if mode == "multi-task":
        if not has_data:
            raise GepaAdapterError(
                "multi-task mode requires a dataset (compile.trainset)",
                suggestion="Provide train examples under compile.trainset",
            )
        if has_val:
            raise GepaAdapterError(
                "multi-task mode must not set a separate validation set",
                suggestion="Omit valset, or switch compile.mode to generalization",
            )
        return

    # generalization
    if not has_data:
        raise GepaAdapterError(
            "generalization mode requires a training dataset (compile.trainset)",
            suggestion="Provide train examples and a held-out compile.valset",
        )
    if not has_val:
        raise GepaAdapterError(
            "generalization mode requires a validation set (compile.valset)",
            suggestion="Add compile.valset for train/val generalization search",
        )


def default_haystack_score(
    candidate: dict[str, str],
    example: HaystackDataInst,
    output_text: str,
    trace: HaystackTrace | None = None,
) -> tuple[float, str]:
    """Default metric: expected keyword containment + textual feedback (ASI)."""
    del candidate, trace  # unused — signature matches HaystackScoreFn
    expected = str(example.get("answer") or example.get("expected") or "")
    text = output_text or ""
    if expected and expected in text:
        return 1.0, "Good."
    if expected:
        return 0.0, f"Include expected keyword in output: {expected!r}."
    if text.strip():
        return 1.0, "Good."
    return 0.0, "Provide a non-empty agent/pipeline output."


class HaystackGepaAdapter:
    """``GEPAAdapter`` that evaluates candidates via Haystack Agent/Pipeline runs.

    *run_agent* receives the candidate component map and one example, and should
    call ``Agent.run`` / ``Pipeline.run`` (or a test double). Traces are collected
    when ``capture_traces=True`` for reflective mutation (AC-3).
    """

    def __init__(
        self,
        *,
        run_agent: HaystackRunner,
        score_fn: HaystackScoreFn | None = None,
        component_key: str = DEFAULT_COMPONENT_KEY,
        extract_output: Callable[[Any], str] | None = None,
    ) -> None:
        if not component_key.strip():
            raise GepaAdapterError("`component_key` must be a non-empty candidate name")
        self.run_agent = run_agent
        self.score_fn = score_fn or default_haystack_score
        self.component_key = component_key.strip()
        self.extract_output = extract_output or extract_haystack_output_text

    def evaluate(
        self,
        batch: list[HaystackDataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> Any:
        """Run Haystack execution per example; optionally capture traces (AC-1/AC-3)."""
        from gepa.core.adapter import EvaluationBatch

        outputs: list[HaystackRolloutOutput] = []
        scores: list[float] = []
        trajectories: list[HaystackTrace] | None = [] if capture_traces else None

        for example in batch:
            output_text = ""
            raw_result: Any = None
            error: str | None = None
            try:
                raw_result = self.run_agent(candidate, example)
                output_text = self.extract_output(raw_result)
            except Exception as exc:  # noqa: BLE001 — per-example failures → score 0
                error = f"{type(exc).__name__}: {exc}"
                output_text = ""

            trace: HaystackTrace | None = None
            if capture_traces:
                # Placeholder feedback filled after scoring.
                trace = HaystackTrace(
                    data=example,
                    output_text=output_text,
                    feedback="",
                    candidate=dict(candidate),
                    raw_result=raw_result,
                    error=error,
                )

            score, feedback = self.score_fn(candidate, example, output_text, trace)
            if error and score >= 1.0:
                score = 0.0
                feedback = f"Haystack execution failed: {error}"
            elif error:
                feedback = f"{feedback} (execution error: {error})"

            if trace is not None and trajectories is not None:
                trace["feedback"] = feedback
                trajectories.append(trace)

            outputs.append(HaystackRolloutOutput(output_text=output_text))
            scores.append(float(score))

        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
        )

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: Any,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build reflective records from captured Haystack traces."""
        del candidate  # component texts already in trajectories
        trajectories = eval_batch.trajectories or []
        records: list[Mapping[str, Any]] = []
        for traj in trajectories:
            example = traj.get("data") or {}
            user_input = example_user_text(example)
            record = {
                "Inputs": user_input,
                "Generated Outputs": traj.get("output_text") or "",
                "Feedback": traj.get("feedback") or "",
            }
            if traj.get("error"):
                record["Error"] = traj["error"]
            records.append(record)

        result: dict[str, Sequence[Mapping[str, Any]]] = {}
        for name in components_to_update:
            result[name] = list(records)
        return result


def example_user_text(example: Mapping[str, Any]) -> str:
    """Best-effort user/input field from a train/val example."""
    for key in ("input", "question", "query", "user_input"):
        value = example.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def extract_haystack_output_text(result: Any) -> str:
    """Extract assistant text from a Haystack ``Agent.run`` / ``Pipeline.run`` result."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, Mapping):
        for key in ("output_text", "answer", "result", "text"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value
        messages = result.get("messages")
        if isinstance(messages, Sequence) and messages:
            last = messages[-1]
            text = _message_text(last)
            if text:
                return text
        last_message = result.get("last_message")
        text = _message_text(last_message)
        if text:
            return text
    text = _message_text(result)
    if text:
        return text
    return str(result)


def _message_text(message: Any) -> str:
    if message is None:
        return ""
    if isinstance(message, str):
        return message
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(message, Mapping):
        for key in ("text", "content"):
            value = message.get(key)
            if isinstance(value, str):
                return value
    return ""


def _normalize_seed(seed_candidate: str | dict[str, str], component_key: str) -> dict[str, str]:
    if isinstance(seed_candidate, dict):
        if not seed_candidate:
            raise GepaAdapterError(
                "seed_candidate dict must include at least one text component",
                suggestion=f"Pass {{{component_key!r}: '<seed text>'}} or a string seed",
            )
        return {str(k): str(v) for k, v in seed_candidate.items()}
    return {component_key: str(seed_candidate)}


def _single_task_dataset(
    dataset: Sequence[HaystackDataInst] | None,
) -> list[HaystackDataInst]:
    if dataset:
        return [dict(dataset[0])]  # type: ignore[arg-type]
    return [HaystackDataInst(input="optimize this artifact", answer="")]


def optimize_haystack_artifact(
    *,
    seed_candidate: str | dict[str, str],
    run_agent: HaystackRunner,
    mode: OptimizeMode | str | None = None,
    dataset: Sequence[HaystackDataInst] | None = None,
    valset: Sequence[HaystackDataInst] | None = None,
    score_fn: HaystackScoreFn | None = None,
    component_key: str = DEFAULT_COMPONENT_KEY,
    reflection_lm: Any | None = None,
    max_metric_calls: int | None = None,
    stub: bool = False,
    optimize_fn: Callable[..., Any] | None = None,
    adapter: HaystackGepaAdapter | None = None,
    objective: str | None = None,
    background: str | None = None,
    **optimize_kwargs: Any,
) -> OptimizeAnythingResult:
    """Run Pattern B optimization (``optimize_anything`` semantics) — AC-1.

    Modes (AC-2):

    - ``single-task`` — improve one artifact on one problem (no valset)
    - ``multi-task`` — trainset only; cross-task search
    - ``generalization`` — train/val split (preferred for production)
    """
    resolved_mode = resolve_optimize_mode(mode, dataset=dataset, valset=valset)
    validate_mode_datasets(resolved_mode, dataset=dataset, valset=valset)
    seed = _normalize_seed(seed_candidate, component_key)
    gepa_adapter = adapter or HaystackGepaAdapter(
        run_agent=run_agent,
        score_fn=score_fn,
        component_key=next(iter(seed)) if len(seed) == 1 else component_key,
    )

    if resolved_mode == "single-task":
        trainset = _single_task_dataset(list(dataset) if dataset else None)
        resolved_valset: list[HaystackDataInst] | None = None
    elif resolved_mode == "multi-task":
        trainset = [dict(row) for row in dataset or []]  # type: ignore[misc]
        resolved_valset = None
    else:
        trainset = [dict(row) for row in dataset or []]  # type: ignore[misc]
        resolved_valset = [dict(row) for row in valset or []]  # type: ignore[misc]

    if stub:
        # Offline / CI: exercise evaluator + traces without live GEPA.
        batch = trainset[:1] or _single_task_dataset(None)
        eval_batch = gepa_adapter.evaluate(batch, seed, capture_traces=True)
        _ = gepa_adapter.make_reflective_dataset(
            seed,
            eval_batch,
            components_to_update=list(seed.keys()),
        )
        return OptimizeAnythingResult(
            best_candidate=dict(seed),
            mode=resolved_mode,
            stubbed=True,
            extras={
                "scores": list(eval_batch.scores),
                "trace_count": len(eval_batch.trajectories or []),
                "objective": objective,
                "background": background,
            },
        )

    raw = _invoke_optimize_anything(
        seed_candidate=seed,
        adapter=gepa_adapter,
        trainset=trainset,
        valset=resolved_valset,
        reflection_lm=reflection_lm,
        max_metric_calls=max_metric_calls,
        optimize_fn=optimize_fn,
        objective=objective,
        background=background,
        **optimize_kwargs,
    )
    best = _best_candidate_from_result(raw, fallback=seed)
    return OptimizeAnythingResult(
        best_candidate=best,
        mode=resolved_mode,
        stubbed=False,
        raw=raw,
    )


def _invoke_optimize_anything(
    *,
    seed_candidate: dict[str, str],
    adapter: HaystackGepaAdapter,
    trainset: list[HaystackDataInst],
    valset: list[HaystackDataInst] | None,
    reflection_lm: Any | None,
    max_metric_calls: int | None,
    optimize_fn: Callable[..., Any] | None,
    objective: str | None,
    background: str | None,
    **optimize_kwargs: Any,
) -> Any:
    """Prefer ``gepa.optimize_anything``; fall back to ``gepa.optimize`` + adapter."""
    if optimize_fn is not None:
        return optimize_fn(
            seed_candidate=seed_candidate,
            adapter=adapter,
            trainset=trainset,
            valset=valset,
            reflection_lm=reflection_lm,
            max_metric_calls=max_metric_calls,
            objective=objective,
            background=background,
            **optimize_kwargs,
        )

    oa_mod = _try_import_optimize_anything()
    if oa_mod is not None:
        kwargs: dict[str, Any] = {
            "seed_candidate": seed_candidate,
            "evaluator": _evaluator_from_adapter(adapter),
            "dataset": trainset or None,
            "valset": valset,
            "objective": objective,
            "background": background,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        kwargs.update(optimize_kwargs)
        return oa_mod.optimize_anything(**kwargs)

    import gepa

    kwargs = {
        "seed_candidate": seed_candidate,
        "trainset": trainset,
        "valset": valset,
        "adapter": adapter,
        "reflection_lm": reflection_lm,
        "max_metric_calls": max_metric_calls,
    }
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    kwargs.update(optimize_kwargs)
    return gepa.optimize(**kwargs)


def _try_import_optimize_anything() -> Any | None:
    try:
        import gepa.optimize_anything as oa  # type: ignore[import-not-found]
    except ImportError:
        return None
    return oa


def _evaluator_from_adapter(
    adapter: HaystackGepaAdapter,
) -> Callable[[Any, Any], float | tuple[float, dict[str, Any]]]:
    """Adapt :class:`HaystackGepaAdapter` to a simple optimize_anything evaluator."""

    def _evaluate(candidate: Any, example: Any) -> tuple[float, dict[str, Any]]:
        cand = (
            candidate
            if isinstance(candidate, dict)
            else {adapter.component_key: str(candidate)}
        )
        data: HaystackDataInst
        if isinstance(example, Mapping):
            data = cast(HaystackDataInst, dict(example))
        else:
            data = HaystackDataInst(input=str(example))
        batch = adapter.evaluate([data], cand, capture_traces=True)
        score = float(batch.scores[0]) if batch.scores else 0.0
        traj = (batch.trajectories or [None])[0]
        side_info: dict[str, Any] = {
            "Output": batch.outputs[0]["output_text"] if batch.outputs else "",
            "Feedback": traj["feedback"] if traj else "",
        }
        if traj and traj.get("error"):
            side_info["Error"] = traj["error"]
        return score, side_info

    return _evaluate


def _best_candidate_from_result(raw: Any, *, fallback: dict[str, str]) -> dict[str, str]:
    if raw is None:
        return dict(fallback)
    best = getattr(raw, "best_candidate", None)
    if isinstance(best, dict) and best:
        return {str(k): str(v) for k, v in best.items()}
    if isinstance(raw, dict):
        inner = raw.get("best_candidate")
        if isinstance(inner, dict) and inner:
            return {str(k): str(v) for k, v in inner.items()}
        if all(isinstance(v, str) for v in raw.values()):
            return {str(k): str(v) for k, v in raw.items()}
    return dict(fallback)
