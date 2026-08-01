# Story: E8-S07 / E8.7
"""E8-S07 — Workflow run reliability and stage transparency (unit)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml
from pydantic import ValidationError

from zaumzeug.config.schemas import RuntimeRetryConfig
from zaumzeug.logging import configure_logging, get_logger, log_request, reset_logging_config
from zaumzeug.runtime.workflow import (
    WorkflowError,
    run_workflow,
    strip_markdown_json_fence,
    validate_json_stage_output,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _scaffold_harness(
    project_root: Path,
    *,
    harness_extra: dict[str, Any] | None = None,
    agent_extra: dict[str, Any] | None = None,
) -> Path:
    harness_dir = project_root / "usr-harnesses" / "example"
    harness_yaml: dict[str, Any] = {
        "name": "example",
        "serve": {"hayhooks": {"port": 1416}},
    }
    if harness_extra:
        harness_yaml.update(harness_extra)
    _write_yaml(harness_dir / "harness.yaml", harness_yaml)
    _write_yaml(
        harness_dir / "workflow.yaml",
        {"entry": "researcher", "stages": [{"agent": "researcher"}]},
    )
    agent_yaml: dict[str, Any] = {
        "name": "researcher",
        "default_model_id": "mock",
        "agent": {"system_prompt": "prompts/system.md"},
    }
    if agent_extra:
        agent_yaml.update(agent_extra)
    agent_dir = harness_dir / "agents" / "researcher"
    _write_yaml(agent_dir / "agent.yaml", agent_yaml)
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
    fixtures = project_root / "tests" / "fixtures" / "responses"
    fixtures.mkdir(parents=True)
    src = REPO_ROOT / "tests" / "fixtures" / "responses" / "harness-fixture.txt"
    (fixtures / "harness-fixture.txt").write_text(
        src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return harness_dir


def _mock_built_agent(side_effect: Any) -> MagicMock:
    built = MagicMock()
    built.input_rewrite_template = None
    built.agent.run.side_effect = side_effect
    return built


def test_e8_s07_ac2_max_attempts_ge_one() -> None:
    """AC-2: schema rejects max_attempts < 1."""
    with pytest.raises(ValidationError):
        RuntimeRetryConfig(max_attempts=0)


def test_e8_s07_ac1_live_generation_error_is_workflow_error(
    tmp_path: Path,
) -> None:
    """AC-1: Agent.run failures become WorkflowError with stage context."""
    project_root = tmp_path / "project"
    _scaffold_harness(project_root)
    built = _mock_built_agent(RuntimeError("provider blew up"))

    with patch(
        "zaumzeug.runtime.workflow.build_agent_bundle",
        return_value=built,
    ):
        with pytest.raises(WorkflowError) as excinfo:
            run_workflow(
                "example",
                user_input="topic",
                project_root=project_root,
            )

    err = excinfo.value
    assert err.harness_name == "example"
    assert err.agent_name == "researcher"
    assert err.stage == "researcher"
    assert err.__cause__ is not None
    assert "provider blew up" in str(err)


def test_e8_s07_ac2_retry_then_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-2: retries Agent.run then fails with attempt count."""
    project_root = tmp_path / "project"
    _scaffold_harness(
        project_root,
        harness_extra={
            "runtime": {
                "retry": {
                    "max_attempts": 3,
                    "initial_delay_s": 0.01,
                    "backoff": 2.0,
                }
            }
        },
    )
    sleeps: list[float] = []
    monkeypatch.setattr(
        "zaumzeug.runtime.workflow.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )
    built = _mock_built_agent(RuntimeError("flaky"))

    with patch(
        "zaumzeug.runtime.workflow.build_agent_bundle",
        return_value=built,
    ):
        with pytest.raises(WorkflowError) as excinfo:
            run_workflow(
                "example",
                user_input="topic",
                project_root=project_root,
            )

    assert built.agent.run.call_count == 3
    assert "3 attempt" in str(excinfo.value)
    assert sleeps == [0.01, 0.02]


def test_e8_s07_ac2_no_retry_on_config_error(tmp_path: Path) -> None:
    """AC-2: config/build errors are not retried."""
    from zaumzeug.runtime.factory import RuntimeFactoryError

    project_root = tmp_path / "project"
    _scaffold_harness(
        project_root,
        harness_extra={
            "runtime": {"retry": {"max_attempts": 5, "initial_delay_s": 0.0}}
        },
    )
    build_calls = 0

    def _boom(*_a: Any, **_k: Any) -> None:
        nonlocal build_calls
        build_calls += 1
        raise RuntimeFactoryError("build failed once")

    with patch("zaumzeug.runtime.workflow.build_agent_bundle", side_effect=_boom):
        with pytest.raises(WorkflowError) as excinfo:
            run_workflow(
                "example",
                user_input="topic",
                project_root=project_root,
            )

    assert build_calls == 1
    assert "attempt" not in str(excinfo.value).lower()
    assert excinfo.value.stage == "researcher"


def test_e8_s07_ac2_default_single_attempt(tmp_path: Path) -> None:
    """AC-2: default max_attempts=1 preserves one-shot behavior."""
    project_root = tmp_path / "project"
    _scaffold_harness(project_root)
    built = _mock_built_agent(RuntimeError("once"))

    with patch(
        "zaumzeug.runtime.workflow.build_agent_bundle",
        return_value=built,
    ):
        with pytest.raises(WorkflowError) as excinfo:
            run_workflow(
                "example",
                user_input="topic",
                project_root=project_root,
            )

    assert built.agent.run.call_count == 1
    assert "1 attempt" in str(excinfo.value)


def test_e8_s07_ac2_build_once_then_retry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: build_agent_bundle once; only agent.run is retried."""
    project_root = tmp_path / "project"
    _scaffold_harness(
        project_root,
        harness_extra={
            "runtime": {"retry": {"max_attempts": 3, "initial_delay_s": 0.0}}
        },
    )
    monkeypatch.setattr("zaumzeug.runtime.workflow.time.sleep", lambda _s: None)
    built = _mock_built_agent(RuntimeError("flaky"))
    build_calls = 0

    def _build(*_a: Any, **_k: Any) -> MagicMock:
        nonlocal build_calls
        build_calls += 1
        return built

    with patch("zaumzeug.runtime.workflow.build_agent_bundle", side_effect=_build):
        with pytest.raises(WorkflowError):
            run_workflow(
                "example",
                user_input="topic",
                project_root=project_root,
            )

    assert build_calls == 1
    assert built.agent.run.call_count == 3


def test_e8_s07_ac3_stage_log_request_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3: stage lifecycle logs include structured stage key at INFO."""
    reset_logging_config()
    configure_logging(force=True)
    monkeypatch.setenv("HARNESS_LOG_LEVEL", "INFO")
    configure_logging(force=True)

    project_root = tmp_path / "project"
    _scaffold_harness(project_root)

    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = get_logger("runtime.workflow")
    handler = _Capture()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Also assert log_request accepts stage on the structured key list.
    log_request(
        get_logger("test"),
        "probe",
        harness="h",
        agent="a",
        model_id="m",
        stage="s",
        level=logging.INFO,
    )

    result = run_workflow(
        "example",
        user_input="topic",
        project_root=project_root,
    )
    assert result.final_output

    stage_records = [
        r for r in records if getattr(r, "stage", None) == "researcher"
    ]
    messages = [r.getMessage() for r in stage_records]
    assert any("start" in m for m in messages)
    assert any("success" in m for m in messages)
    for record in stage_records:
        assert record.harness == "example"
        assert record.agent == "researcher"
        assert record.stage == "researcher"
        assert record.model_id == "mock"


def test_e8_s07_ac4_invalid_json_retries_then_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-4: invalid JSON output is retryable and becomes WorkflowError."""
    project_root = tmp_path / "project"
    _scaffold_harness(
        project_root,
        harness_extra={
            "runtime": {"retry": {"max_attempts": 2, "initial_delay_s": 0.0}}
        },
        agent_extra={"output": {"format": "json"}},
    )
    monkeypatch.setattr("zaumzeug.runtime.workflow.time.sleep", lambda _s: None)

    def _not_json(**_kwargs: Any) -> dict[str, Any]:
        msg = MagicMock()
        msg.text = "not-json"
        return {"last_message": msg}

    built = _mock_built_agent(_not_json)

    with patch(
        "zaumzeug.runtime.workflow.build_agent_bundle",
        return_value=built,
    ):
        with pytest.raises(WorkflowError) as excinfo:
            run_workflow(
                "example",
                user_input="topic",
                project_root=project_root,
            )

    assert built.agent.run.call_count == 2
    assert "2 attempt" in str(excinfo.value)
    assert excinfo.value.stage == "researcher"


def test_e8_s07_ac4_strips_markdown_fence() -> None:
    """AC-4: markdown fences are stripped before json.loads."""
    assert strip_markdown_json_fence('```json\n{"ok": true}\n```') == '{"ok": true}'
    validate_json_stage_output('```json\n{"ok": true}\n```')


def test_e8_s07_ac4_empty_text_fails_json() -> None:
    """AC-4: empty assistant text fails JSON validation."""
    with pytest.raises(ValueError, match="empty"):
        validate_json_stage_output("")
    with pytest.raises(ValueError, match="empty"):
        validate_json_stage_output("   ")


def test_e8_s07_ac4_no_output_config_skips_validation(tmp_path: Path) -> None:
    """AC-4: agents without output config skip JSON validation."""
    project_root = tmp_path / "project"
    _scaffold_harness(project_root)

    def _plain(**_kwargs: Any) -> dict[str, Any]:
        msg = MagicMock()
        msg.text = "plain text, not json"
        return {"last_message": msg}

    built = _mock_built_agent(_plain)

    with patch(
        "zaumzeug.runtime.workflow.build_agent_bundle",
        return_value=built,
    ):
        result = run_workflow(
            "example",
            user_input="topic",
            project_root=project_root,
        )

    assert result.final_output == "plain text, not json"
