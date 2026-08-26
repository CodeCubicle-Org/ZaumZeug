"""Production trace → dataset ratchet (E8-S03 / E8.3).

Captures Haystack ``Agent.run`` results in production (serve path), writes JSONL
under ``data/traces/``, and merges selected traces into ``data/val.jsonl`` /
``data/train.jsonl`` so Journey C can re-eval, re-compile, and re-deploy.

Haystack ``track_stats`` is recorded as structured metadata on each trace row.
OpenTelemetry is an in-memory stub (no ``opentelemetry`` dependency) until a
real exporter is wired.

Capture is **opt-in**: ``eval.trace_capture.enabled: true`` or
``ZAUMZEUG_TRACE_CAPTURE=1``. Failures in the hook never fail the user request.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zaumzeug.eval.trace import (
    TraceError,
    append_trace_to_valset,
    export_haystack_trace,
    load_trace_jsonl,
    trace_to_valset_row,
)
from zaumzeug.logging import get_logger

__all__ = [
    "TRACE_CAPTURE_ENV",
    "DatasetMergeResult",
    "OTelTraceStub",
    "ProductionTraceHook",
    "StubSpan",
    "append_trace_to_train",
    "haystack_track_stats",
    "install_production_trace_hook",
    "merge_traces_into_datasets",
    "trace_capture_enabled",
]

TRACE_CAPTURE_ENV = "ZAUMZEUG_TRACE_CAPTURE"
_HOOK_MARKER = "_zaumzeug_production_trace_hook"

_logger = get_logger("eval.ratchet")


@dataclass
class StubSpan:
    """One in-memory span recorded by :class:`OTelTraceStub`."""

    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    ended: bool = False

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[str(key)] = value

    def end(self) -> None:
        self.ended = True

    def __enter__(self) -> StubSpan:
        return self

    def __exit__(self, *exc: object) -> bool:
        self.end()
        return False


class OTelTraceStub:
    """No-op OpenTelemetry tracer (no ``opentelemetry-sdk``).

    Records spans in memory so production traces can attach span ids without
    taking an OTel dependency. Replace later with a real exporter.
    """

    def __init__(self) -> None:
        self.spans: list[StubSpan] = []

    def start_span(
        self,
        name: str,
        attributes: Mapping[str, Any] | None = None,
    ) -> StubSpan:
        span = StubSpan(name=str(name), attributes=dict(attributes or {}))
        self.spans.append(span)
        return span

    def as_dict(self) -> dict[str, Any]:
        return {
            "stub": True,
            "spans": [
                {
                    "name": span.name,
                    "attributes": dict(span.attributes),
                    "ended": span.ended,
                }
                for span in self.spans
            ],
        }


def haystack_track_stats(result: Any) -> dict[str, Any]:
    """Collect lightweight Haystack ``Agent.run`` stats for a trace row.

    Haystack 2.x does not expose a public ``track_stats`` API on ``Agent``;
    this helper records message counts and tool names from the run result so
    the JSONL row is self-describing without OTel.
    """
    stats: dict[str, Any] = {"source": "haystack"}
    if not isinstance(result, Mapping):
        stats["result_type"] = type(result).__name__
        return stats

    messages = result.get("messages")
    if isinstance(messages, list):
        stats["message_count"] = len(messages)
    names: list[str] = []
    if isinstance(messages, list):
        for message in messages:
            names.extend(_tool_names(message))
    last = result.get("last_message")
    if last is not None:
        stats["has_last_message"] = True
        names.extend(_tool_names(last))
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    if ordered:
        stats["tools_called"] = ordered
    return stats


def _tool_names(message: Any) -> list[str]:
    names: list[str] = []
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls is None and isinstance(message, Mapping):
        tool_calls = message.get("tool_calls")
    if not tool_calls:
        return names
    for call in tool_calls:
        name = getattr(call, "tool_name", None) or getattr(call, "name", None)
        if name is None and isinstance(call, Mapping):
            name = call.get("tool_name") or call.get("name")
            if name is None:
                fn = call.get("function")
                if isinstance(fn, Mapping):
                    name = fn.get("name")
        if name:
            names.append(str(name))
    return names


def trace_capture_enabled(
    eval_config: Any | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Return True when production trace capture should run.

    Env ``ZAUMZEUG_TRACE_CAPTURE`` wins when set (``1``/``true``/``yes``/``on``
    enable; ``0``/``false``/``no``/``off`` disable). Otherwise
    ``eval.trace_capture.enabled`` is used. Default is off.
    """
    environ = env if env is not None else os.environ
    raw = str(environ.get(TRACE_CAPTURE_ENV, "")).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    capture = getattr(eval_config, "trace_capture", None) if eval_config else None
    if capture is None:
        return False
    return bool(getattr(capture, "enabled", False))


def _message_text(message: Any) -> str | None:
    if message is None:
        return None
    text = getattr(message, "text", None)
    if text:
        return str(text)
    if isinstance(message, Mapping):
        content = message.get("content") or message.get("text")
        if content:
            return str(content)
    return None


def _role_value(message: Any) -> str:
    role = getattr(message, "role", None)
    value = getattr(role, "value", role)
    if value is None and isinstance(message, Mapping):
        value = message.get("role")
    return str(value or "").lower()


def user_input_from_run_args(*args: Any, **kwargs: Any) -> str:
    """Best-effort user turn from ``Agent.run(messages=...)``."""
    messages = kwargs.get("messages")
    if messages is None and args:
        messages = args[0]
    if not messages:
        return ""
    sequence = list(messages)
    for message in reversed(sequence):
        if _role_value(message).endswith("user"):
            text = _message_text(message)
            if text:
                return text
    text = _message_text(sequence[-1])
    return text or ""


class ProductionTraceHook:
    """Wrap ``Agent.run`` and export each turn under ``data/traces/``."""

    def __init__(
        self,
        harness_dir: Path | str,
        *,
        agent: str | None = None,
        otel: OTelTraceStub | None = None,
    ) -> None:
        self.harness_dir = Path(harness_dir)
        self.agent = agent
        self.otel = otel if otel is not None else OTelTraceStub()
        self.last_trace_path: Path | None = None
        self.export_errors: list[str] = []

    def install(self, agent: Any) -> Any:
        """Wrap ``agent.run`` once. Returns *agent*."""
        original = getattr(agent, "run", None)
        if original is None or not callable(original):
            raise TraceError(
                "Cannot install production trace hook: agent has no callable run()",
                suggestion="Pass a Haystack Agent (or test double) with a run method",
            )
        if getattr(original, _HOOK_MARKER, False) is self:
            return agent

        hook = self

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            span = hook.otel.start_span(
                "haystack.agent.run",
                attributes={"agent": hook.agent or ""},
            )
            try:
                with span:
                    result = original(*args, **kwargs)
            except Exception:
                span.end()
                raise
            hook._export_quietly(result, *args, **kwargs)
            return result

        setattr(wrapped, _HOOK_MARKER, self)
        agent.run = wrapped
        return agent

    def _export_quietly(self, result: Any, *args: Any, **kwargs: Any) -> None:
        try:
            user_input = user_input_from_run_args(*args, **kwargs)
            extra = {
                "source": "production",
                "track_stats": haystack_track_stats(result),
                "otel": self.otel.as_dict(),
            }
            self.last_trace_path = export_haystack_trace(
                self.harness_dir,
                user_input,
                result,
                agent=self.agent,
                extra=extra,
            )
        except Exception as exc:  # noqa: BLE001 — never fail the live request
            message = f"Production trace export failed: {exc}"
            self.export_errors.append(message)
            _logger.warning(message)


def install_production_trace_hook(
    agent: Any,
    harness_dir: Path | str,
    *,
    agent_name: str | None = None,
    otel: OTelTraceStub | None = None,
) -> ProductionTraceHook:
    """Install a :class:`ProductionTraceHook` on *agent* and return the hook."""
    hook = ProductionTraceHook(harness_dir, agent=agent_name, otel=otel)
    hook.install(agent)
    return hook


@dataclass(frozen=True, slots=True)
class DatasetMergeResult:
    """Counts from :func:`merge_traces_into_datasets`."""

    val_appended: int
    train_appended: int


def append_trace_to_train(
    trace_path: Path | str,
    train_path: Path | str,
    *,
    expected_output: str | None = None,
    skip_without_expected: bool = True,
) -> int:
    """Append trace row(s) to a compile train JSONL. Returns rows appended.

    Each line is ``{"question": ..., "answer": ...}``. Rows without an expected
    answer are skipped when *skip_without_expected* is true.
    """
    traces = load_trace_jsonl(trace_path)
    path = Path(train_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    from zaumzeug.eval.gepa_bridge import eval_row_to_train_row

    lines: list[str] = []
    for row in traces:
        mapped = dict(row)
        if expected_output is not None:
            mapped["expected_output"] = expected_output
        train_row = eval_row_to_train_row(mapped)
        if train_row is None:
            if skip_without_expected:
                continue
            raise TraceError(
                "Trace row has no expected_output; cannot append to train.jsonl",
                path=path,
                suggestion="Pass expected_output=... or set it on the trace row",
            )
        lines.append(json.dumps(train_row, ensure_ascii=False))

    if not lines:
        return 0

    prefix = ""
    if path.is_file() and path.stat().st_size > 0:
        existing = path.read_text(encoding="utf-8")
        if not existing.endswith("\n"):
            prefix = "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + "\n".join(lines) + "\n")
    return len(lines)


def merge_traces_into_datasets(
    trace_path: Path | str,
    *,
    valset_path: Path | str | None = None,
    train_path: Path | str | None = None,
    expected_output: str | None = None,
) -> DatasetMergeResult:
    """Append a captured trace to valset and/or train JSONL (AC-1).

    When *expected_output* is set, it overlays the gold answer on every row
    before append (needed when the production turn had no gold).
    """
    val_appended = 0
    train_appended = 0

    if valset_path is not None:
        if expected_output is not None:
            traces = load_trace_jsonl(trace_path)
            valset = Path(valset_path)
            valset.parent.mkdir(parents=True, exist_ok=True)
            overlay_lines = []
            for row in traces:
                mapped = dict(row)
                mapped["expected_output"] = expected_output
                overlay_lines.append(
                    json.dumps(trace_to_valset_row(mapped), ensure_ascii=False)
                )
            prefix = ""
            if valset.is_file() and valset.stat().st_size > 0:
                existing = valset.read_text(encoding="utf-8")
                if not existing.endswith("\n"):
                    prefix = "\n"
            with valset.open("a", encoding="utf-8") as handle:
                handle.write(prefix + "\n".join(overlay_lines) + "\n")
            val_appended = len(overlay_lines)
        else:
            val_appended = append_trace_to_valset(trace_path, valset_path)

    if train_path is not None:
        train_appended = append_trace_to_train(
            trace_path,
            train_path,
            expected_output=expected_output,
        )

    return DatasetMergeResult(
        val_appended=val_appended,
        train_appended=train_appended,
    )
