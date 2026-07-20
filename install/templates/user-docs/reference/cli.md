# CLI reference

ZaumZeug command-line interface reference for harness developers.

---

## Global environment

| Variable | Values | Effect |
|---|---|---|
| `HARNESS_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Sets SDK and Haystack log verbosity (same effect as `--verbose` when `DEBUG`) |
| `HARNESS_ROOT` | `deploy` | Load harnesses from `deploy/` instead of `usr-harnesses/` |
| `HARNESS_LIVE_LLM` | `1` | Opt-in live provider e2e (`pytest tests/e2e`). Unset in default CI — mock profile only |

---

## `zaumzeug serve`

Start Hayhooks for a harness under `usr-harnesses/<name>/` (dev mode), or validate without starting.

```bash
zaumzeug serve <harness> [--dry-run] [--deploy] [--json] [--verbose]
```

| Flag | Description |
|---|---|
| `--dry-run` | Validate `harness.yaml`, `workflow.yaml`, and resolved paths without binding a port or calling an LLM |
| `--deploy` | Load harness from `deploy/<name>/` (or set `HARNESS_ROOT=deploy`) |
| `--json` | Emit machine-readable JSON (dry-run only) |
| `--verbose` | Enable SDK and Haystack structured debug logging |

**Behavior (dev mode):** Loads the harness, runs the same validation as `--dry-run`, builds the workflow **entry** agent via `runtime/factory.build_agent()`, then starts self-hosted Hayhooks on `serve.hayhooks.port` (default **1416**). Phase 1 binds **`127.0.0.1`** only (no wide-open `0.0.0.0`).

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible chat (use `"model": "<harness>"`) |
| `GET /v1/models` | Lists the served harness pipeline |
| `POST /<harness>/run` | Direct Hayhooks run API |

**Logging:** Use `--verbose` or set `HARNESS_LOG_LEVEL=DEBUG` to see per-request context (`model_id`, tool name, artifact path). API keys are redacted automatically.

```bash
zaumzeug serve example --verbose
HARNESS_LOG_LEVEL=DEBUG zaumzeug serve example --dry-run
```

### IDE attach (debugpy)

`debugpy` ships in the `[dev]` extra. Attach your IDE to a listening serve process:

```bash
python -m debugpy --listen 5678 -m zaumzeug.cli serve example
```

Then connect the debugger to `localhost:5678`.

### Hayhooks escape hatch

Prefer `zaumzeug serve` for normal work — it loads harness config and builds agents for you. For low-level Haystack debugging only, you can run raw Hayhooks against a pipeline folder:

```bash
# Escape hatch — bypasses ZaumZeug config/agent factory
hayhooks run
# or, for MCP:
hayhooks mcp run
```

Use this to isolate Haystack/Hayhooks issues from harness YAML or SDK wiring. Production and day-to-day local serve should stay on `zaumzeug serve`.

### Phase 1 security notes

- **Bind:** `zaumzeug serve` listens on **`127.0.0.1` only**. Wide-open hosts (`0.0.0.0`) are rejected in Phase 1.
- **Auth:** Hayhooks has no in-process auth in Phase 1 — keep serve on localhost; put Traefik (or similar) in front for production (Phase 4).
- **Secrets:** API keys live in `.env` only — never in YAML, artifacts, or deploy bundles.

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

- [Testing guide](../guides/testing.md) — mock profile, CI tiers, `HARNESS_LIVE_LLM`, debugpy
- [Multi-agent workflow](../guides/multi-agent-workflow.md) — `workflow.yaml` and agent routing
