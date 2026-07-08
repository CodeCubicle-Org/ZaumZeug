"""Centralized structured logging for ZaumZeug CLI and runtime."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

LOGGER_NAME = "zaumzeug"
HARNESS_LOG_LEVEL_ENV = "HARNESS_LOG_LEVEL"
_REDACTED = "***REDACTED***"

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)(['\"]?)([^\s'\"]+)"),
    re.compile(r"(?i)(bearer\s+)([^\s]+)"),
)

_STRUCTURED_KEYS = ("model_id", "tool", "artifact_path", "harness", "agent")

_configured = False


class SecretRedactingFilter(logging.Filter):
    """Redact API keys and bearer tokens from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except (TypeError, ValueError):
            message = str(record.msg)
        record.msg = redact_secrets(message)
        record.args = ()
        for key, value in record.__dict__.items():
            if key in _STRUCTURED_KEYS:
                continue
            if isinstance(value, str) and key not in {"msg", "message"}:
                setattr(record, key, redact_secrets(value))
        return True


class StructuredFormatter(logging.Formatter):
    """Append structured request context fields when present on the record."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = [
            f"{key}={getattr(record, key)}"
            for key in _STRUCTURED_KEYS
            if getattr(record, key, None) is not None
        ]
        if extras:
            return f"{base} [{' '.join(extras)}]"
        return base


def redact_secrets(text: str) -> str:
    """Replace API keys and bearer tokens with a redaction placeholder."""
    result = _SECRET_PATTERNS[0].sub(_REDACTED, text)

    def _redact_key_match(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}{_REDACTED}"

    result = _SECRET_PATTERNS[1].sub(_redact_key_match, result)

    def _redact_bearer(match: re.Match[str]) -> str:
        return f"{match.group(1)}{_REDACTED}"

    return _SECRET_PATTERNS[2].sub(_redact_bearer, result)


def resolve_log_level(
    *,
    verbose: bool = False,
    environ: dict[str, str] | os._Environ | None = None,
) -> int:
    """Resolve effective log level from ``--verbose`` or ``HARNESS_LOG_LEVEL``."""
    if verbose:
        return logging.DEBUG

    env = environ if environ is not None else os.environ
    level_name = env.get(HARNESS_LOG_LEVEL_ENV, "").strip().upper()
    if not level_name:
        return logging.WARNING

    return getattr(logging, level_name, logging.WARNING)


def _configure_haystack_logging() -> None:
    try:
        from haystack import logging as haystack_logging

        haystack_logging.configure_logging()
    except ImportError:
        pass


def configure_logging(*, verbose: bool = False, force: bool = False) -> int:
    """Configure SDK and Haystack loggers. Returns the effective log level."""
    global _configured

    level = resolve_log_level(verbose=verbose)
    logger = logging.getLogger(LOGGER_NAME)

    if force or not _configured:
        handler = logging.StreamHandler()
        handler.setFormatter(
            StructuredFormatter("%(levelname)s %(name)s: %(message)s"),
        )
        handler.addFilter(SecretRedactingFilter())
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.propagate = False
        _configured = True

    logger.setLevel(level)
    logging.getLogger("haystack").setLevel(level)
    if level <= logging.DEBUG:
        _configure_haystack_logging()

    return level


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under the ZaumZeug logging namespace."""
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(LOGGER_NAME)


def log_request(
    logger: logging.Logger,
    message: str,
    *,
    model_id: str | None = None,
    tool: str | None = None,
    artifact_path: str | None = None,
    harness: str | None = None,
    agent: str | None = None,
    level: int = logging.DEBUG,
) -> None:
    """Log a request-scoped message with structured routing context."""
    extra: dict[str, Any] = {}
    if model_id is not None:
        extra["model_id"] = model_id
    if tool is not None:
        extra["tool"] = tool
    if artifact_path is not None:
        extra["artifact_path"] = artifact_path
    if harness is not None:
        extra["harness"] = harness
    if agent is not None:
        extra["agent"] = agent
    logger.log(level, message, extra=extra)


def reset_logging_config() -> None:
    """Reset module logging state (for tests)."""
    global _configured
    _configured = False
    logging.getLogger(LOGGER_NAME).handlers.clear()
