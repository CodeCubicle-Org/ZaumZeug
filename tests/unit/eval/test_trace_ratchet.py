# Story: E8-S03 / E8.3
"""E8-S03 — Trace → dataset ratchet (production capture + JSONL merge)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from zaumzeug.eval.ratchet import (
    TRACE_CAPTURE_ENV,
    OTelTraceStub,
    ProductionTraceHook,
    haystack_track_stats,
    install_production_trace_hook,
    merge_traces_into_datasets,
    trace_capture_enabled,
)
from zaumzeug.eval.trace import load_trace_jsonl, traces_dir_for_harness


REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _haystack_result(text: str, *, tools: list[str] | None = None) -> dict:
    tool_calls = None
    if tools:
        tool_calls = [SimpleNamespace(tool_name=name) for name in tools]
    last = SimpleNamespace(text=text, role="assistant", tool_calls=tool_calls)
    return {"last_message": last, "messages": [last]}


class _FakeAgent:
    def __init__(self, text: str = "sorry, I hallucinated") -> None:
        self._text = text

    def run(self, messages: list[Any] | None = None, **kwargs: object) -> dict:
        del kwargs
        return _haystack_result(self._text, tools=["web_fetch"])


def test_e8_s03_ac1_production_trace_appends_jsonl(tmp_path: Path) -> None:
    """AC-1: Production traces append to dataset JSONL under data/."""
    harness_dir = tmp_path / "usr-harnesses" / "example"
    harness_dir.mkdir(parents=True)
    valset = harness_dir / "data" / "val.jsonl"
    train = harness_dir / "agents" / "researcher" / "data" / "train.jsonl"
    _write_jsonl(valset, [{"input": "seed", "expected_output": "ok"}])
    _write_jsonl(train, [{"question": "seed", "answer": "ok"}])

    user = SimpleNamespace(text="What broke in production?", role="user")
    agent = _FakeAgent()
    hook = install_production_trace_hook(
        agent,
        harness_dir,
        agent_name="researcher",
    )
    result = agent.run(messages=[user])
    assert result["last_message"].text == "sorry, I hallucinated"
    assert hook.last_trace_path is not None
    assert hook.last_trace_path.parent == traces_dir_for_harness(harness_dir)
    assert hook.last_trace_path.is_file()

    rows = load_trace_jsonl(hook.last_trace_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["input"] == "What broke in production?"
    assert row["actual_output"] == "sorry, I hallucinated"
    assert row["source"] == "production"
    assert row["agent"] == "researcher"
    assert row["track_stats"]["source"] == "haystack"
    assert row["track_stats"]["tools_called"] == ["web_fetch"]
    assert row["otel"]["stub"] is True
    assert any(span["name"] == "haystack.agent.run" for span in row["otel"]["spans"])

    merged = merge_traces_into_datasets(
        hook.last_trace_path,
        valset_path=valset,
        train_path=train,
        expected_output="cite the failing stage",
    )
    assert merged.val_appended == 1
    assert merged.train_appended == 1

    val_lines = [
        json.loads(line)
        for line in valset.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train_lines = [
        json.loads(line)
        for line in train.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert val_lines[0] == {"input": "seed", "expected_output": "ok"}
    assert val_lines[1] == {
        "input": "What broke in production?",
        "expected_output": "cite the failing stage",
    }
    assert train_lines[0] == {"question": "seed", "answer": "ok"}
    assert train_lines[1] == {
        "question": "What broke in production?",
        "answer": "cite the failing stage",
    }


def test_e8_s03_trace_capture_off_by_default() -> None:
    """Production capture is opt-in (privacy): yaml/env default off."""
    assert trace_capture_enabled(None, env={}) is False
    assert trace_capture_enabled(SimpleNamespace(trace_capture=None), env={}) is False
    assert (
        trace_capture_enabled(
            SimpleNamespace(trace_capture=SimpleNamespace(enabled=False)),
            env={},
        )
        is False
    )
    assert (
        trace_capture_enabled(
            SimpleNamespace(trace_capture=SimpleNamespace(enabled=True)),
            env={},
        )
        is True
    )
    assert trace_capture_enabled(None, env={TRACE_CAPTURE_ENV: "1"}) is True
    assert (
        trace_capture_enabled(
            SimpleNamespace(trace_capture=SimpleNamespace(enabled=True)),
            env={TRACE_CAPTURE_ENV: "0"},
        )
        is False
    )


def test_e8_s03_hook_export_failure_does_not_raise(tmp_path: Path) -> None:
    """A broken traces directory must not fail the live Agent.run."""
    harness_dir = tmp_path / "blocked"
    harness_dir.mkdir()
    # A file where the traces directory should be → mkdir fails.
    (harness_dir / "data").write_text("not a dir", encoding="utf-8")
    user = SimpleNamespace(text="hello", role="user")
    agent = _FakeAgent("ok")
    hook = ProductionTraceHook(harness_dir, agent="researcher")
    hook.install(agent)
    out = agent.run(messages=[user])
    assert out["last_message"].text == "ok"
    assert hook.last_trace_path is None
    assert hook.export_errors


def test_e8_s03_haystack_track_stats_and_otel_stub() -> None:
    result = _haystack_result("done", tools=["web_fetch"])
    stats = haystack_track_stats(result)
    assert stats["message_count"] == 1
    assert stats["tools_called"] == ["web_fetch"]
    stub = OTelTraceStub()
    with stub.start_span("haystack.agent.run", attributes={"agent": "researcher"}):
        pass
    payload = stub.as_dict()
    assert payload["stub"] is True
    assert payload["spans"][0]["ended"] is True
    assert payload["spans"][0]["attributes"]["agent"] == "researcher"


def test_e8_s03_ac3_replay_deferred_documented() -> None:
    """AC-3: user-docs note ``zaumzeug replay`` as deferred (PRD §9)."""
    live = (REPO_ROOT / "user-docs" / "guides" / "testing.md").read_text(encoding="utf-8")
    template = (
        REPO_ROOT / "install" / "templates" / "user-docs" / "guides" / "testing.md"
    ).read_text(encoding="utf-8")
    cli_live = (REPO_ROOT / "user-docs" / "reference" / "cli.md").read_text(
        encoding="utf-8"
    )
    cli_template = (
        REPO_ROOT / "install" / "templates" / "user-docs" / "reference" / "cli.md"
    ).read_text(encoding="utf-8")
    for text in (live, template, cli_live, cli_template):
        assert "zaumzeug replay" in text
        assert "deferred" in text.lower()
        assert "--trace" in text
