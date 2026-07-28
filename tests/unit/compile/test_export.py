# Story: E4-S03a / E4.3
"""E4-S03a — Export contract unit tests (manifest paths, omit rewrite, legacy alias)."""

from __future__ import annotations

import json
from pathlib import Path

import dspy
import pytest

from zaumzeug.compile.export import (
    ARTIFACT_MANIFEST_NAME,
    LEGACY_MANIFEST_NAME,
    SYSTEM_PROMPT_REL,
    export_optimized_module,
    find_artifact_manifest,
)


def _plain_module() -> dspy.Module:
    class ResearchModule(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.respond = dspy.Predict("question -> answer")
            self.respond.signature = self.respond.signature.with_instructions(
                "Answer research questions with concise facts."
            )

        def forward(self, question: str) -> dspy.Prediction:
            return self.respond(question=question)

    return ResearchModule()


def _rewrite_module() -> dspy.Module:
    class ResearchWithClarify(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.clarify = dspy.Predict("raw_input -> rewritten")
            self.respond = dspy.Predict("question -> answer")
            self.clarify.signature = self.clarify.signature.with_instructions(
                "Clarify ambiguous user input before the agent loop."
            )
            self.respond.signature = self.respond.signature.with_instructions(
                "Answer using the clarified question."
            )

        def forward(self, question: str) -> dspy.Prediction:
            clarified = self.clarify(raw_input=question)
            return self.respond(question=clarified.rewritten)

    return ResearchWithClarify()


def test_e4_s03_ac3_manifest_lists_paths(tmp_path: Path) -> None:
    """AC-3: artifact-manifest.json lists exported paths including optional input_rewrite."""
    run_dir = tmp_path / "artifacts" / "20260728T120000Z"
    result = export_optimized_module(
        run_dir,
        _rewrite_module(),
        run_id="20260728T120000Z",
        module_ref="modules.researcher:ResearchWithClarify",
        harness_name="example",
        agent_name="researcher",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["paths"]["system_prompt"] == SYSTEM_PROMPT_REL
    assert manifest["paths"]["input_rewrite"] == "prompts/input_rewrite.md"
    assert manifest["paths"]["agent_json"] == "agent.json"
    assert manifest["has_input_rewrite"] is True
    assert manifest["module_hash"]
    assert (run_dir / "prompts" / "input_rewrite.md").is_file()


def test_e4_s03_ac4_no_input_rewrite_when_absent(tmp_path: Path) -> None:
    """AC-4: modules without clarify/rewrite omit input_rewrite — no error."""
    run_dir = tmp_path / "artifacts" / "20260728T120100Z"
    result = export_optimized_module(
        run_dir,
        _plain_module(),
        run_id="20260728T120100Z",
        module_ref="modules.researcher:ResearchModule",
    )

    assert result.has_input_rewrite is False
    assert result.paths.input_rewrite is None
    assert "input_rewrite" not in result.manifest["paths"]
    assert not (run_dir / "prompts" / "input_rewrite.md").exists()
    assert result.manifest_path.is_file()


def test_e4_s03_ac6_writes_artifact_manifest_not_deploy(tmp_path: Path) -> None:
    """AC-6: writes artifact-manifest.json per run (not deploy manifest.json)."""
    run_dir = tmp_path / "usr-harnesses" / "example" / "agents" / "researcher" / "artifacts" / "run1"
    result = export_optimized_module(
        run_dir,
        _plain_module(),
        run_id="run1",
        harness_name="example",
        agent_name="researcher",
    )

    assert result.manifest_path.name == ARTIFACT_MANIFEST_NAME
    assert (run_dir / ARTIFACT_MANIFEST_NAME).is_file()
    # Canonical export does not write deploy-style root manifest.json by default.
    assert not (run_dir / LEGACY_MANIFEST_NAME).exists()
    deploy_root = tmp_path / "deploy" / "example"
    assert not (deploy_root / "manifest.json").exists()


def test_e4_s03_ac8_legacy_manifest_alias(tmp_path: Path) -> None:
    """AC-8: legacy manifest.json alias accepted during migration."""
    artifact_dir = tmp_path / "artifacts" / "legacy-run"
    artifact_dir.mkdir(parents=True)
    legacy = artifact_dir / LEGACY_MANIFEST_NAME
    legacy.write_text(
        json.dumps(
            {
                "run_id": "legacy-run",
                "paths": {"system_prompt": "prompts/system.md"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    found = find_artifact_manifest(artifact_dir)
    assert found == legacy

    # Canonical name wins when both exist.
    canonical = artifact_dir / ARTIFACT_MANIFEST_NAME
    canonical.write_text(json.dumps({"run_id": "canonical"}) + "\n", encoding="utf-8")
    assert find_artifact_manifest(artifact_dir) == canonical

    # write_legacy_alias documents migration path.
    run_dir = tmp_path / "artifacts" / "with-alias"
    export_optimized_module(
        run_dir,
        _plain_module(),
        run_id="with-alias",
        write_legacy_alias=True,
    )
    assert (run_dir / ARTIFACT_MANIFEST_NAME).is_file()
    assert (run_dir / LEGACY_MANIFEST_NAME).is_file()
