# Story: E6-S08 / E6.8
"""E6-S08 AC-4 — rate --apply --compile with StubGEPA."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from zaumzeug.compile import CompileError
from zaumzeug.compile.gepa_runner import StubGEPA
from zaumzeug.eval.rate import run_rate
from zaumzeug.eval.trace import export_haystack_trace


_PLAIN_MODULE = '''\
import dspy

class ResearchModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.respond = dspy.Predict("question -> answer")

    def forward(self, question: str):
        return dspy.Prediction(answer="harness")
'''


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


def _purge_import(module_name: str) -> None:
    prefix = module_name + "."
    for key in list(sys.modules):
        if key == module_name or key.startswith(prefix):
            del sys.modules[key]


def _scaffold(project_root: Path, *, with_compile: bool = True) -> Path:
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": "example",
            "serve": {"hayhooks": {"port": 1416}},
            "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
            "deploy": {"eval_gate": "skip"},
        },
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"
    agent_body: dict = {
        "name": "researcher",
        "default_model_id": "mock",
        "agent": {"system_prompt": "prompts/system.md"},
    }
    if with_compile:
        agent_body["compile"] = {
            "module": "modules.researcher:ResearchModule",
            "task_model_id": "mock",
            "reflection_model_id": "mock",
            "trainset": "data/train.jsonl",
            "valset": "data/val.jsonl",
            "auto": "light",
        }
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
    if with_compile:
        module = agent_dir / "modules" / "researcher.py"
        module.parent.mkdir(parents=True, exist_ok=True)
        (agent_dir / "modules" / "__init__.py").write_text("", encoding="utf-8")
        module.write_text(_PLAIN_MODULE, encoding="utf-8")
    _write_jsonl(
        harness_dir / "data" / "val.jsonl",
        [{"input": "What is ZaumZeug?", "expected_output": "harness"}],
    )
    _write_jsonl(
        agent_dir / "data" / "val.jsonl",
        [{"question": "What is ZaumZeug?", "answer": "harness"}],
    )
    _write_jsonl(
        agent_dir / "data" / "train.jsonl",
        [{"question": "What is ZaumZeug?", "answer": "harness"}],
    )
    return harness_dir


def _haystack(text: str) -> dict:
    from types import SimpleNamespace

    last = SimpleNamespace(text=text, role="assistant", tool_calls=None)
    return {"last_message": last, "messages": [last]}


def test_e6_s08_ac4_compile_defaults_to_rated_agent(tmp_path: Path) -> None:
    """AC-4: --compile defaults to the rated agent only."""
    _purge_import("modules")
    harness_dir = _scaffold(tmp_path)
    trace = export_haystack_trace(
        harness_dir,
        "What broke?",
        _haystack("guess"),
        agent="researcher",
        filename="rate-compile.jsonl",
        extra={"source": "test"},
    )
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="cite the failing stage",
        decision="keep_train",
        no_input=True,
        apply=True,
        compile_after=True,
        gepa_cls=StubGEPA,
        stub_gepa=True,
    )
    assert result.compile_result is not None
    assert result.compile_result.exit_code == 0
    assert len(result.compile_result.agents) == 1
    assert result.compile_result.agents[0].agent_name == "researcher"
    assert result.compile_result.agents[0].gepa_invoked is True


def test_e6_s08_ac4_all_agents_flag(tmp_path: Path) -> None:
    """AC-4: --all-agents compiles the whole harness."""
    _purge_import("modules")
    harness_dir = _scaffold(tmp_path)
    # Second agent with compile
    agent2 = harness_dir / "agents" / "reviewer"
    _write_yaml(
        agent2 / "agent.yaml",
        {
            "name": "reviewer",
            "default_model_id": "mock",
            "agent": {"system_prompt": "prompts/system.md"},
            "compile": {
                "module": "modules.researcher:ResearchModule",
                "task_model_id": "mock",
                "reflection_model_id": "mock",
                "trainset": "data/train.jsonl",
                "valset": "data/val.jsonl",
                "auto": "light",
            },
        },
    )
    prompt = agent2 / "prompts" / "system.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("You are a reviewer.", encoding="utf-8")
    _write_yaml(
        agent2 / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {"mock": {"provider": "mock", "model": "harness-fixture"}},
        },
    )
    module = agent2 / "modules" / "researcher.py"
    module.parent.mkdir(parents=True, exist_ok=True)
    (agent2 / "modules" / "__init__.py").write_text("", encoding="utf-8")
    module.write_text(_PLAIN_MODULE, encoding="utf-8")
    _write_jsonl(
        agent2 / "data" / "val.jsonl",
        [{"question": "What is ZaumZeug?", "answer": "harness"}],
    )
    _write_jsonl(
        agent2 / "data" / "train.jsonl",
        [{"question": "What is ZaumZeug?", "answer": "harness"}],
    )
    # Update workflow to include both (compile discovers agents with compile.module)
    _write_yaml(
        harness_dir / "workflow.yaml",
        {
            "entry": "researcher",
            "stages": [{"agent": "researcher"}, {"agent": "reviewer"}],
        },
    )

    trace = export_haystack_trace(
        harness_dir,
        "What broke?",
        _haystack("guess"),
        agent="researcher",
        filename="all-agents.jsonl",
    )
    result = run_rate(
        "example",
        project_root=tmp_path,
        trace=trace,
        quality="fail",
        expected_output="cite",
        decision="keep_train",
        no_input=True,
        apply=True,
        compile_after=True,
        all_agents=True,
        gepa_cls=StubGEPA,
        stub_gepa=True,
    )
    assert result.compile_result is not None
    names = {a.agent_name for a in result.compile_result.agents}
    assert "researcher" in names
    assert "reviewer" in names


def test_e6_s08_ac4_compile_error_leaves_rating(tmp_path: Path) -> None:
    """AC-4: compile failure does not roll back the rating file."""
    _purge_import("modules")
    harness_dir = _scaffold(tmp_path)
    trace = export_haystack_trace(
        harness_dir,
        "What broke?",
        _haystack("guess"),
        agent="researcher",
        filename="compile-fail.jsonl",
    )

    def _boom(*_a, **_kw):
        raise CompileError("GEPA boom", suggestion="fix stubs")

    with patch("zaumzeug.compile.runner.run_compile", side_effect=_boom):
        try:
            run_rate(
                "example",
                project_root=tmp_path,
                trace=trace,
                quality="fail",
                expected_output="cite",
                decision="keep_train",
                no_input=True,
                apply=True,
                compile_after=True,
            )
            raised = False
        except CompileError:
            raised = True
    assert raised
    rating = harness_dir / "data" / "ratings" / "compile-fail.jsonl"
    assert rating.is_file()


def test_e6_s08_ac4_agent_without_compile_errors(tmp_path: Path) -> None:
    """AC-4: agent without compile: → CompileError."""
    harness_dir = _scaffold(tmp_path, with_compile=False)
    trace = export_haystack_trace(
        harness_dir,
        "What broke?",
        _haystack("guess"),
        agent="researcher",
        filename="no-compile.jsonl",
    )
    with pytest.raises(CompileError):
        run_rate(
            "example",
            project_root=tmp_path,
            trace=trace,
            quality="fail",
            expected_output="cite",
            decision="keep_val",
            no_input=True,
            apply=True,
            compile_after=True,
            gepa_cls=StubGEPA,
            stub_gepa=True,
        )
    # Rating already written before compile attempt
    assert (harness_dir / "data" / "ratings" / "no-compile.jsonl").is_file()
