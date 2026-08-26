"""Haystack run → JSONL trace export and load (E6-S05 / E6.5).

Traces land under ``usr-harnesses/<name>/data/traces/`` and share the valset
field names (``input``, ``actual_output``, optional ``expected_output`` /
``retrieval_context``) so a scored failure can be appended to ``eval.valset``.

Production auto-capture (serve ``Agent.run`` wrap + dataset merge) lives in
:mod:`zaumzeug.eval.ratchet` (E8-S03). This module is the export/load contract
used by ``zaumzeug eval --trace``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "DEFAULT_TRACES_SUBDIR",
    "TRACE_SCHEMA_VERSION",
    "TraceError",
    "append_trace_to_valset",
    "build_trace_row",
    "export_haystack_trace",
    "load_trace_jsonl",
    "traces_dir_for_harness",
    "trace_to_valset_row",
]

TRACE_SCHEMA_VERSION = 1
DEFAULT_TRACES_SUBDIR = Path("data") / "traces"


class TraceError(RuntimeError):
    """Trace export/load failed with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.suggestion = suggestion
        super().__init__(message)


def traces_dir_for_harness(harness_dir: Path | str) -> Path:
    """Return ``<harness_dir>/data/traces`` (Architecture §13.4)."""
    return Path(harness_dir) / DEFAULT_TRACES_SUBDIR


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


def _assistant_text(result: Any) -> str:
    """Extract assistant text from a Haystack ``Agent.run`` result."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, Mapping):
        last = result.get("last_message")
        text = _message_text(last)
        if text:
            return text
        messages = result.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                role = getattr(message, "role", None)
                role_value = getattr(role, "value", role)
                if role_value is None and isinstance(message, Mapping):
                    role_value = message.get("role")
                if str(role_value) == "assistant":
                    msg_text = _message_text(message)
                    if msg_text:
                        return msg_text
    return ""


def _tool_names_from_message(message: Any) -> list[str]:
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


def _tools_called(result: Any) -> list[str] | None:
    if not isinstance(result, Mapping):
        return None
    names: list[str] = []
    messages = result.get("messages")
    if isinstance(messages, list):
        for message in messages:
            names.extend(_tool_names_from_message(message))
    last = result.get("last_message")
    if last is not None:
        names.extend(_tool_names_from_message(last))
    # Preserve order, drop duplicates.
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered or None


def build_trace_row(
    user_input: str,
    haystack_result: Any,
    *,
    expected_output: str | None = None,
    retrieval_context: Sequence[str] | str | None = None,
    agent: str | None = None,
    captured_at: datetime | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one valset-compatible JSONL row from a Haystack run result."""
    stamp = captured_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)

    row: dict[str, Any] = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "input": str(user_input),
        "actual_output": _assistant_text(haystack_result),
        "captured_at": stamp.isoformat(),
    }
    if expected_output is not None:
        row["expected_output"] = str(expected_output)
    if retrieval_context is not None:
        if isinstance(retrieval_context, str):
            row["retrieval_context"] = [retrieval_context]
        else:
            row["retrieval_context"] = [str(item) for item in retrieval_context]
    tools = _tools_called(haystack_result)
    if tools is not None:
        row["tools_called"] = tools
    if agent is not None:
        row["agent"] = str(agent)
    if extra:
        for key, value in extra.items():
            if key in row:
                continue
            row[key] = value
    return row


def export_haystack_trace(
    harness_dir: Path | str,
    user_input: str,
    haystack_result: Any,
    *,
    expected_output: str | None = None,
    retrieval_context: Sequence[str] | str | None = None,
    agent: str | None = None,
    traces_dir: Path | str | None = None,
    filename: str | None = None,
    captured_at: datetime | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Path:
    """Write one Haystack run as JSONL under ``data/traces/`` (AC-1).

    Returns the path of the written ``.jsonl`` file.
    """
    harness_path = Path(harness_dir)
    out_dir = Path(traces_dir) if traces_dir is not None else traces_dir_for_harness(harness_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = captured_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)

    if filename is None:
        # Compact UTC stamp suitable for filenames.
        filename = f"trace-{stamp.strftime('%Y%m%dT%H%M%S%fZ')}.jsonl"
    elif not filename.endswith(".jsonl"):
        filename = f"{filename}.jsonl"

    out_path = out_dir / filename
    row = build_trace_row(
        user_input,
        haystack_result,
        expected_output=expected_output,
        retrieval_context=retrieval_context,
        agent=agent,
        captured_at=stamp,
        extra=extra,
    )
    try:
        out_path.write_text(
            json.dumps(row, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise TraceError(
            f"Cannot write trace file {out_path}: {exc}",
            path=out_path,
            suggestion="Ensure the harness data/traces directory is writable",
        ) from exc
    return out_path


def load_trace_jsonl(path: Path | str) -> list[dict[str, Any]]:
    """Load one or more trace rows from a JSONL file.

    Each row must include ``input`` and ``actual_output`` (the captured turn).
    """
    path = Path(path)
    if not path.is_file():
        raise TraceError(
            f"Trace file not found: {path}",
            path=path,
            suggestion="Pass an existing JSONL under data/traces/ "
            "(see export_haystack_trace)",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TraceError(
            f"Cannot read trace file {path}: {exc}",
            path=path,
        ) from exc

    rows: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceError(
                f"Invalid JSONL in {path} at line {line_no}: {exc}",
                path=path,
            ) from exc
        if not isinstance(row, dict):
            raise TraceError(
                f"Invalid JSONL in {path} at line {line_no}: expected object, "
                f"got {type(row).__name__}",
                path=path,
            )
        if "input" not in row:
            raise TraceError(
                f"Invalid JSONL in {path} at line {line_no}: missing required `input`",
                path=path,
            )
        if "actual_output" not in row:
            raise TraceError(
                f"Invalid JSONL in {path} at line {line_no}: "
                "missing required `actual_output`",
                path=path,
                suggestion="Export traces with export_haystack_trace, or add "
                "actual_output before scoring",
            )
        rows.append(row)

    if not rows:
        raise TraceError(
            f"Trace file is empty: {path}",
            path=path,
            suggestion="Add at least one JSONL row with input and actual_output",
        )
    return rows


def trace_to_valset_row(trace: Mapping[str, Any]) -> dict[str, Any]:
    """Map a trace row to valset fields for append (Journey C).

    Copies ``input`` and optional ``expected_output`` / ``retrieval_context``.
    Does **not** copy ``actual_output`` — set ``expected_output`` to the desired
    answer before appending (or edit the valset row after).
    """
    if "input" not in trace:
        raise TraceError(
            "Trace row missing required `input`",
            suggestion="Use a row produced by export_haystack_trace",
        )
    row: dict[str, Any] = {"input": str(trace["input"])}
    if "expected_output" in trace and trace["expected_output"] is not None:
        row["expected_output"] = str(trace["expected_output"])
    retrieval = trace.get("retrieval_context")
    if retrieval is not None:
        if isinstance(retrieval, str):
            row["retrieval_context"] = [retrieval]
        elif isinstance(retrieval, Sequence) and not isinstance(retrieval, (str, bytes)):
            row["retrieval_context"] = [str(item) for item in retrieval]
        else:
            row["retrieval_context"] = [str(retrieval)]
    return row


def append_trace_to_valset(
    trace_path: Path | str,
    valset_path: Path | str,
) -> int:
    """Append trace row(s) to a valset JSONL file. Returns rows appended."""
    traces = load_trace_jsonl(trace_path)
    valset = Path(valset_path)
    valset.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(trace_to_valset_row(row), ensure_ascii=False) for row in traces
    ]
    prefix = ""
    if valset.is_file() and valset.stat().st_size > 0:
        existing = valset.read_text(encoding="utf-8")
        if not existing.endswith("\n"):
            prefix = "\n"
    with valset.open("a", encoding="utf-8") as handle:
        handle.write(prefix + "\n".join(lines) + "\n")
    return len(lines)
