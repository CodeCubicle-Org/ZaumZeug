# Story: E4-S09 / E4.8
"""E4-S09 — Workflow paths documentation substring checks."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(*parts: str) -> str:
    return (REPO_ROOT / Path(*parts)).read_text(encoding="utf-8")


def test_e4_s09_ac7_compile_guide_mentions_paths() -> None:
    for rel in (
        "user-docs/guides/compile.md",
        "install/templates/user-docs/guides/compile.md",
    ):
        text = _read(*rel.split("/"))
        assert "workflow-paths.md" in text, rel
        assert "tool-branch" in text.lower() or "tool branch" in text.lower(), rel
        assert "--workflow-diagram-only" in text, rel
        assert "paths" in text.lower(), rel


def test_e4_s09_ac7_multi_agent_workflow_mentions_paths() -> None:
    for rel in (
        "user-docs/guides/multi-agent-workflow.md",
        "install/templates/user-docs/guides/multi-agent-workflow.md",
    ):
        text = _read(*rel.split("/"))
        assert "workflow-paths.md" in text or "path Mermaid" in text, rel


def test_e4_s09_ac7_cli_reference_mentions_paths() -> None:
    text = _read("user-docs/reference/cli.md")
    assert "--workflow-diagram-only" in text
    assert "workflow-paths" in text or "workflow paths" in text.lower()


def test_e4_s09_ac7_architecture_section_54() -> None:
    text = _read("docs/architecture/04-data-flows.md")
    assert "workflow-paths.md" in text
    assert "tool branch" in text.lower() or "tool-branch" in text.lower()
    assert "agent.yaml" in text
    assert "--workflow-diagram-only" in text


def test_e4_s09_ac7_architecture_section_101() -> None:
    text = _read("docs/architecture/07-deploy-packaging.md")
    assert "docs/workflow-paths.md" in text


def test_e4_s09_ac7_architecture_sdk_map() -> None:
    text = _read("docs/architecture/09-sdk-module-map.md")
    assert "workflow_paths.py" in text or "E4-S09" in text or "E4.8" in text


def test_e4_s09_ac7_architecture_anti_pattern() -> None:
    text = _read("docs/architecture/10-operations-and-reference.md")
    assert "workflow-paths" in text


def test_e4_s09_ac7_example_and_template_match() -> None:
    live = _read("usr-harnesses/example/docs/workflow-paths.md")
    template = _read("install/templates/usr-harnesses/example/docs/workflow-paths.md")
    assert live == template
