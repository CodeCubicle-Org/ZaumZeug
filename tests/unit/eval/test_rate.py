# Story: E6-S08 / E6.8
"""E6-S08 — Human quality rating → compile feedback loop (unit)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
import yaml

from zaumzeug.eval.rate import (
    RateError,
    apply_rating_decision,
    list_unrated_traces,
    normalize_quality,
    ratings_dir_for_harness,
    resolve_dataset_paths,
    run_rate,
)
from zaumzeug.eval.trace import export_haystack_trace, traces_dir_for_harness


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _haystack_result(text: str) -> dict:
    from types import SimpleNamespace

    last = SimpleNamespace(text=text, role="assistant", tool_calls=None)
    return {"last_message": last, "messages": [last]}


def _minimal_rate_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    with_eval: bool = True,
    compile_valset: str | None = "data/val.jsonl",
    shared_val: bool = False,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    harness_dir.mkdir(parents=True, exist_ok=True)

    body: dict = {
        "name": harness_name,
        "serve": {"hayhooks": {"port": 1416}},
    }
    if with_eval:
        body["eval"] = {"framework": "builtin", "valset": "data/val.jsonl"}

    _write_yaml(harness_dir / "harness.yaml", body)
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"
    agent_body: dict = {
        "name": "researcher",
        "agent": {"system_prompt": "prompts/system.md"},
        "compile": {
            "module": "modules.researcher:ResearchModule",
            "task_model_id": "mock",
            "reflection_model_id": "mock",
            "trainset": "data/train.jsonl",
            "auto": "light",
        },
    }
    if compile_valset is not None:
        if shared_val:
            agent_body["compile"]["valset"] = "../../data/val.jsonl"
        else:
            agent_body["compile"]["valset"] = compile_valset
    _write_yaml(agent_dir / "agent.yaml", agent_body)
    prompt = agent_dir / "prompts" / "system.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("You are a researcher.", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {"mock": {"provider": "mock", "model": "harness-fixture"}},
        },
    )
    _write_jsonl(
        harness_dir / "data" / "val.jsonl",
        [{"input": "placeholder", "expected_output": "unused"}],
    )
    if not shared_val and compile_valset is not None:
        _write_jsonl(
            agent_dir / "data" / "val.jsonl",
            [{"question": "placeholder", "answer": "unused"}],
        )
    _write_jsonl(
        agent_dir / "data" / "train.jsonl",
        [{"question": "placeholder", "answer": "unused"}],
    )
    return harness_dir


def _export_trace(harness_dir: Path, *, stem: str = "trace-001", text: str = "bad") -> Path:
    return export_haystack_trace(
        harness_dir,
        "What broke?",
        _haystack_result(text),
        agent="researcher",
        filename=f"{stem}.jsonl",
        extra={"source": "test", "model_id": "openai/gpt-4.1-mini"},
    )


def test_e6_s08_ac1_rate_writes_ratings_jsonl(tmp_path: Path) -> None:
    """AC-1: run_rate writes data/ratings/<stem>.jsonl with trace_path."""
    harness_dir = _minimal_rate_harness(tmp_path)
    trace = _export_trace(harness_dir)
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="cite the failing stage",
        decision="discard",
        notes="missed citation",
        no_input=True,
        apply=False,
    )
    assert result.rating_path.is_file()
    assert result.rating_path.parent == ratings_dir_for_harness(harness_dir)
    record = json.loads(result.rating_path.read_text(encoding="utf-8").strip())
    assert record["trace_path"].endswith("trace-001.jsonl")
    assert record["quality"] == "fail"
    assert record["decision"] == "discard"
    assert record["notes"] == "missed citation"
    assert "expected_output" in record


def test_e6_s08_ac1_unrated_one_stem(tmp_path: Path) -> None:
    """AC-1: --unrated rates exactly one oldest unrated stem."""
    harness_dir = _minimal_rate_harness(tmp_path)
    t1 = _export_trace(harness_dir, stem="trace-older")
    time.sleep(0.05)
    _export_trace(harness_dir, stem="trace-newer", text="also bad")
    result = run_rate(
        "example",
        project_root=tmp_path,
        unrated=True,
        quality="fail",
        expected_output="gold",
        decision="discard",
        no_input=True,
        apply=False,
    )
    assert result.trace_path.resolve() == t1.resolve()
    assert (ratings_dir_for_harness(harness_dir) / "trace-older.jsonl").is_file()
    assert not (ratings_dir_for_harness(harness_dir) / "trace-newer.jsonl").is_file()


def test_e6_s08_ac1_unrated_oldest_first(tmp_path: Path) -> None:
    """AC-1: list_unrated_traces is oldest-first."""
    harness_dir = _minimal_rate_harness(tmp_path)
    older = _export_trace(harness_dir, stem="a-old")
    time.sleep(0.05)
    newer = _export_trace(harness_dir, stem="b-new", text="x")
    pending = list_unrated_traces(harness_dir)
    assert pending[0].resolve() == older.resolve()
    assert pending[1].resolve() == newer.resolve()


def test_e6_s08_ac1_force_overwrite(tmp_path: Path) -> None:
    """AC-1: --force overwrites an existing rating file."""
    harness_dir = _minimal_rate_harness(tmp_path)
    trace = _export_trace(harness_dir)
    run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        decision="discard",
        no_input=True,
        apply=False,
    )
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="pass",
        decision="discard",
        notes="re-rated",
        no_input=True,
        apply=False,
        force=True,
    )
    record = json.loads(result.rating_path.read_text(encoding="utf-8").strip())
    assert record["quality"] == "pass"
    assert record["notes"] == "re-rated"


def test_e6_s08_ac1_existing_rating_errors_without_force(tmp_path: Path) -> None:
    """AC-1: existing rating errors unless --force."""
    harness_dir = _minimal_rate_harness(tmp_path)
    trace = _export_trace(harness_dir)
    run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        decision="discard",
        no_input=True,
        apply=False,
    )
    with pytest.raises(RateError, match="already exists"):
        run_rate(
            "example",
            project_root=tmp_path,
            trace=trace,
            quality="fail",
            decision="discard",
            no_input=True,
            apply=False,
        )


def test_e6_s08_ac1_trace_immutable(tmp_path: Path) -> None:
    """AC-1: rating leaves the original trace unchanged."""
    harness_dir = _minimal_rate_harness(tmp_path)
    trace = _export_trace(harness_dir)
    before = trace.read_text(encoding="utf-8")
    run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="gold",
        decision="keep_val",
        no_input=True,
        apply=True,
    )
    assert trace.read_text(encoding="utf-8") == before


def test_e6_s08_ac1_no_eval_block_fallback(tmp_path: Path) -> None:
    """AC-1: harness without eval: still rates (fallback data/val.jsonl)."""
    harness_dir = _minimal_rate_harness(tmp_path, with_eval=False)
    trace = _export_trace(harness_dir)
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="gold",
        decision="keep_val",
        no_input=True,
        apply=True,
    )
    assert result.applied is True
    val = harness_dir / "data" / "val.jsonl"
    rows = [json.loads(line) for line in val.read_text(encoding="utf-8").splitlines() if line]
    assert any(r.get("expected_output") == "gold" for r in rows)


def test_e6_s08_ac1_rate_error_domain(tmp_path: Path) -> None:
    """AC-1: domain failures raise RateError."""
    with pytest.raises(RateError, match="not found"):
        run_rate(
            "missing",
            project_root=tmp_path,
            unrated=True,
            quality="fail",
            decision="discard",
            no_input=True,
        )


def test_e6_s08_ac1_no_deepeval_required(tmp_path: Path) -> None:
    """AC-1: rate path does not import / require DeepEval."""
    harness_dir = _minimal_rate_harness(tmp_path)
    trace = _export_trace(harness_dir)
    import sys

    blocked = {k for k in sys.modules if "deepeval" in k.lower()}
    for key in blocked:
        del sys.modules[key]
    run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        decision="discard",
        no_input=True,
        apply=False,
    )
    assert not any("deepeval" in k.lower() for k in sys.modules)


def test_e6_s08_ac3_apply_keep_train_merges_val_and_train(tmp_path: Path) -> None:
    """AC-3: keep_train merges into train AND val."""
    harness_dir = _minimal_rate_harness(tmp_path, shared_val=True)
    trace = _export_trace(harness_dir)
    val = harness_dir / "data" / "val.jsonl"
    train = harness_dir / "agents" / "researcher" / "data" / "train.jsonl"
    val_before = val.read_text(encoding="utf-8")
    train_before = train.read_text(encoding="utf-8")
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="cite the failing stage",
        decision="keep_train",
        no_input=True,
        apply=True,
    )
    assert result.merge is not None
    assert result.merge.val_appended >= 1
    assert result.merge.train_appended >= 1
    assert "cite the failing stage" in val.read_text(encoding="utf-8")
    assert "cite the failing stage" in train.read_text(encoding="utf-8")
    assert val.read_text(encoding="utf-8") != val_before
    assert train.read_text(encoding="utf-8") != train_before


def test_e6_s08_ac3_keep_val_val_only(tmp_path: Path) -> None:
    """AC-3: keep_val touches val only."""
    harness_dir = _minimal_rate_harness(tmp_path, shared_val=True)
    trace = _export_trace(harness_dir)
    train = harness_dir / "agents" / "researcher" / "data" / "train.jsonl"
    train_before = train.read_text(encoding="utf-8")
    run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="pass",
        expected_output="gold answer",
        decision="keep_val",
        no_input=True,
        apply=True,
    )
    assert train.read_text(encoding="utf-8") == train_before
    val_rows = [
        json.loads(line)
        for line in (harness_dir / "data" / "val.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert any(r.get("expected_output") == "gold answer" for r in val_rows)


def test_e6_s08_ac3_discard_no_merge(tmp_path: Path) -> None:
    """AC-3: discard never merges."""
    harness_dir = _minimal_rate_harness(tmp_path, shared_val=True)
    trace = _export_trace(harness_dir)
    val = harness_dir / "data" / "val.jsonl"
    train = harness_dir / "agents" / "researcher" / "data" / "train.jsonl"
    val_before = val.read_text(encoding="utf-8")
    train_before = train.read_text(encoding="utf-8")
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="ignored",
        decision="discard",
        no_input=True,
        apply=True,
    )
    assert result.applied is False
    assert val.read_text(encoding="utf-8") == val_before
    assert train.read_text(encoding="utf-8") == train_before


def test_e6_s08_ac3_missing_expected_errors(tmp_path: Path) -> None:
    """AC-3: missing gold → RateError before merge helpers."""
    harness_dir = _minimal_rate_harness(tmp_path, shared_val=True)
    trace = _export_trace(harness_dir)
    with pytest.raises(RateError, match="expected_output"):
        run_rate(
            "example",
            project_root=tmp_path,
            trace=trace,
            quality="fail",
            expected_output="",
            decision="keep_train",
            no_input=True,
            apply=True,
        )


def test_e6_s08_ac3_high_quality_no_actual_as_gold(tmp_path: Path) -> None:
    """AC-3: high quality alone must never copy actual_output as gold."""
    harness_dir = _minimal_rate_harness(tmp_path, shared_val=True)
    trace = _export_trace(harness_dir, text="hallucinated answer")
    with pytest.raises(RateError, match="expected_output"):
        run_rate(
            "example",
            project_root=tmp_path,
            trace=trace,
            quality="pass",
            expected_output="",
            decision="keep_val",
            no_input=True,
            apply=True,
        )
    val_text = (harness_dir / "data" / "val.jsonl").read_text(encoding="utf-8")
    assert "hallucinated answer" not in val_text or "placeholder" in val_text


def test_e6_s08_ac3_rating_fields_not_in_datasets(tmp_path: Path) -> None:
    """AC-3: rating-only fields never appear in dataset rows."""
    harness_dir = _minimal_rate_harness(tmp_path, shared_val=True)
    trace = _export_trace(harness_dir)
    run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="cite stage",
        decision="keep_train",
        notes="tone ok",
        no_input=True,
        apply=True,
    )
    val_lines = (harness_dir / "data" / "val.jsonl").read_text(encoding="utf-8")
    train_lines = (
        harness_dir / "agents" / "researcher" / "data" / "train.jsonl"
    ).read_text(encoding="utf-8")
    for banned in ("quality", "notes", "decision", "rater", "rated_at", "score"):
        # Only check newly appended rows — scan last line of each file
        last_val = [json.loads(l) for l in val_lines.splitlines() if l][-1]
        last_train = [json.loads(l) for l in train_lines.splitlines() if l][-1]
        assert banned not in last_val
        assert banned not in last_train


def test_e6_s08_ac3_dedupes_same_valset_path(tmp_path: Path) -> None:
    """AC-3: shared eval/compile valset path is appended once."""
    harness_dir = _minimal_rate_harness(tmp_path, shared_val=True)
    val_paths, _ = resolve_dataset_paths(
        harness_dir, harness_name="example", agent="researcher"
    )
    assert len(val_paths) == 1
    trace = _export_trace(harness_dir)
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="once",
        decision="keep_val",
        no_input=True,
        apply=True,
    )
    assert result.merge is not None
    assert result.merge.val_appended == 1


def test_e6_s08_ac3_dual_val_paths_when_different(tmp_path: Path) -> None:
    """AC-3: distinct eval + compile valset paths both receive the gold row."""
    harness_dir = _minimal_rate_harness(tmp_path, shared_val=False)
    val_paths, _ = resolve_dataset_paths(
        harness_dir, harness_name="example", agent="researcher"
    )
    assert len(val_paths) == 2
    trace = _export_trace(harness_dir)
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="dual gold",
        decision="keep_val",
        no_input=True,
        apply=True,
    )
    assert result.merge is not None
    assert result.merge.val_appended == 2
    harness_val = (harness_dir / "data" / "val.jsonl").read_text(encoding="utf-8")
    agent_val = (
        harness_dir / "agents" / "researcher" / "data" / "val.jsonl"
    ).read_text(encoding="utf-8")
    assert "dual gold" in harness_val
    assert "dual gold" in agent_val


def test_e6_s08_ac6_records_model_id_and_artifact(tmp_path: Path) -> None:
    """AC-6: rating stores model_id and optional artifact."""
    harness_dir = _minimal_rate_harness(tmp_path)
    # Pin artifact on agent.yaml
    agent_yaml = harness_dir / "agents" / "researcher" / "agent.yaml"
    data = yaml.safe_load(agent_yaml.read_text(encoding="utf-8"))
    data["agent"]["artifact"] = "artifacts/20260826T120000Z"
    agent_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    trace = export_haystack_trace(
        harness_dir,
        "What broke?",
        _haystack_result("bad"),
        agent="researcher",
        filename="trace-model.jsonl",
        extra={"source": "test"},
    )
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        decision="discard",
        no_input=True,
        apply=False,
        model_id="openai/gpt-4.1-mini",
    )
    record = json.loads(result.rating_path.read_text(encoding="utf-8").strip())
    assert record["model_id"] == "openai/gpt-4.1-mini"
    assert record["artifact"] == "artifacts/20260826T120000Z"
    assert record["agent"] == "researcher"


def test_normalize_quality_integer_mapping() -> None:
    assert normalize_quality(5) == ("pass", 5)
    assert normalize_quality(4) == ("partial", 4)
    assert normalize_quality(3) == ("partial", 3)
    assert normalize_quality(2) == ("fail", 2)
    assert normalize_quality(1) == ("fail", 1)
    assert normalize_quality("pass") == ("pass", None)


def test_apply_discard_noop(tmp_path: Path) -> None:
    merged = apply_rating_decision(
        decision="discard",
        trace_path=tmp_path / "missing.jsonl",
        expected_output=None,
        val_paths=[],
        train_path=None,
    )
    assert merged.val_appended == 0
    assert merged.train_appended == 0
