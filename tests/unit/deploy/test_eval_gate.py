# Story: E5-S06 / E5.6 (shared E6-S03 / E6.3)
"""E5-S06 / E6-S03 — Deploy eval gate (Architecture §6.4)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import yaml

from zaumzeug.cli import _deploy_command, build_parser
from zaumzeug.deploy.packager import (
    DeployError,
    apply_eval_gate,
    package_harness,
    resolve_eval_gate,
)
from zaumzeug.eval.runner import EvalCaseResult, EvalResult


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


def _minimal_deploy_harness(
    project_root: Path,
    *,
    harness_name: str = "example",
    eval_section: dict | None = None,
    include_eval: bool = True,
    deploy_section: dict | None = None,
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
    if deploy_section is not None:
        harness_yaml["deploy"] = deploy_section

    _write_yaml(harness_dir / "harness.yaml", harness_yaml)
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    diagram = harness_dir / "docs" / "workflow-diagram.md"
    diagram.parent.mkdir(parents=True, exist_ok=True)
    diagram.write_text(
        "# Workflow diagram — test\n\n```mermaid\nflowchart LR\n  s0[researcher]\n```\n",
        encoding="utf-8",
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


def _fake_eval_result(
    harness_name: str,
    harness_dir: Path,
    *,
    failed: int = 0,
) -> EvalResult:
    cases = [
        EvalCaseResult(
            index=0,
            input="hello",
            expected_output="world",
            actual_output="world" if failed == 0 else "nope",
            passed=failed == 0,
        )
    ]
    if failed > 1:
        cases.append(
            EvalCaseResult(
                index=1,
                input="ping",
                expected_output="pong",
                actual_output="nope",
                passed=False,
            )
        )
    passed = len(cases) - failed
    return EvalResult(
        harness_name=harness_name,
        harness_dir=harness_dir,
        framework="builtin",
        agent_name="researcher",
        cases=cases,
        passed=passed,
        failed=failed,
    )


def test_e5_s06_ac1_skip_warn_block_behaviors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: deploy.eval_gate skip | warn | block behaves per Architecture §6.4."""
    monkeypatch.chdir(tmp_path)
    harness_dir = _minimal_deploy_harness(
        tmp_path,
        deploy_section={"eval_gate": "skip"},
    )

    calls: list[str] = []

    def _tracking_eval(harness_name: str, **kwargs):  # noqa: ANN003
        calls.append(harness_name)
        return _fake_eval_result(harness_name, harness_dir, failed=1)

    # skip — do not run eval
    skip_result = package_harness(
        "example",
        project_root=tmp_path,
        run_eval_fn=_tracking_eval,
        output=io.StringIO(),
    )
    assert skip_result.eval_gate.mode == "skip"
    assert skip_result.eval_gate.skipped is True
    assert skip_result.eval_gate.eval_ran is False
    assert skip_result.packaged is True
    assert calls == []

    # block — run eval; abort on failure
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": "example",
            "serve": {"hayhooks": {"port": 1416}},
            "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
            "deploy": {"eval_gate": "block"},
        },
    )
    block_result = package_harness(
        "example",
        project_root=tmp_path,
        run_eval_fn=_tracking_eval,
        output=io.StringIO(),
    )
    assert block_result.eval_gate.mode == "block"
    assert block_result.eval_gate.blocked is True
    assert block_result.packaged is False
    assert calls == ["example"]

    # warn — run eval; continue on failure
    _write_yaml(
        harness_dir / "harness.yaml",
        {
            "name": "example",
            "serve": {"hayhooks": {"port": 1416}},
            "eval": {"framework": "builtin", "valset": "data/val.jsonl"},
            "deploy": {"eval_gate": "warn"},
        },
    )
    warn_out = io.StringIO()
    warn_result = package_harness(
        "example",
        project_root=tmp_path,
        run_eval_fn=_tracking_eval,
        output=warn_out,
    )
    assert warn_result.eval_gate.mode == "warn"
    assert warn_result.eval_gate.blocked is False
    assert warn_result.packaged is True
    assert "continuing deploy" in warn_out.getvalue()
    assert calls == ["example", "example"]


def test_e5_s06_ac2_cli_override_eval_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: CLI ``zaumzeug deploy <name> --eval-gate block`` overrides yaml."""
    monkeypatch.chdir(tmp_path)
    harness_dir = _minimal_deploy_harness(
        tmp_path,
        deploy_section={"eval_gate": "skip"},
    )

    seen: dict[str, object] = {}

    def _fake_eval(harness_name: str, **kwargs):  # noqa: ANN003
        seen["ran"] = True
        return _fake_eval_result(harness_name, harness_dir, failed=1)

    # Override skip → block via package_harness API
    result = package_harness(
        "example",
        eval_gate="block",
        project_root=tmp_path,
        run_eval_fn=_fake_eval,
        output=io.StringIO(),
    )
    assert seen.get("ran") is True
    assert result.eval_gate.mode == "block"
    assert result.eval_gate.blocked is True
    assert result.exit_code == 1

    # CLI parses --eval-gate and passes override into packager
    parser = build_parser()
    args = parser.parse_args(["deploy", "example", "--eval-gate", "block"])
    assert args.eval_gate == "block"

    import zaumzeug.deploy.packager as packager_mod

    captured: dict[str, object] = {}

    def _spy_package(harness_name: str, **kwargs):  # noqa: ANN003
        captured["eval_gate"] = kwargs.get("eval_gate")
        return package_harness(
            harness_name,
            eval_gate=kwargs.get("eval_gate"),
            project_root=tmp_path,
            run_eval_fn=_fake_eval,
            output=io.StringIO(),
        )

    monkeypatch.setattr(packager_mod, "package_harness", _spy_package)
    # Re-import handler path uses package_harness from packager at call time
    code = _deploy_command(args)
    assert captured.get("eval_gate") == "block"
    assert code == 1


def test_e5_s06_ac3_block_noop_without_eval_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: If no eval section, block is a no-op."""
    monkeypatch.chdir(tmp_path)
    _minimal_deploy_harness(
        tmp_path,
        include_eval=False,
        deploy_section={"eval_gate": "block"},
    )

    calls: list[str] = []

    def _should_not_run(harness_name: str, **kwargs):  # noqa: ANN003
        calls.append(harness_name)
        raise AssertionError("run_eval must not be called when eval: is absent")

    result = package_harness(
        "example",
        project_root=tmp_path,
        run_eval_fn=_should_not_run,
        output=io.StringIO(),
    )
    assert result.eval_gate.mode == "block"
    assert result.eval_gate.skipped is True
    assert result.eval_gate.blocked is False
    assert result.packaged is True
    assert calls == []


def test_e5_s06_ac4_warn_continues_after_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: warn continues deploy after printing failures."""
    monkeypatch.chdir(tmp_path)
    harness_dir = _minimal_deploy_harness(
        tmp_path,
        deploy_section={"eval_gate": "warn"},
    )

    def _failing_eval(harness_name: str, **kwargs):  # noqa: ANN003
        return _fake_eval_result(harness_name, harness_dir, failed=2)

    packs: list[str] = []

    def _spy_write(
        harness_name: str,
        *,
        project_root: Path,
        harness_dir: Path,
        harness_config,
        **_kwargs,
    ) -> Path:
        packs.append(harness_name)
        dest = project_root / "deploy" / harness_name
        dest.mkdir(parents=True, exist_ok=True)
        return dest

    out = io.StringIO()
    result = package_harness(
        "example",
        project_root=tmp_path,
        run_eval_fn=_failing_eval,
        write_bundle=_spy_write,
        output=out,
    )
    text = out.getvalue()
    assert "FAIL" in text or "failure" in text.lower()
    assert "continuing deploy" in text
    assert result.packaged is True
    assert result.eval_gate.blocked is False
    assert packs == ["example"]


def test_e6_s03_ac2_packager_invokes_eval_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E6-S03 AC-2: Eval runner invoked from deploy packager when gate is warn or block."""
    monkeypatch.chdir(tmp_path)
    harness_dir = _minimal_deploy_harness(tmp_path)

    for mode in ("warn", "block"):
        calls: list[str] = []

        def _make_tracking(call_list: list[str]):
            def _tracking_eval(harness_name: str, **kwargs):  # noqa: ANN003
                call_list.append(harness_name)
                return _fake_eval_result(harness_name, harness_dir, failed=0)

            return _tracking_eval

        result = package_harness(
            "example",
            eval_gate=mode,
            project_root=tmp_path,
            run_eval_fn=_make_tracking(calls),
            output=io.StringIO(),
        )
        assert calls == ["example"], f"expected run_eval for gate={mode}"
        assert result.eval_gate.mode == mode
        assert result.eval_gate.eval_ran is True
        assert result.eval_gate.skipped is False


def test_resolve_eval_gate_defaults_and_override(tmp_path: Path) -> None:
    """resolve_eval_gate: default skip; yaml; CLI override."""
    from zaumzeug.config import DeployConfig, HarnessConfig

    bare = HarnessConfig(name="x")
    assert resolve_eval_gate(bare) == "skip"

    with_yaml = HarnessConfig(name="x", deploy=DeployConfig(eval_gate="warn"))
    assert resolve_eval_gate(with_yaml) == "warn"
    assert resolve_eval_gate(with_yaml, override="block") == "block"

    with pytest.raises(DeployError, match="Unknown eval gate"):
        resolve_eval_gate(bare, override="explode")


def test_apply_eval_gate_direct_api(tmp_path: Path) -> None:
    """apply_eval_gate is the single source of truth used by package_harness."""
    from zaumzeug.config import DeployConfig, EvalConfig, HarnessConfig

    config = HarnessConfig(
        name="example",
        eval=EvalConfig(framework="builtin", valset="data/val.jsonl"),
        deploy=DeployConfig(eval_gate="block"),
    )
    harness_dir = tmp_path / "usr-harnesses" / "example"

    def _ok_eval(harness_name: str, **kwargs):  # noqa: ANN003
        return _fake_eval_result(harness_name, harness_dir, failed=0)

    gate = apply_eval_gate(
        "example",
        config,
        project_root=tmp_path,
        run_eval_fn=_ok_eval,
        output=io.StringIO(),
    )
    assert gate.blocked is False
    assert gate.eval_ran is True
