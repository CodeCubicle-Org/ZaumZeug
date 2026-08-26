# Story: E6-S02 / E6.2
"""E6-S02 — ``zaumzeug eval`` command (builtin + DeepEval frameworks)."""

from __future__ import annotations

import builtins
import inspect
import json
from pathlib import Path

import pytest
import yaml

from zaumzeug.cli import _eval_command, build_parser
from zaumzeug.eval import DEEPEVAL_MISSING_MESSAGE
from zaumzeug.eval.runner import (
    MISSING_EVAL_MESSAGE,
    EvalError,
    builtin_match,
    resolve_eval_framework,
    run_eval,
)


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _minimal_eval_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    eval_section: dict | None = None,
    include_eval: bool = True,
    valset_rows: list[dict] | None = None,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / harness_name
    harness_dir.mkdir(parents=True, exist_ok=True)

    if eval_section is None:
        eval_section = {
            "framework": "builtin",
            "valset": "data/val.jsonl",
        }

    harness_yaml: dict = {
        "name": harness_name,
        "serve": {"hayhooks": {"port": 1416}},
    }
    if include_eval:
        harness_yaml["eval"] = eval_section

    _write_yaml(harness_dir / "harness.yaml", harness_yaml)
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_dir = harness_dir / "agents" / "researcher"
    _write_yaml(
        agent_dir / "agent.yaml",
        {
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
        },
    )
    prompt_path = agent_dir / "prompts" / "system.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("You are a researcher.", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {
                "mock": {"provider": "mock", "model": "harness-fixture"},
            },
        },
    )

    if include_eval:
        rows = valset_rows
        if rows is None:
            rows = [
                {"input": "hello", "expected_output": "world"},
                {"input": "ping", "expected_output": "pong"},
            ]
        valset_rel = eval_section.get("valset", "data/val.jsonl")
        _write_jsonl(harness_dir / valset_rel, rows)

    return harness_dir


def test_builtin_match_exact_and_substring() -> None:
    assert builtin_match("hello world", "hello world") is True
    assert builtin_match("prefix hello world suffix", "hello world") is True
    assert builtin_match("hello", "world") is False
    assert builtin_match("anything", None) is True


def test_e6_s02_ac1_deepeval_missing_extra_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: eval.framework deepeval requires [eval] extra; shows install hint."""
    _minimal_eval_harness(
        tmp_path,
        eval_section={
            "framework": "deepeval",
            "valset": "data/val.jsonl",
            "metrics": [{"type": "AnswerRelevancyMetric", "threshold": 0.5}],
        },
    )

    real_import = builtins.__import__

    def _block_deepeval(name: str, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "deepeval" or name.startswith("deepeval."):
            raise ImportError("blocked for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _block_deepeval)

    with pytest.raises(EvalError) as exc_info:
        run_eval(
            "example",
            project_root=tmp_path,
            agent_runner=lambda _inp: "unused",
        )

    message = str(exc_info.value)
    assert message == DEEPEVAL_MISSING_MESSAGE
    assert 'pip install "zaumzeug[eval]"' in message


def test_e6_s02_ac2_builtin_jsonl_checks(tmp_path: Path) -> None:
    """AC-2: eval.framework builtin runs JSONL checks without DeepEval."""
    _minimal_eval_harness(
        tmp_path,
        eval_section={"framework": "builtin", "valset": "data/val.jsonl"},
        valset_rows=[
            {"input": "q1", "expected_output": "alpha"},
            {"input": "q2", "expected_output": "beta"},
            {"input": "q3", "expected_output": "missing"},
        ],
    )

    outputs = {"q1": "alpha", "q2": "prefix beta suffix", "q3": "gamma"}

    result = run_eval(
        "example",
        project_root=tmp_path,
        agent_runner=lambda inp: outputs[inp],
    )

    assert result.framework == "builtin"
    assert result.passed == 2
    assert result.failed == 1
    assert result.exit_code == 1
    assert result.cases[0].passed is True
    assert result.cases[1].passed is True
    assert result.cases[2].passed is False


def test_e6_s02_ac3_missing_eval_section_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-3: Missing eval section → clear error exit."""
    harness_dir = tmp_path / "usr-harnesses" / "example"
    harness_dir.mkdir(parents=True)
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
        {"name": "researcher", "agent": {"system_prompt": "prompts/system.md"}},
    )
    (agent_dir / "prompts").mkdir(parents=True)
    (agent_dir / "prompts" / "system.md").write_text("hi", encoding="utf-8")
    _write_yaml(
        agent_dir / "agents-models.yaml",
        {
            "default_model_id": "mock",
            "models": {"mock": {"provider": "mock", "model": "harness-fixture"}},
        },
    )

    with pytest.raises(EvalError, match="No eval configured") as exc_info:
        run_eval("example", project_root=tmp_path)

    assert str(exc_info.value) == MISSING_EVAL_MESSAGE

    def _fake_run_eval(harness_name, **kwargs):
        raise EvalError(MISSING_EVAL_MESSAGE, harness_name=harness_name)

    import zaumzeug.eval.runner as eval_runner

    monkeypatch.setattr(eval_runner, "run_eval", _fake_run_eval)
    parser = build_parser()
    args = parser.parse_args(["eval", "example"])
    code = _eval_command(args)
    captured = capsys.readouterr()
    assert code == 1
    assert "No eval configured" in captured.err


def test_e6_s02_ac4_cli_framework_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-4: CLI ``zaumzeug eval <name> --framework builtin`` overrides yaml."""
    _minimal_eval_harness(
        tmp_path,
        eval_section={
            "framework": "deepeval",
            "valset": "data/val.jsonl",
            "metrics": [{"type": "AnswerRelevancyMetric", "threshold": 0.5}],
        },
        valset_rows=[{"input": "hello", "expected_output": "hello"}],
    )

    real_import = builtins.__import__

    def _block_deepeval(name: str, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "deepeval" or name.startswith("deepeval."):
            raise ImportError("blocked for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _block_deepeval)

    result = run_eval(
        "example",
        project_root=tmp_path,
        framework="builtin",
        agent_runner=lambda inp: inp,
    )
    assert result.framework == "builtin"
    assert result.failed == 0
    assert result.exit_code == 0

    parser = build_parser()
    args = parser.parse_args(["eval", "example", "--framework", "builtin"])
    assert args.framework == "builtin"

    def _fake_run_eval(harness_name, **kwargs):
        assert harness_name == "example"
        assert kwargs.get("framework") == "builtin"
        from zaumzeug.eval.runner import EvalResult

        return EvalResult(
            harness_name="example",
            harness_dir=tmp_path / "usr-harnesses" / "example",
            framework="builtin",
            agent_name="researcher",
            passed=1,
            failed=0,
        )

    import zaumzeug.eval.runner as eval_runner

    monkeypatch.setattr(eval_runner, "run_eval", _fake_run_eval)
    code = _eval_command(args)
    captured = capsys.readouterr()
    assert code == 0
    assert "builtin" in captured.out


def test_e6_s02_ac5_default_deepeval_when_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-5: Default framework deepeval when eval: present and framework omitted."""
    from zaumzeug.config import EvalConfig

    cfg = EvalConfig(valset="data/val.jsonl")
    assert cfg.framework is None
    assert resolve_eval_framework(cfg) == "deepeval"

    _minimal_eval_harness(
        tmp_path,
        eval_section={
            # framework intentionally omitted
            "valset": "data/val.jsonl",
            "metrics": [{"type": "AnswerRelevancyMetric", "threshold": 0.5}],
        },
    )

    real_import = builtins.__import__

    def _block_deepeval(name: str, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "deepeval" or name.startswith("deepeval."):
            raise ImportError("blocked for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _block_deepeval)

    with pytest.raises(EvalError) as exc_info:
        run_eval(
            "example",
            project_root=tmp_path,
            agent_runner=lambda _inp: "unused",
        )

    # Missing-extra hint proves the resolved framework was deepeval (not builtin).
    assert str(exc_info.value) == DEEPEVAL_MISSING_MESSAGE


def test_e6_s02_dod_serve_does_not_import_eval() -> None:
    """DoD: ``zaumzeug eval`` / DeepEval never run on the production serve path.

    E8-S03 may wrap ``Agent.run`` for opt-in JSONL capture (``eval.ratchet``);
    that is not ``run_eval`` and does not import DeepEval.
    """
    import zaumzeug.serve.runner as serve_runner

    source = inspect.getsource(serve_runner)
    assert "run_eval" not in source
    assert "require_deepeval" not in source
    assert "deepeval" not in source.lower()
