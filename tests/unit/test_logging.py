# Story: E2-S06 / E2.6
"""E2-S06 — Structured logging."""

from __future__ import annotations

import logging

import pytest

from zaumzeug.logging import (
    LOGGER_NAME,
    HARNESS_LOG_LEVEL_ENV,
    SecretRedactingFilter,
    StructuredFormatter,
    configure_logging,
    get_logger,
    log_request,
    redact_secrets,
    reset_logging_config,
    resolve_log_level,
)


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    reset_logging_config()
    logging.getLogger("haystack").setLevel(logging.WARNING)


def test_e2_s06_ac1_verbose_flag_sets_debug_level() -> None:
    """AC-1: --verbose enables SDK + Haystack DEBUG logging."""
    level = configure_logging(verbose=True, force=True)
    assert level == logging.DEBUG
    assert resolve_log_level(verbose=True) == logging.DEBUG
    assert logging.getLogger(LOGGER_NAME).level == logging.DEBUG
    assert logging.getLogger("haystack").level == logging.DEBUG


def test_e2_s06_ac2_harness_log_level_env_equivalent(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-2: HARNESS_LOG_LEVEL=DEBUG is equivalent to --verbose."""
    monkeypatch.setenv(HARNESS_LOG_LEVEL_ENV, "DEBUG")
    env_level = resolve_log_level(verbose=False)
    verbose_level = resolve_log_level(verbose=True)
    assert env_level == logging.DEBUG
    assert verbose_level == logging.DEBUG

    configured = configure_logging(verbose=False, force=True)
    assert configured == logging.DEBUG
    assert logging.getLogger(LOGGER_NAME).level == logging.DEBUG
    assert logging.getLogger("haystack").level == logging.DEBUG


def test_e2_s06_ac3_log_record_includes_model_tool_artifact() -> None:
    """AC-3: request logs include model_id, tool, and artifact_path."""
    configure_logging(verbose=True, force=True)
    logger = get_logger("test")

    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger.addHandler(_Capture())

    log_request(
        logger,
        "routing request",
        model_id="gpt-4",
        tool="web_search",
        artifact_path="artifacts/current",
    )

    assert len(records) == 1
    record = records[0]
    assert record.model_id == "gpt-4"
    assert record.tool == "web_search"
    assert record.artifact_path == "artifacts/current"

    handler = logging.getLogger(LOGGER_NAME).handlers[0]
    formatted = handler.formatter.format(record)
    assert "model_id=gpt-4" in formatted
    assert "tool=web_search" in formatted
    assert "artifact_path=artifacts/current" in formatted


def test_e2_s06_ac4_api_keys_redacted_in_logs() -> None:
    """AC-4: API keys and bearer tokens are redacted from log output."""
    secret = "sk-abcdefghijklmnopqrstuvwxyz1234567890"
    assert secret not in redact_secrets(f"provider key={secret}")
    assert secret not in redact_secrets(f"Authorization: Bearer {secret}")
    assert secret not in redact_secrets('api_key="sk-shortbutstillsecret"')

    configure_logging(verbose=True, force=True)
    logger = get_logger("test")
    handler = logging.getLogger(LOGGER_NAME).handlers[0]
    record = logging.LogRecord(
        name=logger.name,
        level=logging.DEBUG,
        pathname=__file__,
        lineno=1,
        msg="calling provider key=%s",
        args=(secret,),
        exc_info=None,
    )
    for flt in handler.filters:
        flt.filter(record)
    formatted = handler.formatter.format(record)
    assert secret not in formatted
    assert "***REDACTED***" in formatted

    record = logging.LogRecord(
        name=logger.name,
        level=logging.DEBUG,
        pathname=__file__,
        lineno=1,
        msg="configured api_key=%s",
        args=("sk-anothersecretvalue12345",),
        exc_info=None,
    )
    SecretRedactingFilter().filter(record)
    assert StructuredFormatter("%(message)s").format(record) == (
        "configured api_key=***REDACTED***"
    )
