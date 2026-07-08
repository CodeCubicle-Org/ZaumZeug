"""``zaumzeug serve --dry-run`` report formatting."""

from __future__ import annotations

import json
from dataclasses import asdict

from zaumzeug.serve.validate import ServeValidationResult


def format_dry_run(result: ServeValidationResult) -> str:
    """Human-readable dry-run summary."""
    lines: list[str] = [f"Serve dry-run: {result.harness_name}"]

    if result.port is not None:
        lines.append(f"  port: {result.port}")
    if result.entry is not None:
        lines.append(f"  entry agent: {result.entry.agent_name}")
    if result.model_id is not None:
        lines.append(f"  model_id: {result.model_id}")
    if result.entry is not None:
        lines.append(
            f"  runtime: {result.entry.source.value} at {result.entry.path}"
        )
    if result.tools is not None:
        if result.tools:
            lines.append(f"  tools: {', '.join(result.tools)}")
        else:
            lines.append("  tools: (none)")

    failures = [check for check in result.checks if check.severity == "fail"]
    if failures:
        lines.append("  errors:")
        for check in failures:
            lines.append(f"    - {check.message}")
    elif result.ok:
        lines.append("  status: ok")

    return "\n".join(lines)


def dry_run_to_dict(result: ServeValidationResult) -> dict[str, object]:
    """Machine-readable dry-run payload."""
    payload: dict[str, object] = {
        "ok": result.ok,
        "exit_code": result.exit_code,
        "harness": result.harness_name,
        "checks": [asdict(check) for check in result.checks],
    }
    if result.port is not None:
        payload["port"] = result.port
    if result.entry is not None:
        payload["entry_agent"] = result.entry.agent_name
        payload["runtime_source"] = result.entry.source.value
        payload["runtime_path"] = str(result.entry.path)
    if result.model_id is not None:
        payload["model_id"] = result.model_id
    if result.tools is not None:
        payload["tools"] = list(result.tools)
    return payload


def dry_run_to_json(result: ServeValidationResult) -> str:
    return json.dumps(dry_run_to_dict(result), indent=2, sort_keys=True)
