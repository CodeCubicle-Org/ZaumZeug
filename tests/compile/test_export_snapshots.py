# Story: E4-S03a / E4.3
"""E4-S03a — Golden export snapshots (with / without optional input rewrite)."""

from __future__ import annotations

import json
from pathlib import Path

import dspy
import pytest

from zaumzeug.compile.export import (
    ARTIFACT_MANIFEST_NAME,
    EXPORT_VERSION,
    export_optimized_module,
    map_dump_state_to_haystack,
)

_GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def _stable_module(*, with_rewrite: bool) -> dspy.Module:
    if with_rewrite:

        class ModuleWithRewrite(dspy.Module):
            def __init__(self) -> None:
                super().__init__()
                self.clarify = dspy.Predict("raw_input -> rewritten")
                self.respond = dspy.Predict("question -> answer")
                self.clarify.signature = self.clarify.signature.with_instructions(
                    "GOLDEN_REWRITE: Clarify and rewrite user input."
                )
                self.respond.signature = self.respond.signature.with_instructions(
                    "GOLDEN_SYSTEM: Answer research questions carefully."
                )

            def forward(self, question: str) -> dspy.Prediction:
                clarified = self.clarify(raw_input=question)
                return self.respond(question=clarified.rewritten)

        return ModuleWithRewrite()

    class PlainModule(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.respond = dspy.Predict("question -> answer")
            self.respond.signature = self.respond.signature.with_instructions(
                "GOLDEN_SYSTEM: Answer research questions carefully."
            )

        def forward(self, question: str) -> dspy.Prediction:
            return self.respond(question=question)

    return PlainModule()


def _snapshot_payload(result_dir: Path) -> dict:
    """Normalize volatile fields for golden comparison."""
    manifest = json.loads((result_dir / ARTIFACT_MANIFEST_NAME).read_text(encoding="utf-8"))
    agent = json.loads((result_dir / "agent.json").read_text(encoding="utf-8"))
    system = (result_dir / "prompts" / "system.md").read_text(encoding="utf-8")
    rewrite_path = result_dir / "prompts" / "input_rewrite.md"
    rewrite = rewrite_path.read_text(encoding="utf-8") if rewrite_path.is_file() else None

    # module_hash is deterministic from dump_state; keep it.
    return {
        "export_version": manifest["export_version"],
        "paths": manifest["paths"],
        "has_input_rewrite": manifest["has_input_rewrite"],
        "optimization_target": manifest["optimization_target"],
        "module_hash": manifest["module_hash"],
        "agent_json": agent,
        "system_prompt": system,
        "input_rewrite": rewrite,
    }


def _assert_matches_golden(actual: dict, golden_name: str) -> None:
    golden_path = _GOLDEN_DIR / golden_name
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    assert actual == expected


def test_e4_s03_ac1_minimal_export_snapshot(tmp_path: Path) -> None:
    """AC-1: dump_state maps to system_prompt, tool descriptions, pipeline Jinja templates."""
    module = _stable_module(with_rewrite=False)
    state = module.dump_state()
    system, paths, agent_json, rewrite = map_dump_state_to_haystack(state, module=module)

    assert "GOLDEN_SYSTEM" in system
    assert paths.system_prompt == "prompts/system.md"
    assert paths.input_rewrite is None
    assert rewrite is None
    assert "tools" in agent_json
    assert isinstance(agent_json["tools"], list)
    assert "templates" in agent_json
    # Field placeholders become Jinja for Haystack pipelines.
    assert any("{{" in v for v in agent_json["templates"].values())

    run_dir = tmp_path / "run-minimal"
    result = export_optimized_module(
        run_dir,
        module,
        run_id="20260728T120000Z",
        module_ref="modules.researcher:PlainModule",
    )
    assert result.manifest["export_version"] == EXPORT_VERSION
    assert (run_dir / "prompts" / "system.md").is_file()
    assert (run_dir / "agent.json").is_file()
    _assert_matches_golden(_snapshot_payload(run_dir), "export_without_rewrite.json")


def test_e4_s03_ac2_export_with_input_rewrite(tmp_path: Path) -> None:
    """AC-2: clarify/rewrite signature text → prompts/input_rewrite.md + manifest path."""
    module = _stable_module(with_rewrite=True)
    run_dir = tmp_path / "run-rewrite"
    result = export_optimized_module(
        run_dir,
        module,
        run_id="20260728T120000Z",
        module_ref="modules.researcher:ModuleWithRewrite",
    )

    assert result.has_input_rewrite is True
    rewrite_file = run_dir / "prompts" / "input_rewrite.md"
    assert rewrite_file.is_file()
    assert "GOLDEN_REWRITE" in rewrite_file.read_text(encoding="utf-8")
    assert result.manifest["paths"]["input_rewrite"] == "prompts/input_rewrite.md"
    _assert_matches_golden(_snapshot_payload(run_dir), "export_with_rewrite.json")


def test_e4_s03_ac7_golden_with_and_without_rewrite(tmp_path: Path) -> None:
    """AC-7: golden snapshot tests for export shape (with and without rewrite)."""
    plain_dir = tmp_path / "plain"
    rewrite_dir = tmp_path / "rewrite"
    export_optimized_module(
        plain_dir,
        _stable_module(with_rewrite=False),
        run_id="plain",
    )
    export_optimized_module(
        rewrite_dir,
        _stable_module(with_rewrite=True),
        run_id="rewrite",
    )

    plain_snap = _snapshot_payload(plain_dir)
    rewrite_snap = _snapshot_payload(rewrite_dir)
    _assert_matches_golden(plain_snap, "export_without_rewrite.json")
    _assert_matches_golden(rewrite_snap, "export_with_rewrite.json")

    assert plain_snap["has_input_rewrite"] is False
    assert rewrite_snap["has_input_rewrite"] is True
    assert plain_snap["input_rewrite"] is None
    assert rewrite_snap["input_rewrite"] is not None
    assert "input_rewrite" not in plain_snap["paths"]
    assert "input_rewrite" in rewrite_snap["paths"]
