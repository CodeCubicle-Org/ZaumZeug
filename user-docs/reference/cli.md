# CLI reference

ZaumZeug command-line interface reference for harness developers.

---

## Global environment

| Variable | Values | Effect |
|---|---|---|
| `HARNESS_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Sets SDK and Haystack log verbosity (`DEBUG` ≈ `--verbose`). Use **`INFO`** with `zaumzeug run` to see stage lifecycle (`stage=…`); default `WARNING` hides those INFO lines |
| `HARNESS_ROOT` | `deploy` | Force production root (`deploy/<name>/`) for **serve**, **mcp**, **acp**, **a2a**, and other root-aware commands (`doctor`, `run`) instead of `usr-harnesses/`. Equivalent to `--deploy`. Use in containers / systemd so the flag is not required on every invocation. Default when unset: `usr-harnesses/` |
| `HARNESS_LIVE_LLM` | `1` | Opt-in live provider e2e (`pytest tests/e2e`). Unset in default CI — mock profile only |
| `ZAUMZEUG_TRACE_CAPTURE` | `1` / `0` | Opt-in production trace export on `zaumzeug serve` (`data/traces/*.jsonl`). Overrides `eval.trace_capture.enabled`. Default off. See [Testing — Trace → test case](../guides/testing.md#trace--test-case-journey-c) |

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

Start Hayhooks for a harness under `usr-harnesses/<name>/` (dev mode) or `deploy/<name>/` (`--deploy`), or validate without starting.

```bash
zaumzeug serve <harness> [--dry-run] [--deploy] [--json] [--verbose] [--port N]
```

| Flag | Description |
|---|---|
| `--dry-run` | Validate `harness.yaml`, `workflow.yaml`, and resolved paths without binding a port or calling an LLM |
| `--deploy` | Load harness **only** from `deploy/<name>/` (or `HARNESS_ROOT=deploy`); requires a valid `manifest.json` |
| `--json` | Emit machine-readable JSON (dry-run only) |
| `--verbose` | Enable SDK and Haystack debug logging |
| `--port N` | Override `serve.hayhooks.port` from harness.yaml (CI smoke on an ephemeral free port) |

**Behavior (dev mode):** Loads the harness, runs the same validation as `--dry-run`, builds the workflow **entry** agent via `runtime/factory.build_agent()`, then starts self-hosted Hayhooks on `serve.hayhooks.port` (default **1416**), or `--port` when set. Phase 1 binds **`127.0.0.1`** only (no wide-open `0.0.0.0`). Pipelines listed in **`serve.expose`** are registered as **`POST /{id}/run`** (E8-S01). Optional **`serve.hayhooks.chainlit: true`** mounts Chainlit at `/chat` on the same port — requires `pip install "hayhooks[chainlit]"`. Open WebUI, SPA + Nginx, and Next.js layouts use the same REST `baseURL` (`http://127.0.0.1:1416/v1`, not `api.openai.com`) — see [Web deployment](../guides/web-deployment.md) and [Pipelines and RAG](../guides/pipelines.md). Hayhooks has **no built-in auth** — production TLS/bearer lives at Traefik ([Production auth](../guides/production-auth.md)).

**Behavior (`--deploy` / production):** Same OpenAI REST API as dev serve (`POST /v1/chat/completions`, `GET /v1/models`, `POST /<harness>/run`), but paths resolve under `deploy/<name>/` only — `usr-harnesses/` is never consulted. Fails fast when the deploy folder is missing or `manifest.json` is absent/invalid. Typical ops flow after `zaumzeug deploy <name>` and target install: `zaumzeug serve <name> --deploy`, `zaumzeug mcp <name> --deploy` (**Done** E7-S06 — same MCP surface as dev), or set `HARNESS_ROOT=deploy` in the container/systemd environment (see [Global environment](#global-environment)).

CI mock smoke (E1-S07) uses `python install/ci_serve_smoke.py example` — starts `zaumzeug serve` on an ephemeral port, probes `GET /v1/models`, then stops the process.

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible chat — `"model": "<harness>"`; optional `"model_id": "<registry-key>"` selects the LLM |
| `GET /v1/models` | Lists the served harness pipeline |
| `POST /<harness>/run` | Direct Hayhooks run API for the **entry agent** |
| `POST /<pipeline-id>/run` | Exposed Haystack YAML from `serve.expose` (E8-S01) — see [Pipelines and RAG](../guides/pipelines.md) |
| `GET /docs` | FastAPI Swagger UI for manual REST probes |
| `GET /chat` | Optional Chainlit GUI — only when `serve.hayhooks.chainlit: true` and `pip install "hayhooks[chainlit]"` |

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

- **Bind:** `zaumzeug serve` listens on **`127.0.0.1` only**. Wide-open hosts (`0.0.0.0`) are rejected.
- **Auth:** Hayhooks has **no in-process auth** (no `serve.auth`). Keep serve on localhost; production TLS + bearer/ForwardAuth lives at Traefik (**Done** E8-S02) — [Production auth](../guides/production-auth.md).
- **Secrets:** API keys live in `.env` only — never in YAML, artifacts, or deploy bundles. Auth credentials stay in Traefik/host env on the target.

---

## `zaumzeug mcp`

Serve the harness as an MCP server for Cursor, Claude Desktop, and other MCP hosts. The workflow **entry** agent is exposed as an MCP tool. External MCP servers declared in `tools.mcp` are wired into the agent as Haystack `MCPToolset`s.

```bash
zaumzeug mcp <harness> [--deploy] [--verbose] [--port N]
```

| Flag | Description |
|---|---|
| `--deploy` | Load harness **only** from `deploy/<name>/` (or `HARNESS_ROOT=deploy`); requires a valid `manifest.json` |
| `--verbose` | Enable SDK and Haystack debug logging |
| `--port N` | Override `serve.hayhooks.mcp_port` from harness.yaml (default **1417**) |

**Bind:** `127.0.0.1` only (same Phase 1 localhost rule as `zaumzeug serve`).

| Endpoint | Purpose |
|---|---|
| `POST /mcp` | MCP Streamable HTTP (JSON-RPC 2.0) |
| `GET /status` | Health check (`{"status": "ok"}`) |

```bash
zaumzeug mcp example
# production bundle (no usr-harnesses/):
zaumzeug mcp example --deploy
# equivalent env override (containers / systemd):
# HARNESS_ROOT=deploy zaumzeug mcp example
# Cursor / Claude Desktop URL:
# http://127.0.0.1:1417/mcp
```

Declare client MCP servers on an agent with `tools.mcp` in `agent.yaml` (stdio via `command`/`args`, or HTTP via `url`):

```yaml
tools:
  mcp:
    - name: filesystem
      command: uv
      args: ["run", "mcp-server-filesystem", "/workspace"]
```

`zaumzeug doctor` warns (non-blocking) when stdio MCP is configured but `uv` is not on PATH. MCP JSON-RPC errors use `{jsonrpc, error: {code, message, data}}` with `data.ok: false`.

Cursor setup (`.cursor/mcp.json` → `http://localhost:{mcp_port}/mcp`): [Cursor MCP setup](../guides/cursor-mcp.md). Production: [Deploy and ship](../guides/deploy.md).

---

## `zaumzeug a2a`

Optional **Agent2Agent (A2A)** hosting so other agents can discover and delegate to your harness. Requires `serve.a2a: true` (or `serve.a2a.enabled: true`) in `harness.yaml` and `pip install "hayhooks[a2a]"`. This is **not** MCP and **not** ACP — see [A2A guide](../guides/a2a.md).

```bash
zaumzeug a2a <harness> [--deploy] [--verbose] [--port N]
```

| Flag | Description |
|---|---|
| `--deploy` | Load harness **only** from `deploy/<name>/` (or `HARNESS_ROOT=deploy`); requires a valid `manifest.json` |
| `--verbose` | Enable SDK and Haystack debug logging |
| `--port N` | Override `serve.a2a.port` from harness.yaml (default **1418**) |

**Bind:** `127.0.0.1` only (same Phase 1 localhost rule as `zaumzeug serve` / `zaumzeug mcp`).

| Endpoint | Purpose |
|---|---|
| `GET /{harness}/.well-known/agent-card.json` | Agent Card for discovery |
| `POST /{harness}/` | A2A JSON-RPC binding |
| `GET /status` | Health + list of exposed agents |

```bash
# harness.yaml must include serve.a2a: true
zaumzeug a2a example
# production bundle:
zaumzeug a2a example --deploy
# HARNESS_ROOT=deploy zaumzeug a2a example
# curl http://127.0.0.1:1418/example/.well-known/agent-card.json
```

One process = one harness (NG1 multi-tenant remains out of scope). Fleet layout: [A2A guide](../guides/a2a.md#agent-fleet-layout-one-harness-per-process).

---

## `zaumzeug acp`

Serve the harness as an **Agent Client Protocol** (ACP) agent on **stdio JSON-RPC** so Zed, JetBrains, or Neovim can drive it as the primary agent. This is **not** IBM Agent Communication Protocol / **A2A**.

```bash
zaumzeug acp <harness> [--deploy] [--verbose]
```

| Flag | Description |
|---|---|
| `--deploy` | Load harness **only** from `deploy/<name>/` (or `HARNESS_ROOT=deploy`); requires a valid `manifest.json` |
| `--verbose` | Enable SDK and Haystack debug logging (**stderr only** — stdout is the protocol) |

**Transport:** newline-delimited JSON-RPC 2.0 on stdin/stdout (`initialize`, `session/new`, `session/prompt`). Status banners go to stderr. Optional `serve.acp.enabled` in `harness.yaml` documents intent; the CLI always starts the adapter.

The factory still wires `tools.mcp` on the entry agent (internal MCP client). Cursor is **not** a generic ACP client — use `zaumzeug mcp` instead ([Cursor MCP setup](../guides/cursor-mcp.md)).

**Zed** — Agent Settings → External Agents → Add Custom Agent (`agent_servers` in `settings.json`):

```json
{
  "agent_servers": {
    "zaumzeug": {
      "type": "custom",
      "command": "zaumzeug",
      "args": ["acp", "example"],
      "env": {}
    }
  }
}
```

**JetBrains** — AI Chat → Add Custom Agent writes `~/.jetbrains/acp.json`:

```json
{
  "agent_servers": {
    "ZaumZeug": {
      "command": "zaumzeug",
      "args": ["acp", "example"],
      "env": {}
    }
  }
}
```

Full registration notes: [ACP (Zed / JetBrains)](../guides/acp.md).

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
| `--verbose` | Enable SDK and Haystack structured debug logging (includes stage INFO lifecycle) |

```bash
zaumzeug run example --input "Summarize the latest release notes"
zaumzeug run example --from reviewer --input "Check the draft"
HARNESS_LOG_LEVEL=INFO zaumzeug run example --input "…"   # stage start/success/retry/failure
```

**Behavior:** Stages run top-to-bottom from `workflow.yaml`. Prior stage assistant text is prepended as a user message before `--input` for the next agent. **`pipeline:`** stages invoke Haystack YAML listed in **`serve.expose`** (E8-S01) — see [Pipelines and RAG](../guides/pipelines.md). Live generation failures become typed `WorkflowError` with harness / agent / stage. Optional `runtime.retry` on `harness.yaml` retries `Agent.run` (and optional `output.format: json`) per stage; build/config errors are not retried. Stage lifecycle logs use structured `stage` at INFO — set `HARNESS_LOG_LEVEL=INFO` or `--verbose` (default WARNING hides them). See [Multi-agent workflow — Run reliability](../guides/multi-agent-workflow.md#run-reliability-zaumzeug-run). **Serve/HTTP does not yet share this reliability layer.**

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

See [Testing — Trace → test case](../guides/testing.md#trace--test-case-journey-c) for the JSONL schema, production capture (`eval.trace_capture` / `ZAUMZEUG_TRACE_CAPTURE`), and valset/train merge; [Mode C](../guides/testing.md#mode-c--http-black-box-stagingdebug) for HTTP black-box eval; and [GEPA ↔ DeepEval bridge](../guides/testing.md#gepa--deepeval-bridge-compile--eval--compile) for failed-eval → train / shared valset.

---

## `zaumzeug replay` (deferred)

Re-run a captured tool loop with recorded tool outputs:

```bash
zaumzeug replay <name> --trace data/traces/run-001.jsonl
```

**Not available in v1** — deferred (PRD §9). Score a captured turn with `zaumzeug eval --trace` instead; merge rows into `data/val.jsonl` / `data/train.jsonl` with `merge_traces_into_datasets` ([Journey C](../guides/testing.md#trace--test-case-journey-c)).

---

## `zaumzeug deploy`

Package a harness for production (Architecture §10.2). Runs **doctor** preflight, then the **eval gate** (Architecture §6.4 / E5-S06 / E6-S03), then writes `deploy/<name>/` (E5-S01 + copy matrix E5-S02): stripped yaml, workflow, pinned artifacts, `manifest.json`, `README.deploy.md`, and target install scripts.

```bash
zaumzeug deploy <harness> [--eval-gate skip|warn|block] [--dockerfile] [--verbose]
```

| Flag / arg | Description |
|---|---|
| `<harness>` | Harness name under `usr-harnesses/` |
| `--eval-gate` | Override `deploy.eval_gate` from `harness.yaml` for this run |
| `--dockerfile` | Include `Dockerfile`, `.dockerignore`, and `docker-compose.example.yml` in the bundle (or set `deploy.dockerfile: true`) |
| `--verbose` | Enable SDK and Haystack structured debug logging |

**Config** (`harness.yaml`):

```yaml
deploy:
  eval_gate: skip    # skip | warn | block (default: skip)
  dockerfile: false  # optional: generate Dockerfile in deploy/<name>/ (E8-S05)
```

| Mode | Behavior |
|---|---|
| `skip` | Do not run eval (default when `deploy:` omitted). |
| `warn` | Run `zaumzeug eval` when `eval:` is set; print failures; continue packaging. |
| `block` | Run `zaumzeug eval` when `eval:` is set; abort packaging on any failure. |

If `eval:` is absent, `warn` / `block` are a no-op. Gate logic lives only in `deploy/packager.py` (no duplicate path).

**Bundle contents** (`deploy/<name>/`): stripped `harness.yaml` (no `eval`/`deploy`/`compile`), `workflow.yaml`, per-agent runtime files (`prompts/` / `tools/` / `hooks.py` / `agents-models.yaml` when referenced) + pinned `artifacts/<run_id>/`, `docs/workflow-diagram.md`, `manifest.json`, `README.deploy.md`, and `target_install.py` (+ `.sh` / `.ps1` wrappers). Optional **Dockerfile** (+ `.dockerignore`, `docker-compose.example.yml`) when `--dockerfile` / `deploy.dockerfile: true` (E8-S05) — base `python:3.11-slim`, `target_install --skip-venv`, CMD `zaumzeug serve <name> --deploy`; `.env` injected at run time only. **Never** copies `modules/`, `skills/`, `data/`, or `eval/` (Architecture §10.1 / E5-S02). Missing required runtime paths abort deploy before writing. Idempotent — overwrites an existing bundle. Target install (**Done** E5-S09a/b/c): optional `.venv`, `pip install zaumzeug` (runtime only), seed `.env` from `.env.example` when missing, wrappers forward flags/exit codes, optional `--verify` runs `zaumzeug doctor <name> --deploy` then `zaumzeug serve <name> --deploy --dry-run`.

**After deploy:** copy `deploy/<name>/` to the target → run bundled `target_install` → create `.env` on the target → `zaumzeug serve <name> --deploy` (**Done** E5-S03) or `zaumzeug mcp <name> --deploy` (**Done** E7-S06) or `HARNESS_ROOT=deploy zaumzeug serve|mcp <name>` (**Done** E5-S04). Ship workflow docs **Done** E5-S05 — see [Deploy and ship](../guides/deploy.md) and the bundle `README.deploy.md`. Deploy git policy **Done** E5-S07 — default ignore `deploy/` / artifacts; optional release commit or CI upload ([Git policy](../guides/deploy.md#git-policy-for-deploy-bundles)). Platform policy **Done** E5-S08 — Linux-first ops target; OS-neutral bundle; Win/macOS best-effort not CI-gated; Linux CI deploy→serve smoke ([Platforms](../guides/deploy.md#platforms)). Optional Dockerfile **Done** E8-S05. Target install **Done** E5-S09a/b/c (core / wrappers / `--verify`). Same OpenAI REST as dev serve; same MCP surface as `zaumzeug mcp` in development; `usr-harnesses/` is not required. See also [serve](#zaumzeug-serve), [mcp](#zaumzeug-mcp), and [Global environment](#global-environment).

```bash
zaumzeug deploy example
zaumzeug deploy example --eval-gate block
zaumzeug deploy example --dockerfile
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
| `--deploy` | Validate deploy bundle under `deploy/` (or set `HARNESS_ROOT=deploy`) |

**Checks include:** Python version, package import, `.env`/API keys for live models, `harness.yaml` (including optional `eval:` / `EvalConfig`, `deploy:` / `DeployConfig`, and `runtime:` / `RuntimeRetryConfig`), **`workflow.yaml`** (required `entry` and `stages`, agent refs, unique agent folder names), per-agent model registries, runtime paths, pinned artifact manifests, and port availability. **Failing (blocking):** `tools.custom` import errors — `custom_tools` fails in default **and** `--deploy` modes with the module path and expected file (E7-S02). Warnings (non-blocking): MCP without `uv` when stdio `tools.mcp` is configured, stale `workflow-diagram.md`, stale compiled artifact vs `compile.module` `source_hash` (re-run `zaumzeug compile`), pin ≠ `artifacts/current`. Doctor does **not** require the optional `[eval]` / DeepEval extra (E6-S01); use `zaumzeug eval` for regression (E6-S02), `deploy.eval_gate` on `zaumzeug deploy` (E6-S03 / E5-S06), `zaumzeug eval --trace` for captured failures (E6-S05), `zaumzeug eval --base-url` for Mode C staging/debug (E6-S06), and `zaumzeug.eval.gepa_bridge` for failed-eval → train / optional DeepEval GEPA metrics (E6-S07).

Note: `doctor --verbose` controls report detail, not log level. For SDK/Haystack debug logs on serve, compile, eval, deploy, or run, use `--verbose` on those commands or `HARNESS_LOG_LEVEL` (`INFO` for run stage lifecycle; `DEBUG` for full request noise).

---

## Related

- [Testing guide](../guides/testing.md) — mock profile, CI tiers, `HARNESS_LIVE_LLM`, debugpy, `zaumzeug eval`, `--trace` / Journey C ratchet, Mode C `--base-url`, GEPA ↔ DeepEval bridge, deploy eval gates; `zaumzeug replay` deferred
- [Custom tools](../guides/custom-tools.md) — `tools.custom` Python modules, `ComponentTool` / `Tool`, doctor import errors
- [Cursor MCP setup](../guides/cursor-mcp.md) — `.cursor/mcp.json` → `http://localhost:{mcp_port}/mcp`; `--cursor-mcp`; `uv` for stdio `tools.mcp`
- [ACP (Zed / JetBrains)](../guides/acp.md) — `zaumzeug acp` stdio JSON-RPC; Agent Client Protocol ≠ A2A; Cursor uses MCP
- [A2A (agent fleets)](../guides/a2a.md) — optional `zaumzeug a2a` / `serve.a2a: true`; agent card; ≠ MCP/ACP
- [Multi-agent workflow](../guides/multi-agent-workflow.md) — `workflow.yaml`, agent routing, [run reliability](../guides/multi-agent-workflow.md#run-reliability-zaumzeug-run) (`runtime.retry`, `output.format: json`, stage logs)
- [Web deployment](../guides/web-deployment.md) — Chainlit `/chat`, Open WebUI, SPA + Nginx, Next.js; OpenAI `baseURL` at the harness
- [Production auth](../guides/production-auth.md) — Traefik proxy-only TLS + ForwardAuth; no `serve.auth` in v1
- [Deploy and ship](../guides/deploy.md) — `zaumzeug deploy` → target install → `serve --deploy`
