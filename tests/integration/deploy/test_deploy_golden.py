# Story: E5-S02 / E5.2 · E5-S08 / E5.8
"""E5-S02 — Golden deploy bundle snapshot for Architecture §10.1 copy matrix.

E5-S08 — OS-neutral production bundle assertions (Architecture §10.6).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from zaumzeug.config.resolver import ARTIFACT_MANIFEST
from zaumzeug.config.schemas import HarnessConfig
from zaumzeug.deploy.packager import write_deploy_bundle

_GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
_GOLDEN_PATHS = _GOLDEN_DIR / "example_bundle_paths.json"


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _seed_golden_example(
    project_root: Path,
    *,
    run_id: str = "20260728T120000Z",
) -> Path:
    """Example-shaped harness with full include/exclude matrix for golden compare."""
    harness_name = "example"
    harness_dir = project_root / "usr-harnesses" / harness_name
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": harness_name,
            "description": "Golden deploy matrix harness",
            "models": "models.yaml",
            "serve": {
                "hayhooks": {"port": 1416},
                "expose": ["summarize"],
            },
            "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
            "deploy": {"eval_gate": "skip"},
        },
    )
    _write_yaml(
        harness_dir / "models.yaml",
        {"models": {"shared-mock": {"provider": "mock", "model": "harness-shared"}}},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    diagram = harness_dir / "docs" / "workflow-diagram.md"
    diagram.parent.mkdir(parents=True, exist_ok=True)
    diagram.write_text(
        "# Workflow diagram — example\n\n```mermaid\nflowchart LR\n  s0[researcher]\n```\n",
        encoding="utf-8",
    )
    _write_yaml(
        harness_dir / "pipelines" / "summarize.yaml",
        {"name": "summarize", "components": {}},
    )

    (harness_dir / "data").mkdir(parents=True, exist_ok=True)
    (harness_dir / "data" / "val.jsonl").write_text("{}\n", encoding="utf-8")
    (harness_dir / "eval").mkdir(parents=True, exist_ok=True)
    (harness_dir / "eval" / "metrics.py").write_text("# eval\n", encoding="utf-8")

    agent_dir = harness_dir / "agents" / "researcher"
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"artifact": f"artifacts/{run_id}"},
            "tools": {
                "builtin": ["web_fetch"],
                "custom": ["tools/search_docs.py"],
            },
            "hooks": {"enabled": True},
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
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {"mock": {"provider": "mock", "model": "harness-fixture"}},
        },
    )
    prompt = agent_dir / "prompts" / "system.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("You are a researcher.\n", encoding="utf-8")
    (agent_dir / "modules" / "researcher.py").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / "modules" / "researcher.py").write_text("# DSPy\n", encoding="utf-8")
    (agent_dir / "skills" / "recon.md").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / "skills" / "recon.md").write_text("# skill\n", encoding="utf-8")
    (agent_dir / "data" / "train.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / "data" / "train.jsonl").write_text("{}\n", encoding="utf-8")
    tool = agent_dir / "tools" / "search_docs.py"
    tool.parent.mkdir(parents=True, exist_ok=True)
    tool.write_text("def search_docs(query: str) -> str:\n    return query\n", encoding="utf-8")
    (agent_dir / "hooks.py").write_text("# hooks\n", encoding="utf-8")

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


def _bundle_relative_paths(bundle: Path) -> list[str]:
    """Sorted posix-relative file paths under the deploy bundle."""
    paths: list[str] = []
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            paths.append(path.relative_to(bundle).as_posix())
    return paths


def _stable_bundle_paths(paths: list[str]) -> list[str]:
    """Drop volatile generated files that are not part of the §10.1 matrix."""
    skip_names = {
        "manifest.json",
        "README.deploy.md",
        "target_install.py",
        "target-install.sh",
        "target-install.ps1",
        "models.yaml",  # merged registry; content varies with global config/
    }
    return [p for p in paths if p not in skip_names and not p.startswith("models.")]


# Canonical §10.1 matrix paths for the golden example harness (E5-S02).
_EXPECTED_MATRIX_PATHS = [
    "agents/researcher/agent.yaml",
    "agents/researcher/agents-models.yaml",
    "agents/researcher/artifacts/20260728T120000Z/artifact-manifest.json",
    "agents/researcher/artifacts/20260728T120000Z/prompts/system.md",
    "agents/researcher/hooks.py",
    "agents/researcher/tools/search_docs.py",
    "docs/workflow-diagram.md",
    "harness.yaml",
    "pipelines/summarize.yaml",
    "workflow.yaml",
]


def test_e5_s02_golden_example_bundle(tmp_path: Path) -> None:
    """AC-1–5 golden: example deploy contents match Architecture §10.1 matrix."""
    run_id = "20260728T120000Z"
    harness_dir = _seed_golden_example(tmp_path, run_id=run_id)
    config = HarnessConfig(name="example", models="models.yaml")
    bundle = write_deploy_bundle(
        "example",
        project_root=tmp_path,
        harness_dir=harness_dir,
        harness_config=config,
    )

    actual = _stable_bundle_paths(_bundle_relative_paths(bundle))
    expected = list(_EXPECTED_MATRIX_PATHS)
    # Persist golden for review / future syrupy-style diffs.
    _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    _GOLDEN_PATHS.write_text(
        json.dumps(expected, indent=2) + "\n",
        encoding="utf-8",
    )
    on_disk = json.loads(_GOLDEN_PATHS.read_text(encoding="utf-8"))
    assert actual == on_disk == expected

    # Explicit exclude assertions (AC-1).
    for forbidden in (
        "eval",
        "data",
        "agents/researcher/modules",
        "agents/researcher/skills",
        "agents/researcher/data",
        "agents/researcher/prompts/system.md",  # artifact pin skips loose prompts/
    ):
        assert not (bundle / forbidden).exists(), forbidden

    harness_data = yaml.safe_load((bundle / "harness.yaml").read_text(encoding="utf-8"))
    assert "compile" not in harness_data
    assert "eval" not in harness_data
    assert "deploy" not in harness_data

    agent_data = yaml.safe_load(
        (bundle / "agents" / "researcher" / "agent.yaml").read_text(encoding="utf-8")
    )
    assert "compile" not in agent_data
    assert agent_data["agent"]["artifact"] == f"artifacts/{run_id}"


# Portable text/config/source suffixes expected in an OS-neutral bundle (E5-S08).
_OS_NEUTRAL_SUFFIXES = frozenset(
    {
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".py",
        ".ps1",
        ".sh",
        ".txt",
        ".jsonl",
        "",  # extensionless (rare)
    }
)
_NATIVE_BINARY_SUFFIXES = frozenset(
    {".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".whl", ".egg"}
)

_README_DEPLOY_TEMPLATE = (
    Path(__file__).resolve().parents[3]
    / "install"
    / "templates"
    / "deploy"
    / "README.deploy.md"
)
_SHIP_GUIDE = (
    Path(__file__).resolve().parents[3] / "user-docs" / "guides" / "deploy.md"
)


def test_e5_s08_ac2_os_neutral_bundle(tmp_path: Path) -> None:
    """AC-2: Bundle is OS-neutral Python + pinned artifacts (no native binaries)."""
    run_id = "20260728T120000Z"
    harness_dir = _seed_golden_example(tmp_path, run_id=run_id)
    config = HarnessConfig(name="example", models="models.yaml")
    bundle = write_deploy_bundle(
        "example",
        project_root=tmp_path,
        harness_dir=harness_dir,
        harness_config=config,
    )

    for path in bundle.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(bundle).as_posix()
        assert "\\" not in rel, f"bundle path must be portable: {rel}"
        suffix = path.suffix.lower()
        assert suffix not in _NATIVE_BINARY_SUFFIXES, (
            f"OS-native binary not allowed in deploy bundle: {rel}"
        )
        assert suffix in _OS_NEUTRAL_SUFFIXES, (
            f"unexpected non-portable file type in deploy bundle: {rel}"
        )

    pinned = (
        bundle
        / "agents"
        / "researcher"
        / "artifacts"
        / run_id
        / "artifact-manifest.json"
    )
    assert pinned.is_file(), "pinned artifact manifest must ship in the bundle"
    assert (bundle / "agents" / "researcher" / "artifacts" / run_id / "prompts" / "system.md").is_file()

    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    artifact_map = manifest.get("artifact_run_id")
    assert isinstance(artifact_map, dict)
    assert artifact_map.get("researcher") == run_id

    readme = (bundle / "README.deploy.md").read_text(encoding="utf-8")
    assert "OS-neutral" in readme
    assert "Linux" in readme
    assert "pinned" in readme.lower() or "artifact" in readme.lower()


def test_e5_s08_platform_docs_matrix() -> None:
    """AC-1 / AC-3 / AC-4 (docs): Linux-first, best-effort Win/macOS, E8-S05 link."""
    for path in (_README_DEPLOY_TEMPLATE, _SHIP_GUIDE):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        assert "linux" in lower
        assert "vm" in lower or "bare metal" in lower
        assert "docker" in lower or "kubernetes" in lower or "k8s" in lower
        assert "os-neutral" in lower
        assert "best-effort" in lower
        assert "not ci-gated" in lower or "not CI-gated" in text
        assert "e8-s05" in lower
        assert "dockerfile" in lower
