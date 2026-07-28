# Story: E6-S05 / E6.5
"""E6-S05 — Trace → test case (export JSONL + ``zaumzeug eval --trace``)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from zaumzeug.cli import _eval_command, build_parser
from zaumzeug.eval.runner import EvalError, EvalResult, run_eval
from zaumzeug.eval.trace import (
    TRACE_SCHEMA_VERSION,
    append_trace_to_valset,
    export_haystack_trace,
    load_trace_jsonl,
    trace_to_valset_row,
    traces_dir_for_harness,
)


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


def _minimal_eval_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    eval_section: dict | None = None,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    harness_dir.mkdir(parents=True, exist_ok=True)

    if eval_section is None:
        eval_section = {
            "framework": "builtin",
            "valset": "data/val.jsonl",
        }

    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": harness_name,
            "serve": {"hayhooks": {"port": 1416}},
            "eval": eval_section,
        },
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
        },
    )
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("You are a researcher.", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    _write_jsonl(
        harness_dir / "data" / "val.jsonl",
        [{"input": "placeholder", "expected_output": "unused"}],
    )
    return harness_dir


def _haystack_result(text: str, *, tools: list[str] | None = None) -> dict:
    """Minimal Haystack-shaped Agent.run result for unit tests."""
    tool_calls = None
    if tools:
        tool_calls = [SimpleNamespace(tool_name=name) for name in tools]
    last = SimpleNamespace(text=text, role="assistant", tool_calls=tool_calls)
    return {"last_message": last, "messages": [last]}


def test_e6_s05_ac1_trace_export_jsonl(tmp_path: Path) -> None:
    """AC-1: Haystack trace export writes JSONL under data/traces/."""
    harness_dir = tmp_path / "usr-harnesses" / "example"
    harness_dir.mkdir(parents=True)
    captured = datetime(2026, 7, 28, 18, 0, 0, tzinfo=timezone.utc)

    out = export_haystack_trace(
        harness_dir,
        "What broke in production?",
        _haystack_result("sorry, I hallucinated", tools=["web_fetch"]),
        expected_output="cite the failing stage",
        retrieval_context=["stage researcher timed out"],
        agent="researcher",
        filename="run-001.jsonl",
        captured_at=captured,
    )

    assert out == traces_dir_for_harness(harness_dir) / "run-001.jsonl"
    assert out.is_file()
    assert out.parent.name == "traces"
    assert out.parent.parent.name == "data"

    rows = load_trace_jsonl(out)
    assert len(rows) == 1
    row = rows[0]
    assert row["schema_version"] == TRACE_SCHEMA_VERSION
    assert row["input"] == "What broke in production?"
    assert row["actual_output"] == "sorry, I hallucinated"
    assert row["expected_output"] == "cite the failing stage"
    assert row["retrieval_context"] == ["stage researcher timed out"]
    assert row["tools_called"] == ["web_fetch"]
    assert row["agent"] == "researcher"
    assert row["captured_at"].startswith("2026-07-28")

    valset_row = trace_to_valset_row(row)
    assert valset_row == {
        "input": "What broke in production?",
        "expected_output": "cite the failing stage",
        "retrieval_context": ["stage researcher timed out"],
    }
    assert "actual_output" not in valset_row


def test_e6_s05_ac2_eval_trace_flag_scores(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-2: ``zaumzeug eval --trace <path>`` scores a single captured trace."""
    harness_dir = _minimal_eval_harness(tmp_path)
    trace_path = export_haystack_trace(
        harness_dir,
        "hello",
        _haystack_result("world"),
        expected_output="world",
        filename="pass.jsonl",
    )
    fail_path = export_haystack_trace(
        harness_dir,
        "hello",
        _haystack_result("nope"),
        expected_output="world",
        filename="fail.jsonl",
    )

    # Must not invoke the agent when --trace is set.
    def _boom(_inp: str) -> str:
        raise AssertionError("agent must not run for --trace scoring")

    passed = run_eval(
        "example",
        project_root=tmp_path,
        framework="builtin",
        trace=trace_path,
        agent_runner=_boom,
    )
    assert passed.framework == "builtin"
    assert passed.passed == 1
    assert passed.failed == 0
    assert passed.exit_code == 0
    assert passed.cases[0].actual_output == "world"

    failed = run_eval(
        "example",
        project_root=tmp_path,
        framework="builtin",
        trace=fail_path,
        agent_runner=_boom,
    )
    assert failed.failed == 1
    assert failed.exit_code == 1
    assert failed.cases[0].actual_output == "nope"

    # Relative path resolved under the harness (data/traces/...).
    relative = run_eval(
        "example",
        project_root=tmp_path,
        framework="builtin",
        trace="data/traces/pass.jsonl",
        agent_runner=_boom,
    )
    assert relative.exit_code == 0

    parser = build_parser()
    args = parser.parse_args(
        ["eval", "example", "--framework", "builtin", "--trace", str(trace_path)]
    )
    assert args.trace == str(trace_path)

    def _fake_run_eval(harness_name, **kwargs):
        assert harness_name == "example"
        assert kwargs.get("trace") == str(trace_path)
        return EvalResult(
            harness_name="example",
            harness_dir=harness_dir,
            framework="builtin",
            agent_name="researcher",
            passed=1,
            failed=0,
        )

    import zaumzeug.eval.runner as eval_runner

    monkeypatch.setattr(eval_runner, "run_eval", _fake_run_eval)
    code = _eval_command(args)
    captured = capsys.readouterr()
    assert code == 0
    assert "1 passed" in captured.out


def test_e6_s05_append_trace_to_valset(tmp_path: Path) -> None:
    """Helper: promote a scored trace into the valset JSONL (Journey C)."""
    harness_dir = tmp_path / "usr-harnesses" / "example"
    harness_dir.mkdir(parents=True)
    trace_path = export_haystack_trace(
        harness_dir,
        "fix query",
        _haystack_result("bad answer"),
        expected_output="good answer",
        filename="promote.jsonl",
    )
    valset = harness_dir / "data" / "val.jsonl"
    _write_jsonl(valset, [{"input": "seed", "expected_output": "ok"}])

    appended = append_trace_to_valset(trace_path, valset)
    assert appended == 1
    lines = [
        json.loads(line)
        for line in valset.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines[0] == {"input": "seed", "expected_output": "ok"}
    assert lines[1] == {
        "input": "fix query",
        "expected_output": "good answer",
    }


def test_e6_s05_trace_missing_file_errors(tmp_path: Path) -> None:
    """Missing --trace path → clear EvalError."""
    _minimal_eval_harness(tmp_path)
    with pytest.raises(EvalError, match="Trace file not found"):
        run_eval(
            "example",
            project_root=tmp_path,
            framework="builtin",
            trace=tmp_path / "missing.jsonl",
            agent_runner=lambda _inp: "unused",
        )
