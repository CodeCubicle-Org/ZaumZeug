"""Human quality rating → dataset merge / optional compile (E6-S08 / E6.8).

Core path — no DeepEval / ``[eval]`` required. Primary SDK hook: :func:`run_rate`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from zaumzeug.config.harness_root import harness_dir as resolve_harness_dir
from zaumzeug.config.loader import ConfigValidationError, load_harness
from zaumzeug.config.resolver import load_agent_yaml
from zaumzeug.doctor.project import find_project_root
from zaumzeug.eval.ratchet import DatasetMergeResult, merge_traces_into_datasets
from zaumzeug.eval.trace import (
    TraceError,
    export_haystack_trace,
    load_trace_jsonl,
    traces_dir_for_harness,
)
from zaumzeug.runtime.workflow import StageResult, WorkflowRunResult

__all__ = [
    "DEFAULT_RATINGS_SUBDIR",
    "RATING_SCHEMA_VERSION",
    "RateError",
    "RateResult",
    "apply_rating_decision",
    "list_unrated_traces",
    "normalize_quality",
    "ratings_dir_for_harness",
    "resolve_dataset_paths",
    "run_rate",
    "select_last_agent_stage",
    "synthetic_haystack_result",
    "write_rating_jsonl",
]

RATING_SCHEMA_VERSION = 1
DEFAULT_RATINGS_SUBDIR = Path("data") / "ratings"

VALID_DECISIONS = frozenset({"keep_val", "keep_train", "discard"})
VALID_QUALITY_LABELS = frozenset({"pass", "partial", "fail"})

# Integer quality 1–5 → label (story rules).
_QUALITY_INT_MAP: dict[int, str] = {
    5: "pass",
    4: "partial",
    3: "partial",
    2: "fail",
    1: "fail",
}

# Rating-only fields — never copied into val/train rows.
RATING_ONLY_FIELDS = frozenset(
    {"quality", "score", "notes", "decision", "rater", "rated_at"}
)


class RateError(RuntimeError):
    """Rating / apply failed with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        harness_name: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.harness_name = harness_name
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(slots=True)
class RateResult:
    """Outcome of :func:`run_rate`."""

    harness_name: str
    rating_path: Path
    trace_path: Path
    decision: str
    quality: str
    score: int | None = None
    applied: bool = False
    merge: DatasetMergeResult | None = None
    compile_result: Any | None = None
    agent: str | None = None
    exit_code: int = 0


def ratings_dir_for_harness(harness_dir: Path | str) -> Path:
    """Return ``<harness_dir>/data/ratings``."""
    return Path(harness_dir) / DEFAULT_RATINGS_SUBDIR


def select_last_agent_stage(stages: Sequence[StageResult]) -> StageResult:
    """Walk *stages* reversed; return the first with ``kind == "agent"``."""
    for stage in reversed(stages):
        if stage.kind == "agent":
            return stage
    raise RateError(
        "No agent stage to rate (workflow has no agent stages)",
        suggestion=(
            "zaumzeug rate / run --rate rates the last agent stage; "
            "pipeline-only workflows cannot be rated"
        ),
    )


def synthetic_haystack_result(text: str) -> dict[str, Any]:
    """Minimal Haystack-shaped ``Agent.run`` result for ``run --rate`` export."""
    last = SimpleNamespace(text=text, role="assistant", tool_calls=None)
    return {"last_message": last, "messages": [last]}


def normalize_quality(quality: str | int) -> tuple[str, int | None]:
    """Normalize *quality* to ``(label, optional_score)``.

    Accepts ``pass`` / ``partial`` / ``fail`` or integer ``1–5``
    (5→pass, 3–4→partial, 1–2→fail).
    """
    if isinstance(quality, int):
        if quality not in _QUALITY_INT_MAP:
            raise RateError(
                f"Invalid quality score {quality}; expected integer 1–5",
                suggestion="Use 1–5 or pass|partial|fail",
            )
        return _QUALITY_INT_MAP[quality], quality

    label = str(quality).strip().lower()
    if label.isdigit():
        return normalize_quality(int(label))
    if label not in VALID_QUALITY_LABELS:
        raise RateError(
            f"Invalid quality {quality!r}; expected pass|partial|fail or 1–5",
            suggestion="Use pass, partial, fail, or an integer 1–5",
        )
    return label, None


def list_unrated_traces(harness_dir: Path | str) -> list[Path]:
    """Return trace paths under ``data/traces/`` with no matching rating (oldest first)."""
    traces_dir = traces_dir_for_harness(harness_dir)
    ratings_dir = ratings_dir_for_harness(harness_dir)
    if not traces_dir.is_dir():
        return []

    unrated: list[tuple[float, Path]] = []
    for path in traces_dir.glob("*.jsonl"):
        rating = ratings_dir / path.name
        if rating.is_file():
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        unrated.append((mtime, path))

    unrated.sort(key=lambda item: (item[0], str(item[1])))
    return [path for _, path in unrated]


def _resolve_trace_path(harness_dir: Path, trace_ref: str | Path) -> Path:
    path = Path(trace_ref)
    if path.is_absolute():
        return path
    candidate = (Path.cwd() / path).resolve()
    if candidate.is_file():
        return candidate
    return (harness_dir / path).resolve()


def _prompt(prompt: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    if not raw and default is not None:
        return default
    return raw


def _collect_interactive(
    *,
    actual_output: str,
    quality: str | int | None,
    expected_output: str | None,
    decision: str | None,
    notes: str | None,
) -> tuple[str, int | None, str, str, str]:
    """Prompt for missing rating fields. Returns quality, score, notes, expected, decision."""
    print("--- Rate harness output ---")
    print(f"actual_output:\n{actual_output}\n")

    if quality is None:
        raw_q = _prompt("quality (pass|partial|fail or 1-5)")
        if not raw_q:
            raise RateError(
                "quality is required",
                suggestion="Enter pass, partial, fail, or 1–5",
            )
        quality = raw_q

    quality_label, score = normalize_quality(quality)

    if notes is None:
        notes = _prompt("notes (optional)", default="")

    if expected_output is None:
        expected_output = _prompt("expected_output (gold answer)")

    if decision is None:
        default_decision = "keep_train" if quality_label in {"fail", "partial"} else "keep_val"
        decision = _prompt(
            "decision (keep_val|keep_train|discard)",
            default=default_decision,
        )

    decision = str(decision).strip().lower()
    if decision not in VALID_DECISIONS:
        raise RateError(
            f"Invalid decision {decision!r}; expected keep_val|keep_train|discard",
        )

    return quality_label, score, str(notes or ""), str(expected_output or ""), decision


def _require_noninteractive_fields(
    *,
    quality: str | int | None,
    expected_output: str | None,
    decision: str | None,
) -> tuple[str, int | None, str]:
    if quality is None:
        raise RateError(
            "quality is required in non-interactive mode",
            suggestion="Pass --quality pass|partial|fail|1-5 with --no-input",
        )
    if decision is None:
        raise RateError(
            "decision is required in non-interactive mode",
            suggestion="Pass --decision keep_val|keep_train|discard with --no-input",
        )
    quality_label, score = normalize_quality(quality)
    decision_norm = str(decision).strip().lower()
    if decision_norm not in VALID_DECISIONS:
        raise RateError(
            f"Invalid decision {decision!r}; expected keep_val|keep_train|discard",
        )
    # expected_output validated later when applying keep_* decisions
    del expected_output
    return quality_label, score, decision_norm


def resolve_dataset_paths(
    harness_dir: Path,
    *,
    harness_name: str,
    agent: str | None,
) -> tuple[list[Path], Path | None]:
    """Resolve deduped val paths and optional train path for *agent*.

    Val: ``eval.valset`` if configured, else ``data/val.jsonl``. If the rated
    agent's ``compile.valset`` resolves to a different file, include it too.
    Train: rated agent's ``compile.trainset`` when present.
    """
    harness_yaml = harness_dir / "harness.yaml"
    try:
        harness_config = load_harness(harness_yaml)
    except ConfigValidationError as exc:
        raise RateError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=f"Fix harness.yaml at {harness_yaml}",
        ) from exc

    if harness_config.eval is not None and harness_config.eval.valset:
        primary_val = (harness_dir / harness_config.eval.valset).resolve()
    else:
        primary_val = (harness_dir / "data" / "val.jsonl").resolve()

    val_paths: list[Path] = [primary_val]
    train_path: Path | None = None

    if agent:
        agent_dir = harness_dir / "agents" / agent
        try:
            _, agent_data = load_agent_yaml(harness_dir, agent)
        except Exception:  # noqa: BLE001 — optional compile section
            agent_data = {}
        compile_section = agent_data.get("compile") if isinstance(agent_data, dict) else None
        if isinstance(compile_section, dict):
            compile_valset = compile_section.get("valset")
            if compile_valset:
                compile_val = (agent_dir / str(compile_valset)).resolve()
                if compile_val not in {p.resolve() for p in val_paths}:
                    val_paths.append(compile_val)
            compile_trainset = compile_section.get("trainset")
            if compile_trainset:
                train_path = (agent_dir / str(compile_trainset)).resolve()

    # Dedup by resolve() equality while preserving order
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in val_paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)

    return deduped, train_path


def _artifact_ref(harness_dir: Path, agent: str | None) -> str | None:
    """Best-effort artifact pin/path for the rating record."""
    if not agent:
        return None
    agent_dir = harness_dir / "agents" / agent
    try:
        _, data = load_agent_yaml(harness_dir, agent)
    except Exception:  # noqa: BLE001
        data = {}
    agent_block = data.get("agent") if isinstance(data, dict) else None
    if isinstance(agent_block, dict):
        pinned = agent_block.get("artifact")
        if pinned:
            return str(pinned)
    current = agent_dir / "artifacts" / "current"
    if current.exists():
        return "artifacts/current"
    return None


def write_rating_jsonl(
    rating_path: Path,
    record: Mapping[str, Any],
    *,
    force: bool = False,
) -> Path:
    """Write one rating JSON object to *rating_path*."""
    rating_path = Path(rating_path)
    if rating_path.is_file() and not force:
        raise RateError(
            f"Rating already exists at {rating_path}",
            path=rating_path,
            suggestion="Pass --force to overwrite the existing rating",
        )
    rating_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        rating_path.write_text(
            json.dumps(dict(record), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise RateError(
            f"Failed to write rating to {rating_path}: {exc}",
            path=rating_path,
        ) from exc
    return rating_path


def apply_rating_decision(
    *,
    decision: str,
    trace_path: Path,
    expected_output: str | None,
    val_paths: Sequence[Path],
    train_path: Path | None,
) -> DatasetMergeResult:
    """Validate gold and merge into val/train per *decision*.

    Gold enforcement lives here — do not rely on append helpers that silently skip.
    """
    decision = decision.strip().lower()
    if decision == "discard":
        return DatasetMergeResult(val_appended=0, train_appended=0)

    if decision not in {"keep_val", "keep_train"}:
        raise RateError(
            f"Invalid decision {decision!r}; expected keep_val|keep_train|discard",
        )

    gold = (expected_output or "").strip()
    if not gold:
        raise RateError(
            "expected_output (gold) is required for keep_val / keep_train",
            suggestion=(
                "Pass --expected with the correct answer; "
                "high quality alone never copies actual_output as gold"
            ),
        )

    total_val = 0
    total_train = 0

    if decision == "keep_val":
        for val_path in val_paths:
            merged = merge_traces_into_datasets(
                trace_path,
                valset_path=val_path,
                expected_output=gold,
            )
            total_val += merged.val_appended
        return DatasetMergeResult(val_appended=total_val, train_appended=0)

    # keep_train → train AND val
    if train_path is None:
        raise RateError(
            "keep_train requires the rated agent to have compile.trainset",
            suggestion="Add compile.trainset to the agent.yaml or use keep_val / discard",
        )
    for val_path in val_paths:
        merged = merge_traces_into_datasets(
            trace_path,
            valset_path=val_path,
            expected_output=gold,
        )
        total_val += merged.val_appended
    merged_train = merge_traces_into_datasets(
        trace_path,
        train_path=train_path,
        expected_output=gold,
    )
    total_train += merged_train.train_appended
    return DatasetMergeResult(val_appended=total_val, train_appended=total_train)


def _build_rating_record(
    *,
    trace_row: Mapping[str, Any],
    quality: str,
    score: int | None,
    notes: str,
    expected_output: str,
    decision: str,
    agent: str | None,
    model_id: str | None,
    artifact: str | None,
    trace_path: Path,
    harness_dir: Path,
    rater: str = "dev",
    rated_at: datetime | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    stamp = rated_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)

    try:
        rel_trace = str(trace_path.relative_to(harness_dir)).replace("\\", "/")
    except ValueError:
        rel_trace = str(trace_path).replace("\\", "/")

    if stamp.tzinfo is timezone.utc or (
        stamp.utcoffset() is not None and stamp.utcoffset().total_seconds() == 0
    ):
        rated_at_str = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        rated_at_str = stamp.isoformat()

    record: dict[str, Any] = {
        "schema_version": RATING_SCHEMA_VERSION,
        "input": str(trace_row.get("input", "")),
        "actual_output": str(trace_row.get("actual_output", "")),
        "expected_output": expected_output,
        "quality": quality,
        "notes": notes,
        "decision": decision,
        "rater": rater,
        "rated_at": rated_at_str,
        "trace_path": rel_trace,
    }

    if score is not None:
        record["score"] = score
    if agent is not None:
        record["agent"] = agent
    if model_id is not None:
        record["model_id"] = model_id
    if artifact is not None:
        record["artifact"] = artifact
    if extra:
        record["extra"] = dict(extra)
    elif "source" in trace_row:
        record["extra"] = {"source": trace_row["source"]}
    return record


def format_rate_result(result: RateResult) -> str:
    """Human-readable summary for the CLI."""
    lines = [
        f"Rated {result.harness_name}: quality={result.quality} decision={result.decision}",
        f"  rating: {result.rating_path}",
        f"  trace:  {result.trace_path}",
    ]
    if result.agent:
        lines.append(f"  agent:  {result.agent}")
    if result.applied and result.merge is not None:
        lines.append(
            f"  merged: val+={result.merge.val_appended} "
            f"train+={result.merge.train_appended}"
        )
    if result.compile_result is not None:
        lines.append("  compile: ok")
    return "\n".join(lines)


def run_rate(
    harness_name: str,
    *,
    trace: Path | str | None = None,
    unrated: bool = False,
    workflow_result: WorkflowRunResult | None = None,
    user_input: str | None = None,
    quality: str | int | None = None,
    expected_output: str | None = None,
    decision: str | None = None,
    notes: str | None = None,
    apply: bool | None = None,
    compile_after: bool = False,
    all_agents: bool = False,
    force: bool = False,
    no_input: bool = False,
    project_root: Path | str | None = None,
    deploy: bool = False,
    gepa_cls: Any | None = None,
    stub_gepa: bool | None = None,
    rater: str = "dev",
    model_id: str | None = None,
    artifact: str | None = None,
    agent: str | None = None,
    input_fn: Callable[..., str] | None = None,
    abort: bool = False,
) -> RateResult:
    """Rate a harness turn and optionally merge into val/train + compile.

    Primary unit/SDK hook for E6-S08. No DeepEval dependency.
    """
    root = Path(project_root) if project_root is not None else find_project_root()
    harness_path = resolve_harness_dir(root, harness_name, deploy=deploy)
    harness_yaml = harness_path / "harness.yaml"
    if not harness_yaml.is_file():
        raise RateError(
            f"Harness '{harness_name}' not found at {harness_path} (missing harness.yaml)",
            path=harness_path,
            harness_name=harness_name,
            suggestion=f"Create the harness with `zaumzeug init {harness_name}`",
        )

    # --- Resolve / export trace ------------------------------------------------
    stage: StageResult | None = None
    export_extra: dict[str, Any] | None = None

    if workflow_result is not None:
        stage = select_last_agent_stage(workflow_result.stages)
        agent = agent or stage.stage_id
        model_id = model_id if model_id is not None else stage.model_id
        prompt_input = user_input if user_input is not None else ""
        haystack = synthetic_haystack_result(stage.output)
        export_extra = {"source": "run"}
        try:
            trace_path = export_haystack_trace(
                harness_path,
                prompt_input,
                haystack,
                agent=agent,
                extra=export_extra,
            )
        except TraceError as exc:
            raise RateError(
                str(exc),
                path=exc.path,
                harness_name=harness_name,
                suggestion=exc.suggestion,
            ) from exc
    elif unrated:
        pending = list_unrated_traces(harness_path)
        if not pending:
            raise RateError(
                f"No unrated traces under {traces_dir_for_harness(harness_path)}",
                harness_name=harness_name,
                suggestion="Capture a turn with zaumzeug run --rate or serve trace_capture",
            )
        trace_path = pending[0]
    elif trace is not None:
        trace_path = _resolve_trace_path(harness_path, trace)
    else:
        raise RateError(
            "Specify --trace PATH, --unrated, or use zaumzeug run --rate",
            harness_name=harness_name,
            suggestion="zaumzeug rate <harness> --trace data/traces/….jsonl",
        )

    if not trace_path.is_file():
        raise RateError(
            f"Trace not found: {trace_path}",
            path=trace_path,
            harness_name=harness_name,
            suggestion="Pass a path under data/traces/ or use --unrated",
        )

    try:
        rows = load_trace_jsonl(trace_path)
    except TraceError as exc:
        raise RateError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=exc.suggestion,
        ) from exc
    if not rows:
        raise RateError(
            f"Trace is empty: {trace_path}",
            path=trace_path,
            harness_name=harness_name,
        )
    trace_row = rows[0]

    # Agent / model from trace when not already set (run --rate sets them)
    if agent is None and trace_row.get("agent"):
        agent = str(trace_row["agent"])
    if model_id is None and trace_row.get("model_id"):
        model_id = str(trace_row["model_id"])
    if artifact is None:
        artifact = _artifact_ref(harness_path, agent)

    actual_output = str(trace_row.get("actual_output", ""))

    # --- Collect rating fields -------------------------------------------------
    notes_value = "" if notes is None and no_input else (notes or "")
    try:
        if no_input:
            quality_label, score, decision_norm = _require_noninteractive_fields(
                quality=quality,
                expected_output=expected_output,
                decision=decision,
            )
            expected_value = "" if expected_output is None else str(expected_output)
            notes_value = "" if notes is None else str(notes)
        else:
            # Interactive — optionally use injected input_fn
            if input_fn is not None:
                import builtins

                original_input = builtins.input
                builtins.input = input_fn  # type: ignore[assignment]
                try:
                    (
                        quality_label,
                        score,
                        notes_value,
                        expected_value,
                        decision_norm,
                    ) = _collect_interactive(
                        actual_output=actual_output,
                        quality=quality,
                        expected_output=expected_output,
                        decision=decision,
                        notes=notes,
                    )
                finally:
                    builtins.input = original_input
            else:
                (
                    quality_label,
                    score,
                    notes_value,
                    expected_value,
                    decision_norm,
                ) = _collect_interactive(
                    actual_output=actual_output,
                    quality=quality,
                    expected_output=expected_output,
                    decision=decision,
                    notes=notes,
                )
    except KeyboardInterrupt as exc:
        raise RateError(
            "Rating aborted; datasets unchanged",
            harness_name=harness_name,
            suggestion="Re-run zaumzeug rate when ready",
        ) from exc

    if abort:
        # Test seam: simulate skip after collection, before write/merge
        raise RateError(
            "Rating aborted; datasets unchanged",
            harness_name=harness_name,
        )

    # --- Write rating ----------------------------------------------------------
    rating_path = ratings_dir_for_harness(harness_path) / trace_path.name
    record = _build_rating_record(
        trace_row=trace_row,
        quality=quality_label,
        score=score,
        notes=notes_value,
        expected_output=expected_value,
        decision=decision_norm,
        agent=agent,
        model_id=model_id,
        artifact=artifact,
        trace_path=trace_path,
        harness_dir=harness_path,
        rater=rater,
        extra=export_extra or (
            {"source": trace_row["source"]} if "source" in trace_row else None
        ),
    )
    write_rating_jsonl(rating_path, record, force=force)

    # --- Apply (merge) ---------------------------------------------------------
    # Interactive: apply by default for keep_*; non-interactive: require --apply
    should_apply = apply
    if should_apply is None:
        should_apply = (not no_input) and decision_norm in {"keep_val", "keep_train"}

    merge_result: DatasetMergeResult | None = None
    applied = False
    if should_apply and decision_norm in {"keep_val", "keep_train"}:
        val_paths, train_path = resolve_dataset_paths(
            harness_path,
            harness_name=harness_name,
            agent=agent,
        )
        merge_result = apply_rating_decision(
            decision=decision_norm,
            trace_path=trace_path,
            expected_output=expected_value,
            val_paths=val_paths,
            train_path=train_path,
        )
        applied = True
    elif should_apply and decision_norm == "discard":
        applied = False  # discard never merges
    elif decision_norm in {"keep_val", "keep_train"} and not should_apply:
        # Non-interactive without --apply: rating written, no merge
        pass

    # --- Optional compile ------------------------------------------------------
    compile_result = None
    if compile_after:
        from zaumzeug.compile.runner import run_compile

        compile_kwargs: dict[str, Any] = {
            "project_root": root,
            "deploy": deploy,
        }
        if gepa_cls is not None:
            compile_kwargs["gepa_cls"] = gepa_cls
        if stub_gepa is not None:
            compile_kwargs["stub_gepa"] = stub_gepa
        if all_agents:
            compile_kwargs["agent_name"] = None
        else:
            if not agent:
                raise RateError(
                    "Cannot compile: rated agent is unknown",
                    harness_name=harness_name,
                    suggestion="Ensure the trace has an agent field or use --all-agents",
                )
            compile_kwargs["agent_name"] = agent
        # CompileError surfaces as today; ratings already written are not rolled back.
        compile_result = run_compile(harness_name, **compile_kwargs)

    return RateResult(
        harness_name=harness_name,
        rating_path=rating_path,
        trace_path=trace_path,
        decision=decision_norm,
        quality=quality_label,
        score=score,
        applied=applied,
        merge=merge_result,
        compile_result=compile_result,
        agent=agent,
        exit_code=0,
    )
