# Story: E4-S07
"""E4-S07 — Rollback to pinned artifact run (immutable ``<run_id>/``)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from zaumzeug.compile.export import find_artifact_manifest
from zaumzeug.compile.gepa_runner import GepaRunError, StubGEPA, write_artifact_run
from zaumzeug.compile.runner import run_compile
from zaumzeug.config.resolver import RuntimeSource, resolve_agent_serve


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


_PLAIN_MODULE = """\
import dspy


class ResearchModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.answer = dspy.Predict("question -> answer")

    def forward(self, question: str):
        return self.answer(question=question)
"""


def _scaffold_compile_harness(project_root: Path) -> Path:
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
    _write_module(agent_dir, relative="modules/researcher.py", source=_PLAIN_MODULE)
    return harness_dir


def test_e4_s07_ac4_compile_twice_pin_first_serve_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: Second compile leaves first ``<run_id>/`` intact; pin serves first run."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    harness_dir = _scaffold_compile_harness(tmp_path)
    agent_dir = harness_dir / "agents" / "researcher"

    run_ids = iter(["20260728T100001Z", "20260728T100002Z"])
    monkeypatch.setattr(
        "zaumzeug.compile.gepa_runner.generate_run_id",
        lambda **_kwargs: next(run_ids),
    )

    first = run_compile(
        "example",
        project_root=tmp_path,
        gepa_cls=StubGEPA,
        stub_gepa=True,
    )
    first_run = first.agents[0].run_id
    assert first_run == "20260728T100001Z"
    first_dir = agent_dir / "artifacts" / first_run
    assert first_dir.is_dir()
    marker = first_dir / "gepa-run.json"
    original = marker.read_text(encoding="utf-8")
    first_manifest = find_artifact_manifest(first_dir)
    assert first_manifest is not None

    second = run_compile(
        "example",
        project_root=tmp_path,
        gepa_cls=StubGEPA,
        stub_gepa=True,
    )
    second_run = second.agents[0].run_id
    assert second_run == "20260728T100002Z"
    second_dir = agent_dir / "artifacts" / second_run
    assert second_dir.is_dir()
    assert first_dir.is_dir()
    assert marker.read_text(encoding="utf-8") == original
    assert find_artifact_manifest(first_dir) is not None

    # Re-using the same run_id must fail (immutable).
    with pytest.raises(GepaRunError, match="immutable"):
        write_artifact_run(
            agent_dir,
            run_id=first_run,
            payload={"run_id": first_run, "probe": True},
        )

    # Pin serve path to the first run while current advanced to the second.
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"artifact": f"artifacts/{first_run}"},
            "compile": {
                "module": "modules.researcher:ResearchModule",
                "task_model_id": "mock",
                "reflection_model_id": "mock",
                "auto": "light",
            },
        },
    )
    resolution = resolve_agent_serve(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
    )
    assert resolution.source is RuntimeSource.ARTIFACT
    assert resolution.path.resolve() == first_dir.resolve()
    assert json.loads(original)["run_id"] == first_run
