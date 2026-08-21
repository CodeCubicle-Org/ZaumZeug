# Story: E2-S01 / E2.1
"""E2-S01 — Pydantic config schemas (harness.yaml validation)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zaumzeug.config import ConfigValidationError, HarnessConfig, load_agent_config, load_harness

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

    # Nested Phase 4 key under serve also gets a phase hint.
    nested = dict(PHASE1_MINIMAL)
    nested["serve"] = {"hayhooks": {"port": 1416}, "a2a": {"enabled": True}}
    nested_path = _write_yaml(tmp_path / "harness-a2a.yaml", nested)

    with pytest.raises(ConfigValidationError) as nested_info:
        load_harness(nested_path)

    nested_msg = str(nested_info.value)
    assert "a2a" in nested_msg
    assert "Phase 4" in nested_msg


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


def test_e3_s03_ac5_unknown_builtin_id_fails_with_list(tmp_path: Path) -> None:
    """AC-5: Unknown builtin tool id fails validation with available ids for Phase 1."""
    path = _write_yaml(
        tmp_path / "agent.yaml",
        {
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": {"builtin": ["not_a_real_tool"]},
        },
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_agent_config(path)

    message = str(exc_info.value)
    assert "not_a_real_tool" in message
    assert "web_fetch" in message
    assert "available" in message.lower()


def test_e7_s07_ac3_unknown_builtin_phase3_list(tmp_path: Path) -> None:
    """AC-3: Unknown builtin IDs fail with the Phase 4 available list."""
    path = _write_yaml(
        tmp_path / "agent.yaml",
        {
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": {"builtin": ["not_a_real_tool"]},
        },
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_agent_config(path)

    message = str(exc_info.value)
    assert "not_a_real_tool" in message
    assert "Phase 4" in message
    assert "web_fetch" in message
    assert "calculator" in message
    assert "read_file" in message
    assert "search_docs" in message

    ok = _write_yaml(
        tmp_path / "ok-agent.yaml",
        {
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": {"builtin": ["web_fetch", "calculator", "read_file"]},
        },
    )
    config = load_agent_config(ok)
    assert config.tools is not None
    assert config.tools.builtin == ["web_fetch", "calculator", "read_file"]


# --- E4-S02a / E4.2 ---


def test_e4_s02a_ac1_phase2_compile_schema_validates(tmp_path: Path) -> None:
    """AC-1: Phase 2 compile section validates via extended Pydantic schemas."""
    from zaumzeug.config import CompileConfig

    path = _write_yaml(
        tmp_path / "agent.yaml",
        {
            "name": "researcher",
            "default_model_id": "mock",
            "agent": {"system_prompt": "prompts/system.md"},
            "compile": {
                "module": "modules.researcher:ResearchModule",
                "task_model_id": "mock",
                "reflection_model_id": "strong",
                "trainset": "data/train.jsonl",
                "valset": "data/val.jsonl",
                "budget": "medium",
            },
        },
    )

    config = load_agent_config(path)

    assert config.compile is not None
    assert isinstance(config.compile, CompileConfig)
    assert config.compile.module == "modules.researcher:ResearchModule"
    assert config.compile.task_model_id == "mock"
    assert config.compile.reflection_model_id == "strong"
    assert config.compile.auto == "medium"  # budget alias
    assert config.compile.optimizer == "dspy.GEPA"

    # Missing module fails schema validation.
    bad = _write_yaml(
        tmp_path / "bad-agent.yaml",
        {
            "name": "researcher",
            "compile": {"enabled": True, "trainset": "data/train.jsonl"},
        },
    )
    with pytest.raises(ConfigValidationError) as exc_info:
        load_agent_config(bad)
    assert "module" in str(exc_info.value).lower()

    # Conflicting budget knobs rejected.
    conflict = _write_yaml(
        tmp_path / "conflict-agent.yaml",
        {
            "name": "researcher",
            "compile": {
                "module": "modules.researcher:ResearchModule",
                "auto": "light",
                "max_metric_calls": 10,
            },
        },
    )
    with pytest.raises(ConfigValidationError) as conflict_info:
        load_agent_config(conflict)
    assert "budget" in str(conflict_info.value).lower() or "exactly one" in str(
        conflict_info.value
    ).lower()


# --- E7-S01 / E7.1 ---


def test_e7_s01_mcp_schema_and_mcp_port(tmp_path: Path) -> None:
    """tools.mcp entries and serve.hayhooks.mcp_port validate (E7-S01)."""
    from zaumzeug.config.schemas import McpServerConfig

    path = _write_yaml(
        tmp_path / "agent.yaml",
        {
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": {
                "mcp": [
                    {
                        "name": "filesystem",
                        "command": "uv",
                        "args": ["run", "mcp-server-filesystem", "/workspace"],
                    }
                ]
            },
        },
    )
    config = load_agent_config(path)
    assert config.tools is not None
    assert config.tools.mcp is not None
    assert len(config.tools.mcp) == 1
    entry = config.tools.mcp[0]
    assert isinstance(entry, McpServerConfig)
    assert entry.name == "filesystem"
    assert entry.command == "uv"

    harness_path = _write_yaml(
        tmp_path / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416, "mcp_port": 1417}}},
    )
    harness = load_harness(harness_path)
    assert harness.serve is not None
    assert harness.serve.hayhooks is not None
    assert harness.serve.hayhooks.mcp_port == 1417

    both = _write_yaml(
        tmp_path / "bad-agent.yaml",
        {
            "name": "researcher",
            "tools": {
                "mcp": [{"name": "broken", "command": "uv", "url": "http://localhost:9/mcp"}]
            },
        },
    )
    with pytest.raises(ConfigValidationError) as exc_info:
        load_agent_config(both)
    assert "command" in str(exc_info.value).lower() or "url" in str(exc_info.value).lower()


def test_e7_s04_chainlit_flag_validates(tmp_path: Path) -> None:
    """serve.hayhooks.chainlit is unblocked (E7-S04); default is false."""
    default_path = _write_yaml(
        tmp_path / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    default = load_harness(default_path)
    assert default.serve is not None
    assert default.serve.hayhooks is not None
    assert default.serve.hayhooks.chainlit is False

    enabled_path = _write_yaml(
        tmp_path / "harness-chat.yaml",
        {
            "name": "example",
            "serve": {"hayhooks": {"port": 1416, "chainlit": True}},
        },
    )
    enabled = load_harness(enabled_path)
    assert enabled.serve is not None
    assert enabled.serve.hayhooks is not None
    assert enabled.serve.hayhooks.chainlit is True


def test_e7_s05_acp_schema_unblocked(tmp_path: Path) -> None:
    """serve.acp is unblocked (E7-S05); omitted section stays None."""
    from zaumzeug.config.schemas import AcpConfig

    default_path = _write_yaml(
        tmp_path / "harness.yaml",
        {"name": "example", "serve": {"hayhooks": {"port": 1416}}},
    )
    default = load_harness(default_path)
    assert default.serve is not None
    assert default.serve.acp is None

    enabled_path = _write_yaml(
        tmp_path / "harness-acp.yaml",
        {
            "name": "example",
            "serve": {
                "hayhooks": {"port": 1416},
                "acp": {"enabled": True},
            },
        },
    )
    enabled = load_harness(enabled_path)
    assert enabled.serve is not None
    assert enabled.serve.acp is not None
    assert isinstance(enabled.serve.acp, AcpConfig)
    assert enabled.serve.acp.enabled is True


def test_e7_s02_custom_schema_allows_module_paths(tmp_path: Path) -> None:
    """tools.custom module paths validate (E7-S02); empty entries are rejected."""
    path = _write_yaml(
        tmp_path / "agent.yaml",
        {
            "name": "researcher",
            "agent": {"system_prompt": "prompts/system.md"},
            "tools": {"custom": ["tools/search_docs.py", "tools.calculator:calculator"]},
        },
    )
    config = load_agent_config(path)
    assert config.tools is not None
    assert config.tools.custom == [
        "tools/search_docs.py",
        "tools.calculator:calculator",
    ]

    blank = _write_yaml(
        tmp_path / "blank-custom.yaml",
        {
            "name": "researcher",
            "tools": {"custom": ["  "]},
        },
    )
    with pytest.raises(ConfigValidationError) as exc_info:
        load_agent_config(blank)
    assert "custom" in str(exc_info.value).lower()


def test_e8_s02_no_serve_auth_in_schema(tmp_path: Path) -> None:
    """E8-S02: ``serve.auth`` is not a v1 field — proxy-only auth, extra keys forbidden."""
    data = dict(PHASE1_MINIMAL)
    data["serve"] = {
        "hayhooks": {"port": 1416},
        "auth": {"bearer": True},
    }
    path = _write_yaml(tmp_path / "harness.yaml", data)

    with pytest.raises(ConfigValidationError) as exc_info:
        load_harness(path)

    message = str(exc_info.value).lower()
    assert "auth" in message
    assert "extra" in message or "forbidden" in message or "not permitted" in message
