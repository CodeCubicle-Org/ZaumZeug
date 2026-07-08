# CLI reference

ZaumZeug command-line interface reference for harness developers.

---

## Global environment

| Variable | Values | Effect |
|---|---|---|
| `HARNESS_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Sets SDK and Haystack log verbosity (same effect as `--verbose` when `DEBUG`) |
| `HARNESS_ROOT` | `deploy` | Load harnesses from `deploy/` instead of `usr-harnesses/` |

---

## `zaumzeug serve`

Start Hayhooks for a harness (or validate without starting).

```bash
zaumzeug serve <harness> [--dry-run] [--deploy] [--json] [--verbose]
```

| Flag | Description |
|---|---|
| `--dry-run` | Validate `harness.yaml`, `workflow.yaml`, and resolved paths without binding a port or calling an LLM |
| `--deploy` | Load harness from `deploy/<name>/` (or set `HARNESS_ROOT=deploy`) |
| `--json` | Emit machine-readable JSON (dry-run only) |
| `--verbose` | Enable SDK and Haystack structured debug logging |

**Logging:** Use `--verbose` or set `HARNESS_LOG_LEVEL=DEBUG` to see per-request context (`model_id`, tool name, artifact path). API keys are redacted automatically.

```bash
zaumzeug serve example --verbose
HARNESS_LOG_LEVEL=DEBUG zaumzeug serve example --dry-run
```

---

## `zaumzeug compile`

Compile harness artifacts with GEPA (Phase 2+).

```bash
zaumzeug compile <harness> [--verbose]
```

| Flag | Description |
|---|---|
| `--verbose` | Enable SDK and Haystack structured debug logging |

```bash
zaumzeug compile example --verbose
HARNESS_LOG_LEVEL=DEBUG zaumzeug compile example
```

---

## `zaumzeug doctor`

Preflight environment and harness configuration.

```bash
zaumzeug doctor [<harness>] [--deploy] [--verbose] [--json]
```

| Flag | Description |
|---|---|
| `--verbose` | Include passing checks in the human-readable report |
| `--json` | Emit machine-readable JSON report |
| `--deploy` | Validate deploy bundle under `deploy/` |

**Checks include:** Python version, package import, `.env`/API keys for live models, `harness.yaml`, **`workflow.yaml`** (required `entry` and `stages`, agent refs, unique agent folder names), per-agent model registries, runtime paths, and port availability. Warnings (non-blocking): `eval` in Phase 1, MCP without `uv`, stale `workflow-diagram.md`.

Note: `doctor --verbose` controls report detail, not log level. For SDK/Haystack debug logs on serve or compile, use `--verbose` on those commands or `HARNESS_LOG_LEVEL=DEBUG`.

---

## Related

- [Testing guide](guides/testing.md) — mock profile, CI tiers, `HARNESS_LIVE_LLM`
- [Multi-agent workflow](guides/multi-agent-workflow.md) — `workflow.yaml` and agent routing
