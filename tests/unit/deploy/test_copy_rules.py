# Story: E5-S02 / E5.2 (shared E6-S04 / E6.4; stubs E7-S02 / E8-S01)
"""E5-S02 — Dev vs deploy copy rules (Architecture §10.1).

Covers exclude policy, reference resolver, required-path failures, strip helpers,
and packager include/pin behaviour. Shared early ``eval/`` exclusion supports
E6-S04. Custom-tool / exposed-pipeline rows are shared with E7-S02 / E8-S01.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from zaumzeug.config.resolver import ARTIFACT_MANIFEST
from zaumzeug.config.schemas import HarnessConfig
from zaumzeug.deploy.copy_rules import (
    DEV_ONLY_AGENT_DIRS,
    DEV_ONLY_TOP_LEVEL_DIRS,
    STRIPPED_AGENT_KEYS,
    STRIPPED_HARNESS_KEYS,
    CopyRulesError,
    assert_required_paths,
    is_excluded_from_deploy,
    resolve_deploy_copy_plan,
    strip_agent_yaml,
    strip_harness_yaml,
)
from zaumzeug.deploy.packager import DeployError, write_deploy_bundle


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _seed_matrix_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    with_artifact: bool = True,
    with_tools_hooks: bool = True,
    with_pipeline: bool = False,
    run_id: str = "20260728T120000Z",
    omit_prompt: bool = False,
    omit_agents_models: bool = False,
    omit_diagram: bool = False,
) -> Path:
    """Harness exercising Architecture §10.1 include + exclude matrix."""
    harness_dir = project_root / "usr-harnesses" / harness_name
    harness_body: dict = {
        "name": harness_name,
        "description": "Copy-rules matrix harness",
        "models": "models.yaml",
        "serve": {"hayhooks": {"port": 1416}},
        "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
        "deploy": {"eval_gate": "skip"},
    }
    if with_pipeline:
        harness_body["serve"]["expose"] = ["summarize"]
    _write_yaml(harness_dir / "harness.yaml", harness_body)
    _write_yaml(
        harness_dir / "models.yaml",
        {"models": {"shared-mock": {"provider": "mock", "model": "harness-shared"}}},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    if not omit_diagram:
        diagram = harness_dir / "docs" / "workflow-diagram.md"
        diagram.parent.mkdir(parents=True, exist_ok=True)
        diagram.write_text(
            "# Workflow diagram — example\n\n```mermaid\nflowchart LR\n  s0[researcher]\n```\n",
            encoding="utf-8",
        )

    # Dev-only top-level (must never copy).
    (harness_dir / "data").mkdir(parents=True, exist_ok=True)
    (harness_dir / "data" / "val.jsonl").write_text("{}\n", encoding="utf-8")
    (harness_dir / "eval").mkdir(parents=True, exist_ok=True)
    (harness_dir / "eval" / "metrics.py").write_text("# eval only\n", encoding="utf-8")

    if with_pipeline:
        _write_yaml(
            harness_dir / "pipelines" / "summarize.yaml",
            {"name": "summarize", "components": {}},
        )

    agent_dir = harness_dir / "agents" / "researcher"
    agent_yaml: dict = {
        "name": "researcher",
        "default_model_id": "mock",
        "compile": {
            "module": "modules.researcher:ResearchModule",
            "task_model_id": "mock",
            "reflection_model_id": "mock",
            "trainset": "data/train.jsonl",
            "valset": "data/val.jsonl",
            "auto": "light",
        },
    }
    if with_artifact:
        agent_yaml["agent"] = {"artifact": f"artifacts/{run_id}"}
    else:
        agent_yaml["agent"] = {"system_prompt": "prompts/system.md"}
    if with_tools_hooks:
        agent_yaml["tools"] = {
            "builtin": ["web_fetch"],
            "custom": ["tools/search_docs.py"],
        }
        agent_yaml["hooks"] = {"enabled": True}

    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    if not omit_agents_models:
        _write_yaml(
            agent_dir / "agents-models.yaml",
            {
                "default_model_id": "mock",
                "models": {"mock": {"provider": "mock", "model": "harness-fixture"}},
            },
        )

    if not omit_prompt:
        prompt = agent_dir / "prompts" / "system.md"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text("You are a researcher.\n", encoding="utf-8")

    # Dev-only agent paths.
    (agent_dir / "modules" / "researcher.py").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / "modules" / "researcher.py").write_text("# DSPy\n", encoding="utf-8")
    (agent_dir / "skills" / "recon.md").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / "skills" / "recon.md").write_text("# skill\n", encoding="utf-8")
    (agent_dir / "data" / "train.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / "data" / "train.jsonl").write_text("{}\n", encoding="utf-8")

    if with_tools_hooks:
        tool = agent_dir / "tools" / "search_docs.py"
        tool.parent.mkdir(parents=True, exist_ok=True)
        tool.write_text("def search_docs(query: str) -> str:\n    return query\n", encoding="utf-8")
        (agent_dir / "hooks.py").write_text("# hooks\n", encoding="utf-8")

    if with_artifact:
        artifact_dir = agent_dir / "artifacts" / run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "prompts").mkdir(parents=True, exist_ok=True)
        (artifact_dir / "prompts" / "system.md").write_text(
            "Optimized researcher prompt.\n",
            encoding="utf-8",
        )
        (artifact_dir / ARTIFACT_MANIFEST).write_text(
            json.dumps(
                {
                    "export_version": 1,
                    "run_id": run_id,
                    "paths": {"system_prompt": "prompts/system.md"},
                }
            )
            + "\n",
            encoding="utf-8",
        )

    return harness_dir


def _harness_config(name: str = "example") -> HarnessConfig:
    """Minimal config object — packager re-reads raw yaml and ignores this."""
    return HarnessConfig(name=name, models="models.yaml")


def test_e5_s02_excludes_eval() -> None:
    """AC (E6-S04 AC-3 / E5-S02): ``eval/`` is excluded from the deploy bundle."""
    assert "eval" in DEV_ONLY_TOP_LEVEL_DIRS
    assert is_excluded_from_deploy("eval") is True
    assert is_excluded_from_deploy("eval/metrics.py") is True
    assert is_excluded_from_deploy("eval/test_researcher.py") is True
    assert is_excluded_from_deploy(r"eval\test_smoke.py") is True
    assert is_excluded_from_deploy("harness.yaml") is False
    assert is_excluded_from_deploy("workflow.yaml") is False
    assert is_excluded_from_deploy("agents/researcher/agent.yaml") is False


def test_e5_s02_ac1_excludes_dev_only_dirs() -> None:
    """AC-1: modules/, data/, eval/, skills/ are always excluded from deploy."""
    assert DEV_ONLY_TOP_LEVEL_DIRS == frozenset({"data", "eval"})
    assert DEV_ONLY_AGENT_DIRS == frozenset({"modules", "skills", "data"})

    excluded = [
        "data/",
        "data/val.jsonl",
        "eval/",
        "eval/metrics.py",
        "agents/researcher/modules/",
        "agents/researcher/modules/researcher.py",
        "agents/researcher/skills/",
        "agents/researcher/skills/recon.md",
        "agents/researcher/data/train.jsonl",
        r"agents\researcher\modules\researcher.py",
    ]
    for path in excluded:
        assert is_excluded_from_deploy(path) is True, path

    allowed = [
        "harness.yaml",
        "workflow.yaml",
        "docs/workflow-diagram.md",
        "agents/researcher/prompts/system.md",
        "agents/researcher/tools/search_docs.py",
        "agents/researcher/hooks.py",
        "agents/researcher/agents-models.yaml",
        "agents/researcher/artifacts/20260728T120000Z/prompts/system.md",
        "pipelines/summarize.yaml",
    ]
    for path in allowed:
        assert is_excluded_from_deploy(path) is False, path


@pytest.mark.parametrize(
    "path",
    [
        "data/val.jsonl",
        "agents/researcher/modules/researcher.py",
        "agents/researcher/skills/recon.md",
        "agents/researcher/data/train.jsonl",
    ],
)
def test_e5_s02_excludes_other_dev_only_paths(path: str) -> None:
    """Smoke: other Architecture §10.1 dev-only paths are also marked excluded."""
    assert is_excluded_from_deploy(path) is True


def test_e5_s02_ac2_includes_referenced_runtime_assets(tmp_path: Path) -> None:
    """AC-2: prompts/, tools/, hooks.py, agents-models.yaml follow §10.1 refs."""
    harness_dir = _seed_matrix_harness(
        tmp_path,
        with_artifact=False,
        with_tools_hooks=True,
    )
    agent_data = yaml.safe_load(
        (harness_dir / "agents" / "researcher" / "agent.yaml").read_text(encoding="utf-8")
    )
    harness_raw = yaml.safe_load((harness_dir / "harness.yaml").read_text(encoding="utf-8"))
    plan = resolve_deploy_copy_plan(
        harness_raw=harness_raw,
        agents={"researcher": agent_data},
    )
    paths = set(plan.paths())
    assert "agents/researcher/agents-models.yaml" in paths
    assert "agents/researcher/prompts/system.md" in paths
    assert "agents/researcher/tools/search_docs.py" in paths
    assert "agents/researcher/hooks.py" in paths
    assert plan.of_kind("prompt")
    assert plan.of_kind("tool")
    assert plan.of_kind("hooks")

    bundle = write_deploy_bundle(
        "example",
        project_root=tmp_path,
        harness_dir=harness_dir,
        harness_config=_harness_config(),
    )
    assert (bundle / "agents" / "researcher" / "agents-models.yaml").is_file()
    assert (bundle / "agents" / "researcher" / "prompts" / "system.md").is_file()
    assert (bundle / "agents" / "researcher" / "tools" / "search_docs.py").is_file()
    assert (bundle / "agents" / "researcher" / "hooks.py").is_file()
    # Dev-only must not leak.
    assert not (bundle / "eval").exists()
    assert not (bundle / "data").exists()
    assert not (bundle / "agents" / "researcher" / "modules").exists()
    assert not (bundle / "agents" / "researcher" / "skills").exists()


def test_e5_s02_ac3_pins_per_agent_artifact_runs(tmp_path: Path) -> None:
    """AC-3: pinned artifact run lands under deploy/.../agents/<name>/artifacts/."""
    run_id = "20260728T120000Z"
    harness_dir = _seed_matrix_harness(
        tmp_path,
        with_artifact=True,
        with_tools_hooks=False,
        run_id=run_id,
    )
    agent_data = yaml.safe_load(
        (harness_dir / "agents" / "researcher" / "agent.yaml").read_text(encoding="utf-8")
    )
    plan = resolve_deploy_copy_plan(
        harness_raw={},
        agents={"researcher": agent_data},
    )
    pins = plan.of_kind("artifact_pin")
    assert len(pins) == 1
    assert pins[0].relative_path == f"agents/researcher/artifacts/{run_id}"

    bundle = write_deploy_bundle(
        "example",
        project_root=tmp_path,
        harness_dir=harness_dir,
        harness_config=_harness_config(),
    )
    pinned = bundle / "agents" / "researcher" / "artifacts" / run_id
    assert (pinned / ARTIFACT_MANIFEST).is_file()
    assert (pinned / "prompts" / "system.md").is_file()
    agent_out = yaml.safe_load(
        (bundle / "agents" / "researcher" / "agent.yaml").read_text(encoding="utf-8")
    )
    assert agent_out["agent"]["artifact"] == f"artifacts/{run_id}"
    # system_prompt-only copy is skipped when artifact is pinned.
    assert not (bundle / "agents" / "researcher" / "prompts").exists()


def test_e5_s02_ac4_includes_workflow_and_diagram(tmp_path: Path) -> None:
    """AC-4: workflow.yaml and docs/workflow-diagram.md are always included."""
    harness_dir = _seed_matrix_harness(tmp_path, with_tools_hooks=False)
    harness_raw = yaml.safe_load((harness_dir / "harness.yaml").read_text(encoding="utf-8"))
    agent_data = yaml.safe_load(
        (harness_dir / "agents" / "researcher" / "agent.yaml").read_text(encoding="utf-8")
    )
    plan = resolve_deploy_copy_plan(
        harness_raw=harness_raw,
        agents={"researcher": agent_data},
    )
    assert "workflow.yaml" in plan.paths()
    assert "docs/workflow-diagram.md" in plan.paths()
    assert plan.of_kind("workflow")
    assert plan.of_kind("diagram")

    bundle = write_deploy_bundle(
        "example",
        project_root=tmp_path,
        harness_dir=harness_dir,
        harness_config=_harness_config(),
    )
    assert (bundle / "workflow.yaml").is_file()
    assert (bundle / "docs" / "workflow-diagram.md").is_file()


def test_e5_s02_ac5_stripped_yaml_sections() -> None:
    """AC-5: stripped yaml removes compile / eval / deploy (and agent compile)."""
    assert STRIPPED_HARNESS_KEYS == frozenset({"compile", "eval", "deploy"})
    assert STRIPPED_AGENT_KEYS == frozenset({"compile"})

    harness = {
        "name": "example",
        "serve": {"hayhooks": {"port": 1416}},
        "compile": {"x": 1},
        "eval": {"framework": "builtin"},
        "deploy": {"eval_gate": "skip"},
    }
    stripped_h = strip_harness_yaml(harness)
    assert "compile" not in stripped_h
    assert "eval" not in stripped_h
    assert "deploy" not in stripped_h
    assert stripped_h["name"] == "example"
    assert stripped_h["serve"]["hayhooks"]["port"] == 1416

    agent = {
        "name": "researcher",
        "agent": {"system_prompt": "prompts/system.md"},
        "compile": {"module": "modules.x:Y", "auto": "light"},
    }
    stripped_a = strip_agent_yaml(agent)
    assert "compile" not in stripped_a
    assert stripped_a["agent"]["system_prompt"] == "prompts/system.md"


def test_e5_s02_fails_when_required_runtime_path_missing(tmp_path: Path) -> None:
    """Implementation task: fail deploy when a required runtime path is missing."""
    harness_dir = _seed_matrix_harness(
        tmp_path,
        with_artifact=False,
        with_tools_hooks=False,
        omit_diagram=True,
    )
    harness_raw = yaml.safe_load((harness_dir / "harness.yaml").read_text(encoding="utf-8"))
    agent_data = yaml.safe_load(
        (harness_dir / "agents" / "researcher" / "agent.yaml").read_text(encoding="utf-8")
    )
    plan = resolve_deploy_copy_plan(
        harness_raw=harness_raw,
        agents={"researcher": agent_data},
    )
    with pytest.raises(CopyRulesError, match="workflow-diagram"):
        assert_required_paths(harness_dir, plan)

    with pytest.raises(DeployError, match="workflow-diagram|missing path"):
        write_deploy_bundle(
            "example",
            project_root=tmp_path,
            harness_dir=harness_dir,
            harness_config=_harness_config(),
        )
    assert not (tmp_path / "deploy" / "example").exists()


def test_e5_s02_fails_when_agents_models_missing(tmp_path: Path) -> None:
    """agents-models.yaml is always required per agent."""
    harness_dir = _seed_matrix_harness(
        tmp_path,
        with_artifact=False,
        with_tools_hooks=False,
        omit_agents_models=True,
    )
    with pytest.raises(DeployError, match="agents-models"):
        write_deploy_bundle(
            "example",
            project_root=tmp_path,
            harness_dir=harness_dir,
            harness_config=_harness_config(),
        )


def test_e7_s02_ac4_custom_tools_in_deploy(tmp_path: Path) -> None:
    """Shared E7-S02 AC-4: custom tools listed in yaml are copied to deploy."""
    harness_dir = _seed_matrix_harness(
        tmp_path,
        with_artifact=False,
        with_tools_hooks=True,
    )
    bundle = write_deploy_bundle(
        "example",
        project_root=tmp_path,
        harness_dir=harness_dir,
        harness_config=_harness_config(),
    )
    assert (bundle / "agents" / "researcher" / "tools" / "search_docs.py").is_file()


def test_e8_s01_ac3_exposed_pipelines_in_deploy(tmp_path: Path) -> None:
    """Shared E8-S01 AC-3: pipelines listed in serve.expose are copied.

    Packager accepts string ids and ``{id, path}`` maps (schema unblocked E8-S01).
    """
    harness_dir = _seed_matrix_harness(
        tmp_path,
        with_artifact=False,
        with_tools_hooks=False,
        with_pipeline=True,
    )
    harness_raw = yaml.safe_load((harness_dir / "harness.yaml").read_text(encoding="utf-8"))
    agent_data = yaml.safe_load(
        (harness_dir / "agents" / "researcher" / "agent.yaml").read_text(encoding="utf-8")
    )
    plan = resolve_deploy_copy_plan(
        harness_raw=harness_raw,
        agents={"researcher": agent_data},
    )
    assert any(e.kind == "pipeline" for e in plan.entries)

    bundle = write_deploy_bundle(
        "example",
        project_root=tmp_path,
        harness_dir=harness_dir,
        harness_config=_harness_config(),
    )
    assert (bundle / "pipelines" / "summarize.yaml").is_file()
