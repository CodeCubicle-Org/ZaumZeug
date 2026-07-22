# Story: E1-S04 / E1.4
"""E1-S04 — ``zaumzeug init`` command (unit)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zaumzeug.cli import _init_command, build_parser
from zaumzeug.config import load_agent_config, load_harness, load_workflow
from zaumzeug.scaffold import ScaffoldError, init_harness, validate_harness_name


def test_e1_s04_ac1_creates_harness_folder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-1: ``zaumzeug init <name>`` creates ``usr-harnesses/<name>/``."""
    project_root = tmp_path / "project"
    (project_root / "usr-harnesses").mkdir(parents=True)
    monkeypatch.setattr(
        "zaumzeug.scaffold.init.find_project_root",
        lambda start=None: project_root,
    )

    parser = build_parser()
    args = parser.parse_args(["init", "my-agent"])
    assert _init_command(args) == 0

    harness_dir = project_root / "usr-harnesses" / "my-agent"
    assert harness_dir.is_dir()
    assert (harness_dir / "harness.yaml").is_file()
    assert (harness_dir / "workflow.yaml").is_file()
    assert (harness_dir / "agents" / "agent" / "agent.yaml").is_file()

    out = capsys.readouterr().out
    assert "Created harness" in out
    assert "zaumzeug doctor my-agent" in out
    assert "zaumzeug serve my-agent" in out


def test_e1_s04_ac2_generated_yaml_validates(tmp_path: Path) -> None:
    """AC-2: Generated ``harness.yaml`` passes Phase 1 Pydantic validation."""
    project_root = tmp_path / "project"
    (project_root / "usr-harnesses").mkdir(parents=True)

    harness_dir = init_harness("valid-one", project_root=project_root)
    config = load_harness(harness_dir / "harness.yaml")
    assert config.name == "valid-one"
    assert config.serve is not None
    assert config.serve.hayhooks.port == 1416

    load_workflow(harness_dir)
    load_agent_config(harness_dir / "agents" / "agent" / "agent.yaml")


def test_e1_s04_ac3_template_has_runtime_serve_models(tmp_path: Path) -> None:
    """AC-3: Template includes runtime (system_prompt), serve, and models ref."""
    project_root = tmp_path / "project"
    (project_root / "usr-harnesses").mkdir(parents=True)

    harness_dir = init_harness("templated", project_root=project_root)
    harness = yaml.safe_load((harness_dir / "harness.yaml").read_text(encoding="utf-8"))
    assert harness["name"] == "templated"
    assert "serve" in harness
    assert harness["serve"]["hayhooks"]["port"] == 1416
    assert harness.get("models") == "models.yaml"
    assert (harness_dir / "models.yaml").is_file()

    agent = yaml.safe_load(
        (harness_dir / "agents" / "agent" / "agent.yaml").read_text(encoding="utf-8")
    )
    assert agent["agent"]["system_prompt"] == "prompts/system.md"
    assert (harness_dir / "agents" / "agent" / "prompts" / "system.md").is_file()

    models = yaml.safe_load(
        (harness_dir / "agents" / "agent" / "agents-models.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert models["default_model_id"] == "mock"
    assert "mock" in models["models"]


def test_e1_s04_ac4_fails_if_exists_without_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-4: Fails fast if harness exists unless ``--force``."""
    project_root = tmp_path / "project"
    (project_root / "usr-harnesses").mkdir(parents=True)
    monkeypatch.setattr(
        "zaumzeug.scaffold.init.find_project_root",
        lambda start=None: project_root,
    )

    init_harness("dup", project_root=project_root)
    marker = project_root / "usr-harnesses" / "dup" / "custom.txt"
    marker.write_text("keep-me", encoding="utf-8")

    with pytest.raises(ScaffoldError, match="already exists"):
        init_harness("dup", project_root=project_root)

    parser = build_parser()
    assert _init_command(parser.parse_args(["init", "dup"])) == 1
    err = capsys.readouterr().err
    assert "already exists" in err
    assert "--force" in err
    assert marker.is_file()

    assert _init_command(parser.parse_args(["init", "dup", "--force"])) == 0
    assert not marker.exists()
    assert (project_root / "usr-harnesses" / "dup" / "harness.yaml").is_file()


@pytest.mark.parametrize(
    "bad_name",
    ["", "..", "../x", "a/b", r"a\b", "-bad", "has space", ".hidden"],
)
def test_e1_s04_rejects_unsafe_harness_names(bad_name: str) -> None:
    """Name validation rejects traversal and unsafe path segments."""
    with pytest.raises(ScaffoldError):
        validate_harness_name(bad_name)
