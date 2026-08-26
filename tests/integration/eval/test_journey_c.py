# Story: E8-S03 / E8.3
"""E8-S03 AC-2 — Journey C: trace → valset → eval → compile → deploy."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

from zaumzeug.compile.gepa_runner import StubGEPA
from zaumzeug.compile.runner import run_compile
from zaumzeug.deploy.packager import package_harness
from zaumzeug.doctor.report import CheckResult, DoctorReport
from zaumzeug.eval.ratchet import install_production_trace_hook, merge_traces_into_datasets
from zaumzeug.eval.runner import run_eval


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


def _ok_doctor(**kwargs: object) -> DoctorReport:
    del kwargs
    return DoctorReport(
        checks=[CheckResult(name="preflight", severity="pass", message="ok")],
    )


def _scaffold_journey_harness(project_root: Path) -> Path:
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": "example",
            "serve": {"hayhooks": {"port": 1416}},
            "eval": {
                "framework": "builtin",
                "valset": "data/val.jsonl",
                "trace_capture": {"enabled": True},
            },
            "deploy": {"eval_gate": "skip"},
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
    prompt = agent_dir / "prompts" / "system.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("You are a researcher.", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
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


def test_e8_s03_ac2_trace_to_compile_loop(tmp_path: Path) -> None:
    """AC-2: Production trace → valset → eval → compile → deploy."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    harness_dir = _scaffold_journey_harness(tmp_path)
    valset = harness_dir / "data" / "val.jsonl"
    train = harness_dir / "agents" / "researcher" / "data" / "train.jsonl"

    last = SimpleNamespace(text="I guessed", role="assistant", tool_calls=None)
    agent = SimpleNamespace()

    def _run(*, messages: list[object]) -> dict:
        del messages
        return {"last_message": last, "messages": [last]}

    agent.run = _run
    user = SimpleNamespace(text="What broke in production?", role="user")
    hook = install_production_trace_hook(
        agent,
        harness_dir,
        agent_name="researcher",
    )
    agent.run(messages=[user])
    assert hook.last_trace_path is not None

    merged = merge_traces_into_datasets(
        hook.last_trace_path,
        valset_path=valset,
        train_path=train,
        expected_output="cite the failing stage",
    )
    assert merged.val_appended == 1
    assert merged.train_appended == 1

    gold = {
        "What is ZaumZeug?": "harness",
        "What broke in production?": "cite the failing stage",
    }

    def _runner(user_input: str) -> str:
        return gold.get(user_input, "")

    eval_result = run_eval(
        "example",
        project_root=tmp_path,
        framework="builtin",
        agent_runner=_runner,
    )
    assert eval_result.exit_code == 0
    assert eval_result.passed == 2
    assert eval_result.failed == 0

    compile_result = run_compile(
        "example",
        project_root=tmp_path,
        gepa_cls=StubGEPA,
        stub_gepa=True,
    )
    assert compile_result.exit_code == 0
    assert compile_result.agents[0].gepa_invoked is True
    assert compile_result.agents[0].artifact_dir is not None
    assert compile_result.agents[0].artifact_dir.is_dir()

    deploy_result = package_harness(
        "example",
        project_root=tmp_path,
        run_doctor_fn=_ok_doctor,
        output=io.StringIO(),
    )
    assert deploy_result.packaged is True
    assert deploy_result.bundle_dir is not None
    assert (deploy_result.bundle_dir / "harness.yaml").is_file()
    assert (deploy_result.bundle_dir / "manifest.json").is_file()
    # data/ is never copied to the production bundle
    assert not (deploy_result.bundle_dir / "data").exists()
