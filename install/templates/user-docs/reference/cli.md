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

## `zaumzeug init`

Scaffold a new harness folder under `usr-harnesses/<name>/` from the Phase 1 template (minimal `harness.yaml`, `workflow.yaml`, one agent with mock models and a system prompt).

```bash
zaumzeug init <name> [--force]
```

| Flag | Description |
|---|---|
| `--force` | Overwrite an existing `usr-harnesses/<name>/` folder |

**Name rules:** Single safe path segment — letters, digits, `_`, `-`; no `..` or path separators. Init fails if the folder already exists unless `--force` is set.

```bash
zaumzeug init my-agent
zaumzeug doctor my-agent
zaumzeug serve my-agent
```

See [Project setup](../getting-started/project-setup.md) for layout details.

---

## `zaumzeug install-project` (deferred)

Scaffold project folders (`usr-harnesses/`, `user-docs/`, `.env`, etc.) in an arbitrary cwd for **PyPI consumers** who do not clone this repo. **Not available yet** — deferred until `zaumzeug` is published on PyPI ([E1-S08](../../docs/stories/epic-stories/25-story.md)). Until then, use [clone + client install](../getting-started/installation.md).

---

## `zaumzeug serve`

Start Hayhooks for a harness under `usr-harnesses/<name>/` (dev mode), or validate without starting.

```bash
zaumzeug serve <harness> [--dry-run] [--deploy] [--json] [--verbose] [--port N]
```

| Flag | Description |
|---|---|
| `--dry-run` | Validate `harness.yaml`, `workflow.yaml`, and resolved paths without binding a port or calling an LLM |
| `--deploy` | Load harness from `deploy/<name>/` (or `HARNESS_ROOT=deploy`) |
| `--json` | Emit machine-readable JSON (dry-run only) |
| `--verbose` | Enable SDK and Haystack debug logging |
| `--port N` | Override `serve.hayhooks.port` from harness.yaml (CI smoke on an ephemeral free port) |

**Behavior (dev mode):** Loads the harness, runs the same validation as `--dry-run`, builds the workflow **entry** agent via `runtime/factory.build_agent()`, then starts self-hosted Hayhooks on `serve.hayhooks.port` (default **1416**), or `--port` when set. Phase 1 binds **`127.0.0.1`** only (no wide-open `0.0.0.0`).

CI mock smoke (E1-S07) uses `python install/ci_serve_smoke.py example` — starts `zaumzeug serve` on an ephemeral port, probes `GET /v1/models`, then stops the process.

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible chat — `"model": "<harness>"`; optional `"model_id": "<registry-key>"` selects the LLM |
| `GET /v1/models` | Lists the served harness pipeline |
| `POST /<harness>/run` | Direct Hayhooks run API |

**OpenAI `model` vs `model_id`:** Clients pass the harness name as OpenAI `model` (deployment identity). To override which registry LLM answers, add optional `model_id` (a key from the entry agent's merged `agents-models.yaml`). Omit `model_id` to use the agent's `default_model_id`.

```bash
# Default mock (or configured default_model_id)
curl -s http://127.0.0.1:1416/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"example","messages":[{"role":"user","content":"hi"}]}'

# Override registry entry (must exist in agents-models.yaml)
curl -s http://127.0.0.1:1416/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"example","model_id":"alt","messages":[{"role":"user","content":"hi"}]}'
```

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

## `zaumzeug run`

Execute `workflow.yaml` stages serially (multi-agent orchestration). Each agent stage loads that agent's config and merged `agents-models.yaml`, builds a Haystack Agent via the runtime factory, and forwards prior stage output as context to the next stage.

```bash
zaumzeug run <harness> [--from STAGE] [--input TEXT] [--deploy] [--verbose]
```

| Flag | Description |
|---|---|
| `--from STAGE` | Start from this workflow stage id (agent or pipeline name) — skip earlier stages |
| `--input TEXT` | User input passed to each agent stage (also receives prior stage output as context) |
| `--deploy` | Load harness from `deploy/<name>/` (or set `HARNESS_ROOT=deploy`) |
| `--verbose` | Enable SDK and Haystack structured debug logging |

```bash
zaumzeug run example --input "Summarize the latest release notes"
zaumzeug run example --from reviewer --input "Check the draft"
```

**Behavior:** Stages run top-to-bottom from `workflow.yaml`. Prior stage assistant text is prepended as a user message before `--input` for the next agent. Pipeline stages are not executable in Phase 1 (schema allowed; full invoke is Phase 4). Resolution errors include harness and agent names.

---

## `zaumzeug compile`

Run offline GEPA per agent: validate Phase 2 compile config, load DSPy modules, preflight task/reflection LM ids, optimize, and write artifacts.

```bash
zaumzeug compile <harness> [--agent NAME] [--verbose]
```

| Flag / arg | Description |
|---|---|
| `<harness>` | Harness name under `usr-harnesses/` |
| `--agent NAME` | Compile a single agent (default: every agent with `compile.module`) |
| `--verbose` | Enable SDK and Haystack structured debug logging |

**Requires per agent:** a Phase 2 `compile:` block in `agents/<name>/agent.yaml` with `compile.module` (`module.path:ClassName`). Optional: `task_model_id`, `reflection_model_id`, train/val paths, GEPA budget (`auto` / `budget` / `max_metric_calls` / `max_full_evals`).

**API keys:** Live task/reflection models need provider keys in `.env` (or the environment) before GEPA runs — the same keys `zaumzeug doctor` checks. Missing registry ids or keys fail fast with an actionable suggestion. The shipped `example` harness uses `provider: mock` and a stub GEPA path so you can exercise compile offline without keys; switch to live model ids in `agents-models.yaml` for real optimization.

**Artifacts:** Each run writes immutable `agents/<name>/artifacts/<run_id>/` and updates `artifacts/current` (symlink when possible, otherwise a copy). Export maps `dump_state()` to Haystack files: `prompts/system.md`, optional `prompts/input_rewrite.md`, `agent.json`, and **`artifact-manifest.json`** (not the deploy bundle’s `manifest.json`). Legacy `manifest.json` inside an artifact folder is accepted during migration. **GEPA optimizes the template offline; runtime applies fixed exported text only** — never end-user chat as an optimization target. See [Compile and export](../guides/compile.md).

**Fail-fast (before GEPA):** missing `compile.module`, unimportable module, model id absent from the merged registry, or missing provider API keys in `.env` / the environment.

```bash
zaumzeug compile example --agent researcher --verbose
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
