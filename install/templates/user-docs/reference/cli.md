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
zaumzeug init <name> [--force] [--with-eval]
```

| Flag | Description |
|---|---|
| `--force` | Overwrite an existing `usr-harnesses/<name>/` folder |
| `--with-eval` | Include optional `eval/` DeepEval pytest scaffold (`metrics.py` + `test_*.py`; dev-only, excluded from deploy) |

**Name rules:** Single safe path segment — letters, digits, `_`, `-`; no `..` or path separators. Init fails if the folder already exists unless `--force` is set.

```bash
zaumzeug init my-agent
zaumzeug init my-agent --with-eval   # optional DeepEval pytest scaffold
zaumzeug doctor my-agent
zaumzeug serve my-agent
```

With `--with-eval`, after `pip install "zaumzeug[eval]"`:

```bash
deepeval test run usr-harnesses/my-agent/eval/
```

See [Project setup](../getting-started/project-setup.md) for layout details and [Testing](../guides/testing.md#deepeval-pytest-scaffold) for the eval workflow.

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

Run offline GEPA per agent: validate Phase 2 compile config, load DSPy modules, preflight task/reflection LM ids, optimize, and write artifacts. Every successful compile (except `--dry-run`) also regenerates `docs/workflow-diagram.md`. Use `--dry-run` to validate without GEPA or LLM calls (same idea as `serve --dry-run`), or `--workflow-diagram-only` to refresh the diagram without optimizing.

```bash
zaumzeug compile <harness> [--agent NAME] [--dry-run | --workflow-diagram-only] [--verbose]
```

| Flag / arg | Description |
|---|---|
| `<harness>` | Harness name under `usr-harnesses/` |
| `--agent NAME` | Compile a single agent (default: every agent with `compile.module`) |
| `--dry-run` | Validate Phase 2 compile config, resolve module imports, and print task/reflection model ids — no GEPA, no LLM API calls, no artifact writes |
| `--workflow-diagram-only` | Regenerate `docs/workflow-diagram.md` from `workflow.yaml` + resolved agent models — no GEPA, no LLM calls (mutually exclusive with `--dry-run`) |
| `--verbose` | Enable SDK and Haystack structured debug logging |

**Requires per agent:** a Phase 2 `compile:` block in `agents/<name>/agent.yaml` with `compile.module` (`module.path:ClassName`). Optional: `task_model_id`, `reflection_model_id`, train/val paths, GEPA budget (`auto` / `budget` / `max_metric_calls` / `max_full_evals`). Not required for `--workflow-diagram-only`.

**API keys:** Live task/reflection models need provider keys in `.env` (or the environment) before GEPA runs — the same keys `zaumzeug doctor` checks. Missing registry ids or keys fail fast with an actionable suggestion. The shipped `example` harness uses `provider: mock` and a stub GEPA path so you can exercise compile offline without keys; switch to live model ids in `agents-models.yaml` for real optimization. `--dry-run` still preflights registry ids / keys but never calls the LLM.

**Artifacts:** Each run writes immutable `agents/<name>/artifacts/<run_id>/` (never overwritten) and updates `artifacts/current` (symlink when possible, otherwise a copy). Export maps `dump_state()` to Haystack files: `prompts/system.md`, optional `prompts/input_rewrite.md`, `agent.json`, and **`artifact-manifest.json`** (includes `module_hash` + `source_hash` of the `compile.module` `.py`; not the deploy bundle’s `manifest.json`). Legacy `manifest.json` inside an artifact folder is accepted during migration. **GEPA optimizes the template offline; runtime applies fixed exported text only** — never end-user chat as an optimization target. When the manifest lists `input_rewrite`, `zaumzeug serve` / `zaumzeug run` preprocess user messages with that template before `Agent.run` (no DSPy).

**Workflow diagram:** Full compile and `--workflow-diagram-only` write `docs/workflow-diagram.md` (Mermaid flowchart; auto-generated — do not hand-edit). `zaumzeug doctor` warns when `workflow.yaml` is newer than the diagram (or the file is missing).

**Serve after compile:** Point `agent.artifact` at `artifacts/current` so serve loads the exported prompts (hand-edited `system_prompt` is ignored; `compile.module` is not imported). See [Compile and export — Serve after compile](../guides/compile.md#serve-after-compile).

**Rollback:** Pin `agent.artifact` to a previous immutable `artifacts/<run_id>/` (or retarget `current`) — do not hand-edit exported prompts. See [Compile and export — Rollback](../guides/compile.md#rollback-to-a-pinned-run).

**Fail-fast (before GEPA):** missing `compile.module`, unimportable module, model id absent from the merged registry, or missing provider API keys in `.env` / the environment.

```bash
zaumzeug compile example --dry-run --agent researcher
zaumzeug compile example --workflow-diagram-only
zaumzeug compile example --agent researcher --verbose
HARNESS_LOG_LEVEL=DEBUG zaumzeug compile example
```

---

## `zaumzeug eval`

Run harness regression checks from the optional `eval:` block in `harness.yaml` (Architecture §6.3 / E6-S02). Dev-only — never invoked from `zaumzeug serve`. Score a captured Haystack turn with `--trace` (E6-S05) without re-running the agent. Black-box a **running** serve with `--base-url` (Mode C / E6-S06) — **staging/debug only**. Feed failures into the next GEPA compile with `append_failed_eval_to_train` (E6-S07).

```bash
zaumzeug eval <harness> [--framework builtin|deepeval] [--agent NAME] [--trace PATH] [--base-url [URL]] [--verbose]
```

| Flag / arg | Description |
|---|---|
| `<harness>` | Harness name under `usr-harnesses/` |
| `--framework` | Override `eval.framework` for this run (`builtin` or `deepeval`) |
| `--agent NAME` | Evaluate a single agent (default: workflow entry agent) |
| `--trace PATH` | Score a captured JSONL trace (`data/traces/…`); uses `actual_output` from the file |
| `--base-url [URL]` | Mode C (staging/debug): HTTP black-box against a running `zaumzeug serve` `/v1/chat/completions`. Omit URL to use `http://127.0.0.1:<serve.hayhooks.port>`. Also configurable as `eval.base_url` |
| `--verbose` | Enable SDK and Haystack structured debug logging |

**Requires:** an `eval:` section in `harness.yaml` with at least `valset` (JSONL of `input` / optional `expected_output`). Missing `eval:` exits with a clear error. With `--trace`, the valset file is skipped; metrics/framework still come from `eval:`. Do not combine `--trace` with `--base-url`.

**Frameworks:**

| `eval.framework` | DeepEval required? | Behavior |
|---|---|---|
| *(omitted)* | Yes (`[eval]` extra) | Defaults to `deepeval` |
| `deepeval` | Yes | Run configured `eval.metrics` + thresholds on agent outputs |
| `builtin` | **No** | Load `eval.valset` JSONL; exact or substring match on `expected_output` when present |

```bash
# JSONL checks without DeepEval
zaumzeug eval example --framework builtin

# DeepEval metrics (needs: pip install "zaumzeug[eval]")
zaumzeug eval example
zaumzeug eval example --agent researcher --verbose

# Score one captured production/local failure (Journey C)
zaumzeug eval example --framework builtin --trace data/traces/run-001.jsonl

# Mode C — black-box a running serve (staging/debug only)
zaumzeug serve example &
zaumzeug eval example --framework builtin --base-url
zaumzeug eval example --framework builtin --base-url http://127.0.0.1:1416
```

See [Testing — Trace → test case](../guides/testing.md#trace--test-case-journey-c) for the JSONL schema and valset append, [Mode C](../guides/testing.md#mode-c--http-black-box-stagingdebug) for HTTP black-box eval, and [GEPA ↔ DeepEval bridge](../guides/testing.md#gepa--deepeval-bridge-compile--eval--compile) for failed-eval → train / shared valset.

---

## `zaumzeug deploy`

Package a harness for production. Runs the **eval gate** first (Architecture §6.4 / E5-S06 / E6-S03); full bundle copy rules land in E5-S01.

```bash
zaumzeug deploy <harness> [--eval-gate skip|warn|block] [--verbose]
```

| Flag / arg | Description |
|---|---|
| `<harness>` | Harness name under `usr-harnesses/` |
| `--eval-gate` | Override `deploy.eval_gate` from `harness.yaml` for this run |
| `--verbose` | Enable SDK and Haystack structured debug logging |

**Config** (`harness.yaml`):

```yaml
deploy:
  eval_gate: skip    # skip | warn | block (default: skip)
```

| Mode | Behavior |
|---|---|
| `skip` | Do not run eval (default when `deploy:` omitted). |
| `warn` | Run `zaumzeug eval` when `eval:` is set; print failures; continue packaging. |
| `block` | Run `zaumzeug eval` when `eval:` is set; abort packaging on any failure. |

If `eval:` is absent, `warn` / `block` are a no-op. Gate logic lives only in `deploy/packager.py` (no duplicate path).

```bash
zaumzeug deploy example
zaumzeug deploy example --eval-gate block
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

**Checks include:** Python version, package import, `.env`/API keys for live models, `harness.yaml` (including optional `eval:` / `EvalConfig` and `deploy:` / `DeployConfig`), **`workflow.yaml`** (required `entry` and `stages`, agent refs, unique agent folder names), per-agent model registries, runtime paths, pinned artifact manifests, and port availability. Warnings (non-blocking): MCP without `uv`, stale `workflow-diagram.md`, stale compiled artifact vs `compile.module` `source_hash` (re-run `zaumzeug compile`), pin ≠ `artifacts/current`. Doctor does **not** require the optional `[eval]` / DeepEval extra (E6-S01); use `zaumzeug eval` for regression (E6-S02), `deploy.eval_gate` on `zaumzeug deploy` (E6-S03 / E5-S06), `zaumzeug eval --trace` for captured failures (E6-S05), `zaumzeug eval --base-url` for Mode C staging/debug (E6-S06), and `zaumzeug.eval.gepa_bridge` for failed-eval → train / optional DeepEval GEPA metrics (E6-S07).

Note: `doctor --verbose` controls report detail, not log level. For SDK/Haystack debug logs on serve, compile, eval, or deploy, use `--verbose` on those commands or `HARNESS_LOG_LEVEL=DEBUG`.

---

## Related

- [Testing guide](../guides/testing.md) — mock profile, CI tiers, `HARNESS_LIVE_LLM`, debugpy, `zaumzeug eval`, `--trace` / Journey C, Mode C `--base-url`, GEPA ↔ DeepEval bridge, deploy eval gates
- [Multi-agent workflow](../guides/multi-agent-workflow.md) — `workflow.yaml` and agent routing
