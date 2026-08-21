# ZaumZeug — User documentation

End-user guides for building and running multi-agent harnesses. For SDK design and epics, see the internal `docs/` folder in the repository.

| Section | Audience | Contents |
|---|---|---|
| [Getting started](getting-started/) | New developers | Install, project layout, [first harness](getting-started/first-harness.md) |
| [Guides](guides/) | Day-to-day use | Workflow, agents, custom tools, Cursor MCP, ACP (Zed/JetBrains), web layouts (Chainlit / Open WebUI / SPA / Next.js), pipelines / RAG, compile, deploy |
| [Reference](reference/) | Lookup | CLI commands (`reference/cli.md`), YAML fields *(expanded as features ship)* |

## Getting started

| Guide | Description |
|---|---|
| [Installation](getting-started/installation.md) | Prerequisites, install commands, disk, extras, updates, troubleshooting |
| [Project setup](getting-started/project-setup.md) | Layout and `zaumzeug init` for new harnesses |
| [Your first harness](getting-started/first-harness.md) | Run the shipped `example` research agent (mock, no API keys) |

## Guides

| Guide | Description |
|---|---|
| [Multi-agent workflow](guides/multi-agent-workflow.md) | `workflow.yaml`, agent vs pipeline stages, control flow inside agents; **run reliability** (`runtime.retry`, `output.format: json`, stage INFO logs — E8-S07) |
| [Custom tools](guides/custom-tools.md) | `tools.custom` Python modules under `agents/<name>/tools/`; Haystack `ComponentTool` / `Tool`; doctor/serve import errors include the module path (E7-S02). Builtin catalog: `web_fetch`, `calculator`, `read_file`, `search_docs` (`tools.builtin`; E7-S07 / E8-S01) |
| [Cursor MCP setup](guides/cursor-mcp.md) | Point Cursor at `http://localhost:{mcp_port}/mcp` (default **1417**); install `--cursor-mcp` writes live `.cursor/mcp.json`; `uv` only for stdio `tools.mcp` (E7-S03) |
| [ACP (Zed / JetBrains)](guides/acp.md) | `zaumzeug acp` stdio JSON-RPC for Zed/JetBrains; Agent Client Protocol ≠ IBM ACP/A2A; Cursor uses MCP (E7-S05) |
| [Web deployment](guides/web-deployment.md) | Chainlit `/chat`, Open WebUI two-container, SPA + Nginx, Next.js co-located; OpenAI `baseURL` at the harness (`http://127.0.0.1:1416/v1`), not `api.openai.com` (E7-S08) |
| [Pipelines and RAG](guides/pipelines.md) | `serve.expose` registers `pipelines/` YAML; `POST /{id}/run`; RAG retriever → prompt → generator; `search_docs` builtin (E8-S01) |
| [Compile and export](guides/compile.md) | GEPA offline compile; Haystack artifact export; workflow diagram; optional runtime `input_rewrite`; pin/rollback to immutable `artifacts/<run_id>/` |
| [Deploy and ship](guides/deploy.md) | Copy `deploy/<name>/` → `target_install` → `.env` → `zaumzeug serve --deploy`; runtime-only install (no DSPy/GEPA/DeepEval); Win/macOS/Linux table (E5-S05); git policy for bundles (E5-S07); Linux-first platform matrix (E5-S08); target install — venv / pip / `.env` / wrappers / `--verify` (E5-S09a/b/c) |
| [Testing](guides/testing.md) | Unit, integration, eval layers; mock profile; optional `[eval]` / DeepEval (E6-S01); `zaumzeug eval` (E6-S02); deploy eval gate (E6-S03 / E5-S06); `eval/` pytest (E6-S04); trace → test case (E6-S05); Mode C HTTP `--base-url` (E6-S06); GEPA ↔ DeepEval bridge (E6-S07); deploy packager (E5-S01) + copy matrix (E5-S02); serve `--deploy` (E5-S03); `HARNESS_ROOT=deploy` (E5-S04); ship workflow (E5-S05); deploy git policy (E5-S07); platform policy + Linux deploy smoke (E5-S08); target install + `--verify` (E5-S09a/b/c); CI tiers |

## Quick links

- **`zaumzeug init <name>`** — scaffold a new harness under `usr-harnesses/`
- **Custom tools** — list Python modules in `tools.custom` on `agent.yaml` (`agents/<name>/tools/*.py`). Import errors fail `zaumzeug doctor` / serve with the module path. SDK builtins (`web_fetch`, `calculator`, `read_file`, `search_docs`) use `tools.builtin` instead. `search_docs` needs a RAG pipeline in `serve.expose` — see [Pipelines and RAG](guides/pipelines.md) and [Custom tools](guides/custom-tools.md).
- **`zaumzeug mcp <harness>`** — serve the workflow entry agent as MCP at `http://127.0.0.1:{mcp_port}/mcp` (default **1417**). Production: `zaumzeug mcp <harness> --deploy` (or `HARNESS_ROOT=deploy`). Point Cursor at that URL via `.cursor/mcp.json` (install `--cursor-mcp` or copy the example). Declare external MCP servers in `tools.mcp` on `agent.yaml` (Haystack `MCPToolset`; stdio servers need `uv`). See [Cursor MCP setup](guides/cursor-mcp.md), [Deploy and ship](guides/deploy.md), and [CLI — mcp](reference/cli.md#zaumzeug-mcp).
- **`zaumzeug acp <harness>`** — Agent Client Protocol stdio JSON-RPC for Zed / JetBrains (the IDE drives the harness as the primary agent). Not IBM ACP/A2A. Cursor uses MCP, not ACP. See [ACP (Zed / JetBrains)](guides/acp.md) and [CLI — acp](reference/cli.md#zaumzeug-acp).
- **`zaumzeug serve <harness>`** — interactive chat with the workflow **entry** agent (dev: `usr-harnesses/`). Use **`--deploy`** or **`HARNESS_ROOT=deploy`** to serve a production bundle from `deploy/<name>/` only (E5-S03 / E5-S04) — same OpenAI REST API; no `usr-harnesses/` required. Pipelines listed in **`serve.expose`** are also served as **`POST /{id}/run`** (E8-S01). Optional **`serve.hayhooks.chainlit: true`** serves Chainlit at `/chat` on the same port (`pip install "hayhooks[chainlit]"`). Other web clients (Open WebUI, SPA + Nginx, Next.js) use `baseURL` `http://127.0.0.1:1416/v1` (not `api.openai.com`). See [CLI — serve](reference/cli.md#zaumzeug-serve), [Pipelines and RAG](guides/pipelines.md), [Web deployment](guides/web-deployment.md), [Global environment](reference/cli.md#global-environment), and the bundle's `README.deploy.md`.
- **`zaumzeug run <harness>`** — run serial workflow stages in order (agent stages plus **`pipeline:`** YAML from `serve.expose` — E8-S01); optional `runtime.retry` / `output.format: json` / stage INFO logs (`HARNESS_LOG_LEVEL=INFO`) — see [Run reliability](guides/multi-agent-workflow.md#run-reliability-zaumzeug-run) (E8-S07; serve/HTTP does not share this layer yet) and [Pipelines and RAG](guides/pipelines.md)
- **`zaumzeug compile <harness>`** — run GEPA per agent (Phase 2, Pattern A); writes immutable `artifacts/<run_id>/` + `current` with Haystack export (`artifact-manifest.json`, prompts); regenerates `docs/workflow-diagram.md` (or use `--workflow-diagram-only`); use `--dry-run` to validate modules/registry without GEPA or LLM calls; pin/rollback to a prior run without re-GEPA — see [Compile and export — Rollback](guides/compile.md#rollback-to-a-pinned-run); optional `input_rewrite` is applied at serve/run time; Pattern B (`optimize_anything`) is available via `optimize_haystack_artifact` (E4-S04); live task/reflection models need API keys in `.env` (example uses mock/stub offline). See [Compile and export](guides/compile.md).
- **`zaumzeug eval <harness>`** — optional harness regression (E6-S02): `eval.framework: builtin` JSONL checks (no DeepEval) or `deepeval` metrics (needs `pip install "zaumzeug[eval]"`); CLI `--framework` override. Score a captured turn with `--trace data/traces/….jsonl` (E6-S05) without re-running the agent. Black-box a running serve with `--base-url` (Mode C / E6-S06) — staging/debug only. Optional `eval/` pytest scaffold via `zaumzeug init --with-eval` or the example harness — `deepeval test run usr-harnesses/<name>/eval/` (E6-S04). Failed eval → GEPA train via `append_failed_eval_to_train`; shared valset + optional DeepEval GEPA metrics in `modules/metrics.py` (E6-S07). See [Testing](guides/testing.md) (incl. [Journey C](guides/testing.md#trace--test-case-journey-c), [Mode C](guides/testing.md#mode-c--http-black-box-stagingdebug), and [GEPA ↔ DeepEval bridge](guides/testing.md#gepa--deepeval-bridge-compile--eval--compile)) and [CLI — eval](reference/cli.md#zaumzeug-eval).
- **`zaumzeug deploy <harness>`** — doctor preflight, eval gate (`deploy.eval_gate` / `--eval-gate`), then write `deploy/<name>/` (E5-S01 + E5-S02 copy matrix): stripped yaml, pinned artifacts, no `modules/`/`data/`/`eval/`/`skills/`, `manifest.json`, `README.deploy.md`, target install scripts. Ops then: copy bundle → `target_install` (venv / runtime `pip install zaumzeug` / `.env` seed / wrappers / optional `--verify` — **Done** E5-S09a/b/c) → `.env` → `zaumzeug serve <name> --deploy` or `zaumzeug mcp <name> --deploy` or `HARNESS_ROOT=deploy` (E5-S03–S05, E7-S06). See [Deploy and ship](guides/deploy.md), [CLI — deploy](reference/cli.md#zaumzeug-deploy), and [Testing — deploy gates](guides/testing.md).
