# Story: E2-S01 / E2.1
"""E2-S01 — Pydantic config schemas (harness.yaml validation)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zaumzeug.config import ConfigValidationError, HarnessConfig, load_harness

# Architecture §6.6 — Phase 1 minimal harness.yaml
PHASE1_MINIMAL: dict = {
    "name": "example",
    "description": (
        "Reference research harness (multi-agent layout; one workflow stage in Phase 1)"
    ),
    "models": "models.yaml",
    "serve": {
        "hayhooks": {
            "port": 1416,
        },
    },
}


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_e2_s01_ac1_invalid_yaml_field_errors(tmp_path: Path) -> None:
    """AC-1: Invalid harness.yaml fails with Pydantic field-level errors."""
    path = _write_yaml(
        tmp_path / "harness.yaml",
        {
            "name": "example",
            "serve": {
                "hayhooks": {
                    "port": "not-an-int",
                },
            },
        },
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_harness(path)

    err = exc_info.value
    assert err.errors, "expected field-level error details"
    fields = {e["field"] for e in err.errors}
    assert any("port" in f for f in fields), f"expected port in fields, got {fields}"
    assert any("int" in e["msg"].lower() or "type" in e["type"] for e in err.errors)


def test_e2_s01_ac2_phase1_minimal_valid(tmp_path: Path) -> None:
    """AC-2: Phase 1 minimal example from Architecture §6.6 passes validation."""
    path = _write_yaml(tmp_path / "harness.yaml", PHASE1_MINIMAL)

    config = load_harness(path)

    assert isinstance(config, HarnessConfig)
    assert config.name == "example"
    assert config.description is not None
    assert config.serve is not None
    assert config.serve.hayhooks is not None
    assert config.serve.hayhooks.port == 1416
    assert config.models is not None
    assert Path(config.models).is_absolute()
    assert Path(config.models).name == "models.yaml"


def test_e2_s01_ac3_unknown_key_phase_hint(tmp_path: Path) -> None:
    """AC-3: Unknown sections for current phase fail with a phase hint."""
    data = dict(PHASE1_MINIMAL)
    data["compile"] = {"enabled": True}
    path = _write_yaml(tmp_path / "harness.yaml", data)

    with pytest.raises(ConfigValidationError) as exc_info:
        load_harness(path)

    message = str(exc_info.value)
    assert "compile" in message
    assert "Phase 2" in message

    # Nested Phase 3 key under serve also gets a phase hint.
    nested = dict(PHASE1_MINIMAL)
    nested["serve"] = {"hayhooks": {"port": 1416}, "acp": {"enabled": True}}
    nested_path = _write_yaml(tmp_path / "harness-acp.yaml", nested)

    with pytest.raises(ConfigValidationError) as nested_info:
        load_harness(nested_path)

    nested_msg = str(nested_info.value)
    assert "acp" in nested_msg
    assert "Phase 3" in nested_msg


def test_e2_s01_ac4_error_includes_path_and_field(tmp_path: Path) -> None:
    """AC-4: Error clarity — message includes file path and field name (PRD §11)."""
    path = _write_yaml(
        tmp_path / "harness.yaml",
        {
            # missing required ``name``
            "description": "broken",
            "unknown_section": True,
        },
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_harness(path)

    err = exc_info.value
    message = str(err)
    assert str(path) in message
    assert err.field is not None
    assert err.field in message
    # Either missing ``name`` or forbidden ``unknown_section`` — field must be named.
    assert any(
        token in message
        for token in ("name", "unknown_section")
    ), f"expected a field name in message: {message}"
