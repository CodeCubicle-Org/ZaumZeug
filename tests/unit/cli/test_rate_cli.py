# Story: E6-S08 / E6.8
"""E6-S08 — CLI ``zaumzeug rate`` / ``run --rate`` (AC-2, AC-5)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from zaumzeug.cli import _rate_command, _run_command, build_parser
from zaumzeug.eval.rate import RateError, select_last_agent_stage
from zaumzeug.eval.trace import load_trace_jsonl, traces_dir_for_harness
from zaumzeug.runtime.workflow import StageResult, WorkflowRunResult


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


def _scaffold(project_root: Path) -> Path:
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": "example",
            "serve": {"hayhooks": {"port": 1416}},
            "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
        },
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {
            "entry": "researcher",
            "stages": [
                {"agent": "researcher"},
                {"pipeline": "summarize"},
            ],
        },
    )
    agent_dir = harness_dir / "agents" / "researcher"
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
            "compile": {
                "module": "modules.researcher:ResearchModule",
                "task_model_id": "mock",
                "reflection_model_id": "mock",
                "trainset": "data/train.jsonl",
                "valset": "../../data/val.jsonl",
                "auto": "light",
            },
        },
    )
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
    _write_jsonl(
        agent_dir / "data" / "train.jsonl",
        [{"question": "placeholder", "answer": "unused"}],
    )
    return harness_dir


def test_e6_s08_ac2_run_rate_exports_last_agent_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-2: run --rate exports last agent stage via synthetic Haystack + rate."""
    harness_dir = _scaffold(tmp_path)
    monkeypatch.chdir(tmp_path)

    workflow = WorkflowRunResult(
        harness_name="example",
        stages=[
            StageResult(
                stage_id="researcher",
                kind="agent",
                output="agent said this",
                model_id="openai/gpt-4.1-mini",
            ),
        ],
        final_output="agent said this",
    )

    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "example",
            "--input",
            "What broke?",
            "--rate",
            "--no-input",
            "--quality",
            "fail",
            "--expected",
            "cite stage",
            "--decision",
            "discard",
        ]
    )

    with patch("zaumzeug.cli.run_workflow", return_value=workflow):
        with patch("zaumzeug.doctor.project.find_project_root", return_value=tmp_path):
            code = _run_command(args)

    assert code == 0
    traces = list(traces_dir_for_harness(harness_dir).glob("*.jsonl"))
    assert len(traces) == 1
    rows = load_trace_jsonl(traces[0])
    assert rows[0]["actual_output"] == "agent said this"
    assert rows[0]["agent"] == "researcher"
    assert rows[0].get("source") == "run"
    ratings = list((harness_dir / "data" / "ratings").glob("*.jsonl"))
    assert len(ratings) == 1


def test_e6_s08_ac2_last_agent_before_pipeline() -> None:
    """AC-2: when stages are [agent, pipeline], rate the agent — not the pipeline."""
    stages = [
        StageResult(stage_id="researcher", kind="agent", output="from agent", model_id="m"),
        StageResult(stage_id="summarize", kind="pipeline", output="from pipeline"),
    ]
    selected = select_last_agent_stage(stages)
    assert selected.stage_id == "researcher"
    assert selected.output == "from agent"
    assert selected.model_id == "m"


def test_e6_s08_ac2_pipeline_only_errors() -> None:
    """AC-2: pipeline-only workflow → RateError."""
    stages = [
        StageResult(stage_id="summarize", kind="pipeline", output="pipeline only"),
    ]
    with pytest.raises(RateError, match="No agent stage"):
        select_last_agent_stage(stages)


def test_e6_s08_ac2_source_run_not_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-2: run --rate export uses extra.source=run (not production hook)."""
    harness_dir = _scaffold(tmp_path)
    monkeypatch.chdir(tmp_path)
    workflow = WorkflowRunResult(
        harness_name="example",
        stages=[
            StageResult(stage_id="researcher", kind="agent", output="out", model_id="mock"),
        ],
        final_output="out",
    )
    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "example",
            "--input",
            "q",
            "--rate",
            "--no-input",
            "--quality",
            "fail",
            "--decision",
            "discard",
        ]
    )
    with patch("zaumzeug.cli.run_workflow", return_value=workflow):
        with patch("zaumzeug.doctor.project.find_project_root", return_value=tmp_path):
            assert _run_command(args) == 0
    rows = load_trace_jsonl(next(traces_dir_for_harness(harness_dir).glob("*.jsonl")))
    assert rows[0]["source"] == "run"
    assert rows[0].get("source") != "production"


def test_e6_s08_ac2_skip_no_merge(tmp_path: Path) -> None:
    """AC-2: abort leaves val/train unchanged (rating may be absent)."""
    harness_dir = _scaffold(tmp_path)
    val = harness_dir / "data" / "val.jsonl"
    train = harness_dir / "agents" / "researcher" / "data" / "train.jsonl"
    val_before = val.read_text(encoding="utf-8")
    train_before = train.read_text(encoding="utf-8")

    workflow = WorkflowRunResult(
        harness_name="example",
        stages=[
            StageResult(stage_id="researcher", kind="agent", output="out", model_id="m"),
        ],
        final_output="out",
    )
    from zaumzeug.eval.rate import run_rate

    with pytest.raises(RateError, match="aborted"):
        run_rate(
            "example",
            project_root=tmp_path,
            workflow_result=workflow,
            user_input="q",
            quality="fail",
            expected_output="gold",
            decision="keep_train",
            no_input=True,
            apply=True,
            abort=True,
        )
    assert val.read_text(encoding="utf-8") == val_before
    assert train.read_text(encoding="utf-8") == train_before


def test_e6_s08_ac5_noninteractive_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-5: non-interactive rate via --quality/--expected/--decision/--no-input."""
    harness_dir = _scaffold(tmp_path)
    monkeypatch.chdir(tmp_path)
    from zaumzeug.eval.trace import export_haystack_trace

    last = SimpleNamespace(text="bad", role="assistant", tool_calls=None)
    trace = export_haystack_trace(
        harness_dir,
        "q",
        {"last_message": last, "messages": [last]},
        agent="researcher",
        filename="cli-trace.jsonl",
        extra={"source": "test"},
    )
    parser = build_parser()
    args = parser.parse_args(
        [
            "rate",
            "example",
            "--trace",
            str(trace),
            "--quality",
            "fail",
            "--expected",
            "gold",
            "--decision",
            "keep_val",
            "--notes",
            "fix",
            "--apply",
            "--no-input",
        ]
    )
    with patch("zaumzeug.doctor.project.find_project_root", return_value=tmp_path):
        code = _rate_command(args)
    assert code == 0
    assert (harness_dir / "data" / "ratings" / "cli-trace.jsonl").is_file()
    val_text = (harness_dir / "data" / "val.jsonl").read_text(encoding="utf-8")
    assert "gold" in val_text


def test_e6_s08_ac5_missing_fields_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-5: missing required non-interactive fields → non-zero exit."""
    harness_dir = _scaffold(tmp_path)
    monkeypatch.chdir(tmp_path)
    from zaumzeug.eval.trace import export_haystack_trace

    last = SimpleNamespace(text="bad", role="assistant", tool_calls=None)
    trace = export_haystack_trace(
        harness_dir,
        "q",
        {"last_message": last, "messages": [last]},
        agent="researcher",
        filename="missing.jsonl",
    )
    parser = build_parser()
    args = parser.parse_args(
        ["rate", "example", "--trace", str(trace), "--no-input", "--decision", "discard"]
    )
    with patch("zaumzeug.doctor.project.find_project_root", return_value=tmp_path):
        code = _rate_command(args)
    assert code == 1


def test_e6_s08_ac5_quality_integer_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-5: integer quality 1–5 maps per rules."""
    harness_dir = _scaffold(tmp_path)
    monkeypatch.chdir(tmp_path)
    from zaumzeug.eval.trace import export_haystack_trace

    last = SimpleNamespace(text="bad", role="assistant", tool_calls=None)
    trace = export_haystack_trace(
        harness_dir,
        "q",
        {"last_message": last, "messages": [last]},
        agent="researcher",
        filename="score.jsonl",
    )
    parser = build_parser()
    args = parser.parse_args(
        [
            "rate",
            "example",
            "--trace",
            str(trace),
            "--quality",
            "2",
            "--decision",
            "discard",
            "--no-input",
        ]
    )
    with patch("zaumzeug.doctor.project.find_project_root", return_value=tmp_path):
        assert _rate_command(args) == 0
    record = json.loads(
        (harness_dir / "data" / "ratings" / "score.jsonl").read_text(encoding="utf-8").strip()
    )
    assert record["quality"] == "fail"
    assert record["score"] == 2
