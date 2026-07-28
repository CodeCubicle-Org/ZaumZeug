# ZaumZeug — User documentation

End-user guides for building and running multi-agent harnesses. For SDK design and epics, see the internal `docs/` folder in the repository.

| Section | Audience | Contents |
|---|---|---|
| [Getting started](getting-started/) | New developers | Install, project layout, [first harness](getting-started/first-harness.md) |
| [Guides](guides/) | Day-to-day use | Workflow, agents, pipelines, compile, deploy |
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
| [Multi-agent workflow](guides/multi-agent-workflow.md) | `workflow.yaml`, agent vs pipeline stages, control flow inside agents |
| [Compile and export](guides/compile.md) | GEPA offline compile; Haystack artifact export; workflow diagram; optional runtime `input_rewrite`; pin/rollback to immutable `artifacts/<run_id>/` |
| [Deploy and ship](guides/deploy.md) | Copy `deploy/<name>/` → `target_install` → `.env` → `zaumzeug serve --deploy`; runtime-only install (no DSPy/GEPA/DeepEval); Win/macOS/Linux table (E5-S05); git policy for bundles (E5-S07); Linux-first platform matrix (E5-S08); target install — venv / pip / `.env` / wrappers / `--verify` (E5-S09a/b/c) |
| [Testing](guides/testing.md) | Unit, integration, eval layers; mock profile; optional `[eval]` / DeepEval (E6-S01); `zaumzeug eval` (E6-S02); deploy eval gate (E6-S03 / E5-S06); `eval/` pytest (E6-S04); trace → test case (E6-S05); Mode C HTTP `--base-url` (E6-S06); GEPA ↔ DeepEval bridge (E6-S07); deploy packager (E5-S01) + copy matrix (E5-S02); serve `--deploy` (E5-S03); `HARNESS_ROOT=deploy` (E5-S04); ship workflow (E5-S05); deploy git policy (E5-S07); platform policy + Linux deploy smoke (E5-S08); target install + `--verify` (E5-S09a/b/c); CI tiers |

## Quick links

- **`zaumzeug init <name>`** — scaffold a new harness under `usr-harnesses/`
- **`zaumzeug serve <harness>`** — interactive chat with the workflow **entry** agent (dev: `usr-harnesses/`). Use **`--deploy`** or **`HARNESS_ROOT=deploy`** to serve a production bundle from `deploy/<name>/` only (E5-S03 / E5-S04) — same OpenAI REST API; no `usr-harnesses/` required. See [CLI — serve](reference/cli.md#zaumzeug-serve) / [Global environment](reference/cli.md#global-environment) and the bundle's `README.deploy.md`.
- **`zaumzeug run <harness>`** — run serial workflow stages in order
- **`zaumzeug compile <harness>`** — run GEPA per agent (Phase 2, Pattern A); writes immutable `artifacts/<run_id>/` + `current` with Haystack export (`artifact-manifest.json`, prompts); regenerates `docs/workflow-diagram.md` (or use `--workflow-diagram-only`); use `--dry-run` to validate modules/registry without GEPA or LLM calls; pin/rollback to a prior run without re-GEPA — see [Compile and export — Rollback](guides/compile.md#rollback-to-a-pinned-run); optional `input_rewrite` is applied at serve/run time; Pattern B (`optimize_anything`) is available via `optimize_haystack_artifact` (E4-S04); live task/reflection models need API keys in `.env` (example uses mock/stub offline). See [Compile and export](guides/compile.md).
- **`zaumzeug eval <harness>`** — optional harness regression (E6-S02): `eval.framework: builtin` JSONL checks (no DeepEval) or `deepeval` metrics (needs `pip install "zaumzeug[eval]"`); CLI `--framework` override. Score a captured turn with `--trace data/traces/….jsonl` (E6-S05) without re-running the agent. Black-box a running serve with `--base-url` (Mode C / E6-S06) — staging/debug only. Optional `eval/` pytest scaffold via `zaumzeug init --with-eval` or the example harness — `deepeval test run usr-harnesses/<name>/eval/` (E6-S04). Failed eval → GEPA train via `append_failed_eval_to_train`; shared valset + optional DeepEval GEPA metrics in `modules/metrics.py` (E6-S07). See [Testing](guides/testing.md) (incl. [Journey C](guides/testing.md#trace--test-case-journey-c), [Mode C](guides/testing.md#mode-c--http-black-box-stagingdebug), and [GEPA ↔ DeepEval bridge](guides/testing.md#gepa--deepeval-bridge-compile--eval--compile)) and [CLI — eval](reference/cli.md#zaumzeug-eval).
- **`zaumzeug deploy <harness>`** — doctor preflight, eval gate (`deploy.eval_gate` / `--eval-gate`), then write `deploy/<name>/` (E5-S01 + E5-S02 copy matrix): stripped yaml, pinned artifacts, no `modules/`/`data/`/`eval/`/`skills/`, `manifest.json`, `README.deploy.md`, target install scripts. Ops then: copy bundle → `target_install` (venv / runtime `pip install zaumzeug` / `.env` seed / wrappers / optional `--verify` — **Done** E5-S09a/b/c) → `.env` → `zaumzeug serve <name> --deploy` or `HARNESS_ROOT=deploy` (E5-S03–S05). See [Deploy and ship](guides/deploy.md), [CLI — deploy](reference/cli.md#zaumzeug-deploy), and [Testing — deploy gates](guides/testing.md).
