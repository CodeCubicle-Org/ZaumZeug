# Story: E4-S06 / E4.6
"""E4-S06 — `zaumzeug compile --dry-run` (integration)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from zaumzeug.cli import _compile_command, build_parser
from zaumzeug.compile.runner import CompileError, format_compile_dry_run, run_compile
from zaumzeug.config import load_harness, resolve_agent_compile


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


_PLAIN_MODULE = '''\
import dspy

class ResearchModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.respond = dspy.Predict("question -> answer")

    def forward(self, question: str):
        return dspy.Prediction(answer="harness")
'''


def _scaffold_compile_harness(
    project_root: Path,
    *,
    module_source: str = _PLAIN_MODULE,
    module_ref: str = "modules.researcher:ResearchModule",
    compile_extra: dict | None = None,
    agent_yaml: dict | None = None,
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
        agent_yaml
        or {
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


def test_e4_s06_ac1_validates_phase2_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: dry-run validates harness + Phase 2 compile schema (same path as compile)."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    harness_dir = _scaffold_compile_harness(tmp_path)
    monkeypatch.setattr(
        "zaumzeug.compile.runner.find_project_root",
        lambda start=None: tmp_path,
    )

    load_calls: list[Path] = []
    resolve_calls: list[str] = []
    original_load = load_harness
    original_resolve = resolve_agent_compile

    def tracking_load(path: Path | str):
        load_calls.append(Path(path))
        return original_load(path)

    def tracking_resolve(harness_path: Path | str, *, harness_name: str, agent_name: str):
        resolve_calls.append(agent_name)
        return original_resolve(
            harness_path,
            harness_name=harness_name,
            agent_name=agent_name,
        )

    monkeypatch.setattr("zaumzeug.compile.runner.load_harness", tracking_load)
    monkeypatch.setattr(
        "zaumzeug.compile.runner.resolve_agent_compile",
        tracking_resolve,
    )

    result = run_compile("example", project_root=tmp_path, dry_run=True)

    assert result.exit_code == 0
    assert load_calls == [harness_dir / "harness.yaml"]
    assert "researcher" in resolve_calls
    assert len(result.agents) == 1
    assert result.agents[0].module_ref == "modules.researcher:ResearchModule"

    # Invalid Phase 2 compile block must fail dry-run (schema path).
    bad_root = tmp_path / "bad"
    _scaffold_compile_harness(
        bad_root,
        agent_yaml={
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"system_prompt": "prompts/system.md"},
            "compile": {
                # missing required `module`
                "task_model_id": "mock",
                "auto": "light",
            },
        },
    )
    # Still need a modules file so failure is schema, not import.
    agent_dir = bad_root / "usr-harnesses" / "example" / "agents" / "researcher"
    _write_module(agent_dir, relative="modules/researcher.py", source=_PLAIN_MODULE)
    _purge_import("modules")
    _purge_import("modules.researcher")

    with pytest.raises(CompileError) as exc_info:
        run_compile(
            "example",
            agent_name="researcher",
            project_root=bad_root,
            dry_run=True,
        )
    assert "compile.module" in str(exc_info.value)


def test_e4_s06_ac2_resolves_module_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: dry-run successfully imports ``compile.module``."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    _scaffold_compile_harness(tmp_path)
    monkeypatch.setattr(
        "zaumzeug.compile.runner.find_project_root",
        lambda start=None: tmp_path,
    )

    result = run_compile("example", project_root=tmp_path, dry_run=True)

    assert len(result.agents) == 1
    agent = result.agents[0]
    assert agent.module_ref == "modules.researcher:ResearchModule"
    assert agent.module_instance is not None
    assert agent.module_instance.__class__.__name__ == "ResearchModule"
    assert agent.gepa_invoked is False


def test_e4_s06_ac3_prints_model_registry(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: dry-run prints resolved task/reflection model registry."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    _scaffold_compile_harness(tmp_path)
    monkeypatch.setattr(
        "zaumzeug.compile.runner.find_project_root",
        lambda start=None: tmp_path,
    )

    parser = build_parser()
    args = parser.parse_args(["compile", "example", "--dry-run", "--agent", "researcher"])
    code = _compile_command(args)
    captured = capsys.readouterr()

    assert code == 0
    output = captured.out
    assert "Compile dry-run: example" in output
    assert "task=mock" in output
    assert "reflection=mock" in output
    assert "mock/harness-fixture" in output
    assert "gepa: skipped" in output
    assert "status: ok" in output

    # Formatter covers the structured summary independently of CLI wiring.
    result = run_compile(
        "example",
        agent_name="researcher",
        project_root=tmp_path,
        dry_run=True,
    )
    summary = format_compile_dry_run(result)
    assert "task=mock (mock/harness-fixture)" in summary
    assert "reflection=mock (mock/harness-fixture)" in summary


def test_e4_s06_ac4_no_gepa_no_llm_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: dry-run does not invoke GEPA or make LLM API calls."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    _scaffold_compile_harness(tmp_path)
    monkeypatch.setattr(
        "zaumzeug.compile.runner.find_project_root",
        lambda start=None: tmp_path,
    )

    invoke_mock = MagicMock(side_effect=AssertionError("invoke_gepa must not be called"))
    monkeypatch.setattr("zaumzeug.compile.runner.invoke_gepa", invoke_mock)

    llm_mock = MagicMock(side_effect=AssertionError("litellm must not be called"))
    fake_litellm = MagicMock()
    fake_litellm.completion = llm_mock
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)

    result = run_compile("example", project_root=tmp_path, dry_run=True)

    assert result.exit_code == 0
    assert all(not agent.gepa_invoked for agent in result.agents)
    assert all(agent.artifact_dir is None for agent in result.agents)
    assert all(agent.run_id is None for agent in result.agents)
    invoke_mock.assert_not_called()
    llm_mock.assert_not_called()

    # No artifacts written under the agent folder.
    artifacts = (
        tmp_path
        / "usr-harnesses"
        / "example"
        / "agents"
        / "researcher"
        / "artifacts"
    )
    assert not artifacts.exists()


def test_e4_s06_ac5_exit_zero_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-5: exit 0 when dry-run validation succeeds."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    _scaffold_compile_harness(tmp_path)
    monkeypatch.setattr(
        "zaumzeug.compile.runner.find_project_root",
        lambda start=None: tmp_path,
    )

    result = run_compile("example", project_root=tmp_path, dry_run=True)
    assert result.exit_code == 0

    parser = build_parser()
    args = parser.parse_args(["compile", "example", "--dry-run"])
    assert _compile_command(args) == 0
