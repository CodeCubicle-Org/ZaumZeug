# Story: E4-S02b / E4.2
"""E4-S02b — GEPA runner integration (stub GEPA, artifacts, optional rewrite)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from zaumzeug.compile.gepa_runner import StubGEPA
from zaumzeug.compile.runner import run_compile


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _write_module(agent_dir: Path, *, relative: str, source: str) -> Path:
    path = agent_dir.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    package_root = path.parent
    while package_root != agent_dir and not (package_root / "__init__.py").exists():
        (package_root / "__init__.py").write_text("", encoding="utf-8")
        package_root = package_root.parent
    path.write_text(source, encoding="utf-8")
    return path


def _purge_import(module_name: str) -> None:
    prefix = module_name + "."
    for key in list(sys.modules):
        if key == module_name or key.startswith(prefix):
            del sys.modules[key]


def _scaffold_compile_harness(
    project_root: Path,
    *,
    module_source: str,
    module_ref: str = "modules.researcher:ResearchModule",
    compile_extra: dict | None = None,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"
    compile_block = {
        "module": module_ref,
        "task_model_id": "mock",
        "reflection_model_id": "mock",
        "auto": "light",
        **(compile_extra or {}),
    }
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"system_prompt": "prompts/system.md"},
            "compile": compile_block,
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
    _write_module(agent_dir, relative="modules/researcher.py", source=module_source)
    train = agent_dir / "data" / "train.jsonl"
    train.parent.mkdir(parents=True, exist_ok=True)
    train.write_text(
        '{"question": "What is ZaumZeug?", "answer": "harness"}\n',
        encoding="utf-8",
    )
    return harness_dir


_PLAIN_MODULE = '''\
import dspy

class ResearchModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.respond = dspy.Predict("question -> answer")

    def forward(self, question: str):
        return dspy.Prediction(answer="harness")
'''

_REWRITE_MODULE = '''\
import dspy

class ResearchModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.input_rewrite = dspy.Predict("text -> rewritten")
        self.respond = dspy.Predict("question -> answer")

    def forward(self, question: str):
        return dspy.Prediction(answer="harness")
'''


def test_e4_s02_ac1_invokes_dspy_gepa(tmp_path: Path) -> None:
    """AC-1: ``zaumzeug compile`` runs GEPA per compile section (stub OK in CI)."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    _scaffold_compile_harness(tmp_path, module_source=_PLAIN_MODULE)

    calls: list[dict] = []

    class SpyGEPA(StubGEPA):
        def __init__(self, metric, **kwargs):  # noqa: ANN001
            calls.append({"metric": metric, **kwargs})
            super().__init__(metric, **kwargs)

    result = run_compile(
        "example",
        project_root=tmp_path,
        gepa_cls=SpyGEPA,
        stub_gepa=True,
    )

    assert len(result.agents) == 1
    agent = result.agents[0]
    assert agent.gepa_invoked is True
    assert len(calls) == 1
    assert callable(calls[0]["metric"])
    assert calls[0].get("auto") == "light"


def test_e4_s02_ac2_writes_run_id_and_current(tmp_path: Path) -> None:
    """AC-2: Writes ``artifacts/<run_id>/`` and updates ``artifacts/current``."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    harness_dir = _scaffold_compile_harness(tmp_path, module_source=_PLAIN_MODULE)
    agent_dir = harness_dir / "agents" / "researcher"

    result = run_compile(
        "example",
        project_root=tmp_path,
        gepa_cls=StubGEPA,
        stub_gepa=True,
    )

    agent = result.agents[0]
    assert agent.run_id is not None
    run_dir = agent_dir / "artifacts" / agent.run_id
    current = agent_dir / "artifacts" / "current"
    assert run_dir.is_dir()
    assert (run_dir / "gepa-run.json").is_file()
    assert current.exists()

    meta = json.loads((run_dir / "gepa-run.json").read_text(encoding="utf-8"))
    assert meta["run_id"] == agent.run_id
    assert meta["stubbed"] is True

    if current.is_symlink():
        assert current.resolve() == run_dir.resolve()
    else:
        assert (current / "gepa-run.json").is_file()
        cur_meta = json.loads((current / "gepa-run.json").read_text(encoding="utf-8"))
        assert cur_meta["run_id"] == agent.run_id


def test_e4_s02_ac4_optional_input_rewrite_in_run(tmp_path: Path) -> None:
    """AC-4: Optional clarify/rewrite signature is included in the same GEPA run."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    harness_dir = _scaffold_compile_harness(tmp_path, module_source=_REWRITE_MODULE)
    agent_dir = harness_dir / "agents" / "researcher"

    result = run_compile(
        "example",
        project_root=tmp_path,
        gepa_cls=StubGEPA,
        stub_gepa=True,
    )

    agent = result.agents[0]
    assert agent.gepa_result is not None
    assert agent.gepa_result.has_input_rewrite is True

    meta = json.loads(
        (agent_dir / "artifacts" / agent.run_id / "gepa-run.json").read_text(
            encoding="utf-8"
        )
    )
    assert meta["has_input_rewrite"] is True


def test_e4_s02_example_harness_compile_seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """DoD: example harness compile seed works offline via stub GEPA (mock models)."""
    repo = Path(__file__).resolve().parents[3]
    example = repo / "usr-harnesses" / "example"
    assert (example / "agents" / "researcher" / "modules" / "researcher.py").is_file()

    # Copy example into tmp so we do not pollute the working tree with artifacts.
    import shutil

    dest = tmp_path / "usr-harnesses" / "example"
    shutil.copytree(example, dest)

    _purge_import("modules")
    _purge_import("modules.researcher")

    result = run_compile(
        "example",
        project_root=tmp_path,
        stub_gepa=True,
    )
    assert result.exit_code == 0
    assert result.agents[0].gepa_invoked is True
    assert result.agents[0].run_id is not None
    assert (dest / "agents" / "researcher" / "artifacts" / result.agents[0].run_id).is_dir()
