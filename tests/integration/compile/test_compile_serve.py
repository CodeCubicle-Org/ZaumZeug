# Story: E4-S03b / E4.3
# Story: E4-S05 / E4.5
"""E4-S03b — Runtime ``input_rewrite`` preprocess; E4-S05 — post-compile serve uses artifact."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml
from haystack.dataclasses import ChatMessage

from zaumzeug.compile.export import find_artifact_manifest
from zaumzeug.compile.gepa_runner import StubGEPA
from zaumzeug.compile.runner import run_compile
from zaumzeug.config.models import AgentModelsConfig
from zaumzeug.config.resolver import ARTIFACT_MANIFEST, RuntimeSource
from zaumzeug.runtime.factory import (
    BuiltAgent,
    RuntimeFactoryError,
    build_agent_bundle,
    load_system_prompt,
)
from zaumzeug.runtime.model_router import ModelRouter
from zaumzeug.runtime.preprocess import (
    apply_input_rewrite,
    load_input_rewrite_template,
    preprocess_openai_messages,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = REPO_ROOT / "src" / "zaumzeug" / "runtime"
_FORBIDDEN_ROOTS = frozenset({"dspy", "gepa"})


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


def _mock_router(project_root: Path) -> ModelRouter:
    return ModelRouter(
        AgentModelsConfig.model_validate(
            {
                "default_model_id": "mock",
                "models": {
                    "mock": {"provider": "mock", "model": "harness-fixture"},
                },
            }
        ),
        project_root=project_root,
    )


def _artifact_harness(
    tmp_path: Path,
    *,
    input_rewrite: str | None = "Clarify: {{ user_input }}",
    list_rewrite_in_manifest: bool = True,
    write_rewrite_file: bool = True,
    hand_edited_prompt: str | None = None,
    compile_module: str | None = None,
    system_prompt_in_yaml: bool = False,
) -> tuple[Path, Path]:
    """Scaffold harness with artifact; return (harness_dir, artifact_dir)."""
    harness_dir = tmp_path / "usr-harnesses" / "example"
    _write_yaml(
        harness_dir / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"
    artifact_dir = agent_dir / "artifacts" / "current"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    prompts = artifact_dir / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    (prompts / "system.md").write_text("You are a researcher.\n", encoding="utf-8")

    paths: dict[str, str] = {
        "system_prompt": "prompts/system.md",
        "agent_json": "agent.json",
    }
    has_rewrite = input_rewrite is not None and list_rewrite_in_manifest
    if has_rewrite:
        paths["input_rewrite"] = "prompts/input_rewrite.md"
        if write_rewrite_file:
            assert input_rewrite is not None
            (prompts / "input_rewrite.md").write_text(
                input_rewrite if input_rewrite.endswith("\n") else input_rewrite + "\n",
                encoding="utf-8",
            )

    manifest = {
        "export_version": 1,
        "run_id": "test-run",
        "module_hash": "abc",
        "paths": paths,
        "has_input_rewrite": has_rewrite,
        "optimization_target": "template",
    }
    (artifact_dir / ARTIFACT_MANIFEST).write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "agent.json").write_text("{}\n", encoding="utf-8")

    agent_block: dict[str, Any] = {"artifact": "artifacts/current"}
    if system_prompt_in_yaml or hand_edited_prompt is not None:
        agent_block["system_prompt"] = "prompts/system.md"
        hand_path = agent_dir / "prompts" / "system.md"
        hand_path.parent.mkdir(parents=True, exist_ok=True)
        hand_path.write_text(
            hand_edited_prompt or "HAND_EDITED_PROMPT_SHOULD_BE_IGNORED\n",
            encoding="utf-8",
        )

    agent_yaml: dict[str, Any] = {
        "name": "researcher",
        "default_model_id": "mock",
        "agent": agent_block,
    }
    if compile_module is not None:
        agent_yaml["compile"] = {
            "module": compile_module,
            "task_model_id": "mock",
            "reflection_model_id": "mock",
            "auto": "light",
        }

    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )
    return harness_dir, artifact_dir


_PLAIN_MODULE = '''\
import dspy

class ResearchModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.respond = dspy.Predict("question -> answer")
        self.respond.signature = self.respond.signature.with_instructions(
            "COMPILED_ARTIFACT_SYSTEM_PROMPT"
        )

    def forward(self, question: str):
        return dspy.Prediction(answer="harness")
'''


def _scaffold_compile_then_serve(project_root: Path) -> Path:
    """Compile a harness and point agent.artifact at artifacts/current."""
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
            "agent": {
                "system_prompt": "prompts/system.md",
                "artifact": "artifacts/current",
            },
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
    prompt.write_text("HAND_EDITED_BEFORE_COMPILE\n", encoding="utf-8")
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
    train = agent_dir / "data" / "train.jsonl"
    train.parent.mkdir(parents=True, exist_ok=True)
    train.write_text(
        '{"question": "What is ZaumZeug?", "answer": "harness"}\n',
        encoding="utf-8",
    )
    return harness_dir


def _imported_roots(source: str) -> set[str]:
    tree = ast.parse(source)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_e4_s03b_ac1_loads_input_rewrite_from_manifest(tmp_path: Path) -> None:
    """AC-1: When artifact-manifest.json lists input_rewrite, runtime loads it."""
    harness_dir, artifact_dir = _artifact_harness(tmp_path)
    built = build_agent_bundle(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert isinstance(built, BuiltAgent)
    assert built.resolution.source is RuntimeSource.ARTIFACT
    assert built.resolution.path == artifact_dir.resolve()
    assert built.input_rewrite_template is not None
    assert "Clarify:" in built.input_rewrite_template
    assert "{{ user_input }}" in built.input_rewrite_template

    loaded = load_input_rewrite_template(artifact_dir)
    assert loaded is not None
    assert loaded.strip() == "Clarify: {{ user_input }}"


def test_e4_s03b_ac2_preprocess_before_agent_run(tmp_path: Path) -> None:
    """AC-2: User message is preprocessed through the fixed template before Agent.run."""
    harness_dir, _artifact_dir = _artifact_harness(
        tmp_path,
        input_rewrite="REWRITE: {{ user_input }}",
    )
    built = build_agent_bundle(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert built.input_rewrite_template is not None

    expected = apply_input_rewrite(built.input_rewrite_template, "raw question")
    assert expected == "REWRITE: raw question"

    openai_messages = preprocess_openai_messages(
        built.input_rewrite_template,
        [{"role": "user", "content": "raw question"}],
    )
    assert openai_messages[0]["content"] == expected

    captured: list[Any] = []
    original_run = built.agent.run

    def _spy_run(**kwargs: Any) -> Any:
        captured.append(kwargs.get("messages"))
        return original_run(**kwargs)

    built.agent.run = _spy_run  # type: ignore[method-assign]
    chat_messages = [
        ChatMessage.from_openai_dict_format(message) for message in openai_messages
    ]
    built.agent.run(messages=chat_messages)

    assert len(captured) == 1
    assert captured[0] is not None
    assert captured[0][0].text == expected


def test_e4_s03b_ac3_no_dspy_on_serve_path() -> None:
    """AC-3: No DSPy import on serve/run path when only preprocess runs."""
    paths = [
        RUNTIME_DIR / "preprocess.py",
        RUNTIME_DIR / "factory.py",
        RUNTIME_DIR / "workflow.py",
        REPO_ROOT / "src" / "zaumzeug" / "serve" / "runner.py",
    ]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        roots = _imported_roots(source)
        forbidden = sorted(roots & _FORBIDDEN_ROOTS)
        assert forbidden == [], f"{path.name} imports forbidden modules: {forbidden}"

    # Runtime import of preprocess must not pull dspy into sys.modules.
    before = {name for name in sys.modules if name == "dspy" or name.startswith("dspy.")}
    import zaumzeug.runtime.preprocess as preprocess_mod  # noqa: F401
    import zaumzeug.runtime.factory as factory_mod  # noqa: F401

    after = {name for name in sys.modules if name == "dspy" or name.startswith("dspy.")}
    assert after == before


def test_e4_s03b_ac4_missing_rewrite_actionable_error(tmp_path: Path) -> None:
    """AC-4: Missing input_rewrite file when manifest lists it → actionable error."""
    harness_dir, artifact_dir = _artifact_harness(
        tmp_path,
        input_rewrite="unused",
        list_rewrite_in_manifest=True,
        write_rewrite_file=False,
    )
    expected_path = (artifact_dir / "prompts" / "input_rewrite.md").resolve()
    assert not expected_path.is_file()

    with pytest.raises(RuntimeFactoryError, match="input_rewrite") as exc_info:
        build_agent_bundle(
            harness_dir,
            harness_name="example",
            agent_name="researcher",
            router=_mock_router(tmp_path),
        )
    message = str(exc_info.value)
    assert str(expected_path) in message or "prompts" in message
    assert "missing" in message.lower() or "not found" in message.lower() or "lists" in message


def test_e4_s03b_omit_rewrite_when_absent(tmp_path: Path) -> None:
    """Harnesses without input_rewrite pass user text through unchanged."""
    harness_dir, _ = _artifact_harness(
        tmp_path,
        input_rewrite=None,
        list_rewrite_in_manifest=False,
    )
    built = build_agent_bundle(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert built.input_rewrite_template is None
    messages = preprocess_openai_messages(
        None,
        [{"role": "user", "content": "plain"}],
    )
    assert messages[0]["content"] == "plain"


def test_e4_s03b_plain_instruction_template_prepends() -> None:
    """Plain export text (no placeholders) is prepended to the user message."""
    result = apply_input_rewrite("GOLDEN_REWRITE: Clarify input.", "hello")
    assert result == "GOLDEN_REWRITE: Clarify input.\n\nhello"


def test_e4_s03b_serve_wrapper_applies_rewrite(tmp_path: Path) -> None:
    """Serve path applies rewrite before Agent.run (E4-S05 integration seam)."""
    from zaumzeug.serve.runner import AgentPipelineWrapper

    harness_dir, _ = _artifact_harness(
        tmp_path,
        input_rewrite="SERVE: {{ user_input }}",
    )
    built = build_agent_bundle(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    captured: list[Any] = []

    def _fake_run(*, messages: list[ChatMessage]) -> dict[str, Any]:
        captured.append(messages)
        return {"last_message": ChatMessage.from_assistant("ok")}

    built.agent.run = MagicMock(side_effect=_fake_run)  # type: ignore[method-assign]
    wrapper = AgentPipelineWrapper(
        built.agent,
        router=_mock_router(tmp_path),
        input_rewrite_template=built.input_rewrite_template,
    )
    out = wrapper.run_api("need clarity")
    assert out == "ok"
    assert len(captured) == 1
    assert captured[0][0].text == "SERVE: need clarity"


def test_e4_s05_ac1_serve_uses_artifact_after_compile(tmp_path: Path) -> None:
    """AC-1: After compile, serve/factory resolves and loads the artifact path."""
    _purge_import("modules")
    _purge_import("modules.researcher")
    harness_dir = _scaffold_compile_then_serve(tmp_path)

    result = run_compile(
        "example",
        project_root=tmp_path,
        gepa_cls=StubGEPA,
        stub_gepa=True,
    )
    assert result.exit_code == 0
    agent = result.agents[0]
    assert agent.run_id is not None
    current = harness_dir / "agents" / "researcher" / "artifacts" / "current"
    assert current.exists()
    assert find_artifact_manifest(current) is not None

    built = build_agent_bundle(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert built.resolution.source is RuntimeSource.ARTIFACT
    assert built.resolution.path.resolve() == current.resolve()
    prompt = load_system_prompt(built.resolution)
    assert "COMPILED_ARTIFACT_SYSTEM_PROMPT" in prompt
    assert "HAND_EDITED_BEFORE_COMPILE" not in prompt


def test_e4_s05_ac2_no_module_import_at_serve(tmp_path: Path) -> None:
    """AC-2: Serve/run ignores compile.module — no DSPy module import on factory path."""
    harness_dir, _ = _artifact_harness(
        tmp_path,
        input_rewrite=None,
        list_rewrite_in_manifest=False,
        compile_module="modules.researcher:ResearchModule",
    )
    # Deliberately omit the module file — serve must still succeed from artifact.
    agent_dir = harness_dir / "agents" / "researcher"
    assert not (agent_dir / "modules" / "researcher.py").is_file()

    before = {
        name
        for name in sys.modules
        if name == "dspy"
        or name.startswith("dspy.")
        or name == "modules"
        or name.startswith("modules.")
    }
    built = build_agent_bundle(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    after = {
        name
        for name in sys.modules
        if name == "dspy"
        or name.startswith("dspy.")
        or name == "modules"
        or name.startswith("modules.")
    }
    assert built.resolution.source is RuntimeSource.ARTIFACT
    assert after == before


def test_e4_s05_ac3_artifact_over_hand_edited_prompt(tmp_path: Path) -> None:
    """AC-3: Valid artifact ignores hand-edited system_prompt beside agent.yaml."""
    harness_dir, artifact_dir = _artifact_harness(
        tmp_path,
        input_rewrite=None,
        list_rewrite_in_manifest=False,
        hand_edited_prompt="HAND_EDITED_SHOULD_BE_IGNORED\n",
        system_prompt_in_yaml=True,
    )
    (artifact_dir / "prompts" / "system.md").write_text(
        "FROM_ARTIFACT_ONLY\n",
        encoding="utf-8",
    )
    built = build_agent_bundle(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert built.resolution.source is RuntimeSource.ARTIFACT
    prompt = load_system_prompt(built.resolution)
    assert "FROM_ARTIFACT_ONLY" in prompt
    assert "HAND_EDITED" not in prompt
    assert built.agent.system_prompt is not None
    assert "FROM_ARTIFACT_ONLY" in built.agent.system_prompt


def test_e4_s05_ac4_input_rewrite_preprocess_no_dspy(tmp_path: Path) -> None:
    """AC-4: Optional input_rewrite preprocess on serve path — no GEPA/DSPy at runtime."""
    from zaumzeug.serve.runner import AgentPipelineWrapper

    harness_dir, _ = _artifact_harness(
        tmp_path,
        input_rewrite="E4S05: {{ user_input }}",
    )
    paths = [
        RUNTIME_DIR / "preprocess.py",
        RUNTIME_DIR / "factory.py",
        REPO_ROOT / "src" / "zaumzeug" / "serve" / "runner.py",
    ]
    for path in paths:
        forbidden = sorted(_imported_roots(path.read_text(encoding="utf-8")) & _FORBIDDEN_ROOTS)
        assert forbidden == [], f"{path.name} imports forbidden: {forbidden}"

    built = build_agent_bundle(
        harness_dir,
        harness_name="example",
        agent_name="researcher",
        router=_mock_router(tmp_path),
    )
    assert built.input_rewrite_template is not None

    captured: list[Any] = []

    def _fake_run(*, messages: list[ChatMessage]) -> dict[str, Any]:
        captured.append(messages)
        return {"last_message": ChatMessage.from_assistant("done")}

    built.agent.run = MagicMock(side_effect=_fake_run)  # type: ignore[method-assign]
    wrapper = AgentPipelineWrapper(
        built.agent,
        router=_mock_router(tmp_path),
        input_rewrite_template=built.input_rewrite_template,
    )
    assert wrapper.run_api("ping") == "done"
    assert captured[0][0].text == "E4S05: ping"
