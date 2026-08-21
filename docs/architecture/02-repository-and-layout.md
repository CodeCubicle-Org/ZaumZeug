# Repository and layout

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 3. Repository structure

```text
HarnessDevelopment/
├── src/zaumzeug/          # SDK internals
│   ├── cli.py
│   ├── config/               # Pydantic schemas, loaders (E2-S01), models merge (E2-S02), resolver (E2-S03); CompileConfig (E4-S02a)
│   ├── doctor/               # Preflight checks — pass/warn/fail (E2-S04a–S04c, E4-S05 artifact_module, E4-S07 pinned_artifact, E7-S02 custom_tools)
│   ├── runtime/              # ModelRouter (E3-S01, E3-S05), factory (E3-S00), tools/ (E3-S03 web_fetch, E7-S07 calculator/read_file, E7-S01 MCP, E7-S02 custom), input_rewrite preprocess (E4-S03b)
│   ├── compile/              # DSPy loader; CLI + GEPA + --dry-run; export; workflow diagram; immutable runs (E4-S01–S08)
│   ├── deploy/               # Packager ✅ E5-S01; copy matrix ✅ E5-S02 (`resolve_deploy_copy_plan`); gate ✅ E6-S03/E5-S06; exclude/strip ✅ E6-S04 / E5-S01
│   ├── eval/                 # Optional DeepEval bridge — [eval] extra + require_deepeval() (E6-S01); zaumzeug eval runner (E6-S02); invoked by deploy gate (E6-S03); harness eval/ pytest scaffold (E6-S04); trace export + --trace (E6-S05); Mode C --base-url (E6-S06); GEPA bridge append_failed_eval_to_train + deepeval_gepa_metric (E6-S07)
│   ├── serve/                # validate_serve + dry-run (E2-S05); Hayhooks runner (E3-S02; input_rewrite on request path E4-S03b); optional Chainlit /chat (E7-S04); ACP stdio (E7-S05)
│   ├── integrations/         # mock (E3-S05), haystack provider map (E3-S01); DSPy, GEPA, LiteLLM adapters
│   └── fixtures/responses/   # bundled mock LLM fixtures (pip install; mirrors tests/fixtures/responses/)
├── usr-harnesses/<name>/         # USER dev workspace (author, compile, experiment)
├── deploy/<name>/            # PRODUCTION bundle (generated)
├── config/models.yaml        # Global model registry defaults
├── install/                  # client_install.py, client-install.sh/.ps1, target_install (+ templates)
├── user-docs/                # End-user manuals
├── docs/                     # PRD, architecture, ideation archive
└── tests/
```

### 3.1 Separation rules

| Path | Purpose | Edited by |
|---|---|---|
| `src/zaumzeug/` | Framework | Maintainers |
| `usr-harnesses/<name>/` | Development harness | Developer |
| `deploy/<name>/` | Production bundle | `zaumzeug deploy` only |
| `user-docs/` | Public docs | Docs authors |
| `docs/` | Internal design | Maintainers |

### 3.2 Package naming

**Resolved ([PRD §12](../prd.md#12-open-decisions-blockers-for-some-stories)):** product name **ZaumZeug**.

| Surface | Name |
|---|---|
| **Product / brand** | **ZaumZeug** |
| PyPI | `zaumzeug` |
| Import | `zaumzeug` |
| CLI | `zaumzeug` |
| Entry point | `zaumzeug = "zaumzeug.cli:main"` |
| Source layout | `src/zaumzeug/` |

**Domain terms:** `harness.yaml`, `usr-harnesses/`, `deploy/` refer to a **multi-agent harness instance**, not the product name and not a single agent. Env vars `HARNESS_ROOT`, `HARNESS_LOG_LEVEL` keep the domain prefix. **`HARNESS_ROOT=deploy`** ✅ (E5-S04, 2026-07-28) forces production root for serve/mcp/acp via `config/harness_root.py`.

### 3.3 Harness folder layout

Each harness lives under `usr-harnesses/<harness-name>/` (dev) or `deploy/<harness-name>/` (production subset). **Every agent** has a **uniquely named** subfolder under `agents/`:

```text
usr-harnesses/<harness-name>/
├── harness.yaml              # harness entry: name, serve, deploy, eval
├── workflow.yaml             # stage graph: which agents run, in what order (parallel later)
├── models.yaml               # optional harness-wide shared registry (aliases only)
├── agents/
│   ├── <agent-name>/         # unique agent id — folder name = agent name
│   │   ├── agent.yaml        # role config: prompts, tools, compile, hooks
│   │   ├── agents-models.yaml  # THIS agent's LLM registry (not models.yaml)
│   │   ├── prompts/
│   │   ├── tools/            # role-specific custom tools
│   │   ├── modules/          # DSPy modules (compile-time; excluded from deploy)
│   │   ├── skills/           # GEPA-optimizable skill files (dev)
│   │   ├── hooks.py          # optional lifecycle hooks for this role
│   │   └── artifacts/        # GEPA exports for this agent (pinned per agent on deploy)
│   └── <another-agent-name>/
│       ├── agent.yaml
│       ├── agents-models.yaml
│       └── ...
├── pipelines/                # Haystack YAML — deterministic steps, orchestration (Phase 4+)
├── data/                     # shared queue, context, train/val JSONL (dev); traces/ from E6-S05
├── docs/                     # generated harness docs (workflow-diagram.md at compile)
└── eval/                     # harness-level optional DeepEval pytest (dev only; E6-S04 scaffold)
    ├── test_*.py
    └── metrics.py
```

**Implementation (E6-S04, 2026-07-28):** Optional `eval/` scaffold via `zaumzeug init --with-eval` (template under `install/templates/harness/eval/`); example harness ships `eval/metrics.py` + `test_researcher.py`. Excluded from deploy by `deploy/copy_rules.py`. Run with `deepeval test run usr-harnesses/<name>/eval/` after `pip install "zaumzeug[eval]"`.

**Implementation (E6-S05, 2026-07-28):** Haystack runs export to `data/traces/*.jsonl` via `zaumzeug.eval.trace.export_haystack_trace`; score with `zaumzeug eval --trace`. See [user-docs/guides/testing.md](../user-docs/guides/testing.md#trace--test-case-journey-c).

**Implementation (E6-S06, 2026-07-28):** Mode C HTTP black-box — `zaumzeug eval --base-url` / `eval.base_url` against a running serve `/v1/chat/completions` (staging/debug). See [user-docs/guides/testing.md](../user-docs/guides/testing.md#mode-c--http-black-box-stagingdebug).

**Implementation (E6-S07, 2026-07-28):** GEPA ↔ DeepEval bridge — failed eval → `data/train.jsonl` via `eval/gepa_bridge.append_failed_eval_to_train`; shared val aliases; optional DeepEval GEPA metric in `agents/<agent>/modules/metrics.py` (compile auto-loads `metric`). Example researcher ships the template. See [testing.md — GEPA ↔ DeepEval bridge](../user-docs/guides/testing.md#gepa--deepeval-bridge-compile--eval--compile).

**Agent naming:** `<agent-name>` must be unique within the harness (e.g. `recon-analyst`, `vuln-hunter`, `finding-validator`). Used in `workflow.yaml` stage references and CLI (`zaumzeug compile <harness> --agent <agent-name>`).

**Extension points** (user folder only — never in `src/zaumzeug/`). Configuration is YAML-first; optional Python lives under `agents/<agent-name>/modules/`, `tools/`, or `hooks.py` — no top-level `harness.py` bootstrap file.

| Need | Where | How |
|---|---|---|
| Agent role config | `agents/<agent-name>/agent.yaml` | Prompts, tools, compile, hooks per role |
| Per-agent LLM | `agents/<agent-name>/agents-models.yaml` | Independent provider/model per agent |
| Workflow | `workflow.yaml` | Serial stages; `parallelism` per stage (later) |
| Custom agent logic | `agents/<agent-name>/modules/*.py` | DSPy `Module`; `compile.module` in `agent.yaml` (`module.path:ClassName`) |
| Custom tools | `agents/<agent-name>/tools/*.py` | `tools.custom` in `agent.yaml` ✅ (E7-S02) |
| Custom pipelines | `pipelines/` | YAML or `PipelineWrapper`; `serve.expose` in `harness.yaml` |
| GEPA metrics | `agents/<agent-name>/modules/metrics.py` | Textual feedback per agent; optional DeepEval `.measure()` via `deepeval_gepa_metric` (E6-S07) |
| DeepEval tests | `eval/test_*.py` | Harness-level; may target specific agents |
| Captured traces | `data/traces/*.jsonl` | Export Haystack runs; score with `zaumzeug eval --trace` (E6-S05) |
| Mode C HTTP eval | `zaumzeug eval --base-url` | Black-box a running serve `/v1/chat/completions` (E6-S06; staging/debug) |
| Failed eval → train | `zaumzeug.eval.gepa_bridge.append_failed_eval_to_train` | Append failing cases to `data/train.jsonl` for next compile (E6-S07) |
| Prompts / skills | `agents/<agent-name>/prompts/`, `skills/` | Per-agent; GEPA-optimized |
| Lifecycle hooks | `agents/<agent-name>/hooks.py` | Per-agent sensors |

**Implementation (E4-S01, 2026-07-28):** Compile-time loader `zaumzeug.compile.module_loader.load_dspy_module()` imports `compile.module` relative to `agents/<agent-name>/` (prepends that directory to `sys.path`; rejects traversal). Expects `module.path:ClassName` pointing at a `dspy.Module` subclass under `modules/`. Not used by serve/runtime. **2026-08-14:** drops a stale `sys.modules` chain before import so the same dotted name from another agent folder is not reused. Tests: `tests/unit/compile/test_module_loader.py`.

**Implementation (E7-S02, 2026-08-14):** Runtime loader `zaumzeug.runtime.tools.custom.load_custom_tools()` imports `tools.custom` relative to `agents/<name>/` (same sys.path + cache-drop pattern). Registers Haystack `ComponentTool` / `Tool`. Tests: `tests/unit/runtime/tools/test_custom_loader.py`.

**Implementation (E4-S02a, 2026-07-28):** `zaumzeug compile <harness> [--agent]` validates Phase 2 `CompileConfig` on `agent.yaml`, loads the DSPy module, and preflights task/reflection LM ids against the merged registry + `.env` (`compile/runner.py`, `compile/gepa_runner.py`).

**Implementation (E4-S06, 2026-07-28):** `zaumzeug compile <harness> --dry-run` reuses that validation path without GEPA, LLM calls, or artifact writes (`run_compile(..., dry_run=True)`). Tests: `tests/integration/compile/test_compile_dry_run.py`.

**Implementation (E4-S02b, 2026-07-28):** `invoke_gepa()` runs `dspy.GEPA` (or `StubGEPA` for mock/CI), wires LiteLLM strings, respects budget config, and writes immutable `artifacts/<run_id>/` + `artifacts/current` (symlink or copy). Tests: `pytest … -k e4_s02`.

#### 3.3.1 Model config files (naming)

Three distinct `models` files — do not conflate:

| File | Scope | Purpose |
|---|---|---|
| **`config/models.yaml`** | Project global | Shared defaults for all harnesses in the repo |
| **`usr-harnesses/<harness>/models.yaml`** | Harness (optional) | Shared registry aliases inherited by agents when not overridden |
| **`agents/<agent-name>/agents-models.yaml`** | **Single agent role** | LLM registry for that agent only — may use a completely different provider than sibling agents |

Each `agents-models.yaml` deep-merges over harness `models.yaml` (if present) over global `config/models.yaml`. When the workflow runs stage `finding-validator`, `ModelRouter` loads **that agent's** merged `agents-models.yaml` and `default_model_id` — not the previous stage's model.

Secrets remain in `.env` only; all model files hold provider + model id + generation kwargs.

### 3.4 Install scripts (dev vs target)

| Script | Scope | When |
|---|---|---|
| `install/client_install.py` | **Dev machine once** — venv, editable install, `usr-harnesses/example/`, user-docs skeleton, global `config/models.yaml`, `.env.example` | First clone or new dev machine |
| `install/target_install.py` | **Target machine once per deploy** — runtime `pip install zaumzeug`, optional `.venv`, seed `.env` from `.env.example` (never overwrite), preflight `harness.yaml` + `manifest.json`, optional `--verify` (doctor `--deploy` + serve `--deploy --dry-run`) | After copying `deploy/<name>/` to desktop PC or server. **E5-S01 (2026-07-28):** scripts + wrappers ship in each bundle; **E5-S05 (2026-07-28):** ship workflow docs ([deploy.md](../../user-docs/guides/deploy.md), `README.deploy.md`); **E5-S09a/b/c (2026-07-29):** full venv / pip / `.env` / wrappers / `--verify` ✅ |
| `zaumzeug init <name>` | **Per harness** — scaffold `usr-harnesses/<name>/` from template | Additional harnesses after project setup |
| `zaumzeug install-project` | **PyPI consumer cwd** — scaffold only (no editable install); reuses scaffold logic | **Deferred** until `zaumzeug` is published ([E1-S08](../stories/epic-stories/25-story.md); open #3 resolved 2026-07-22) |

**Wrappers:** `client-install.sh` / `client-install.ps1` delegate to `client_install.py`; `target-install.sh` / `target-install.ps1` delegate to `target_install.py`. OS-specific behavior lives only in the Python scripts ([§2.5](01-overview-and-principles.md#25-cross-platform-portability)).

**Dual install paths (PRD open #3 resolved, 2026-07-22):** Phase 1–4 v1 supports **clone + `install/client_install.py`** only. After PyPI publish, consumers use `pip install zaumzeug` then `zaumzeug install-project` (templates must ship in the wheel). Do not treat `install-project` as a Phase 1–4 v1 deliverable.

**Client install flags:** `--verify`, `--no-example`, `--skip-venv` (CI), `--cursor-mcp`. CI matrix **Done** ([PRD E1.7](../prd.md#epic-e1--onboarding-and-project-setup-phase-1) / [E1-S07](../stories/epic-stories/24-story.md), 2026-07-22) — [`.github/workflows/ci-matrix.yml`](../../.github/workflows/ci-matrix.yml).

**Target install flags:** `--deploy-dir` (default: cwd — typically the bundle root when run from `deploy/<name>/`), `--skip-venv`, `--verify` (doctor + serve dry-run). **Done** ([E5-S09a](../stories/epic-stories/49.1-story.md)–[E5-S09c](../stories/epic-stories/49.3-story.md), 2026-07-29). See [PRD E5.9](../prd.md#epic-e5--deploy-packaging-phase-2) and [§10.7](07-deploy-packaging.md#107-target-runtime-install-script).

**Updating dependencies (dev machine):** Re-run `client_install.py` after `git pull` (idempotent; refreshes `pip install -e ".[dev]"`). Optional extras and provider plugins use separate `pip install -U` commands. Production targets update via redeploy + bundled `target_install`, not ad hoc upgrades. User-facing summary: [PRD §7.4](../prd.md#74-user-installation-guide-content-for-readme--phase-1).

**Implementation (E1-S01, 2026-07-21):** `install/client_install.py` — creates `.venv` (unless `--skip-venv`), runs `pip install -e ".[dev]"`, parses `--verify` / `--no-example` / `--skip-venv` / `--cursor-mcp`, pathlib OS paths, non-blocking missing-`git` warning. Tests: `tests/unit/install/test_client_install.py`.

**Implementation (E1-S02, 2026-07-22):** Thin OS wrappers `install/client-install.sh` and `install/client-install.ps1` locate a working Python 3.11+ (`py -3` preferred on Windows to avoid Store stubs) and forward all args to `client_install.py` — no duplicated install logic. User-facing command table: [installation.md](../../user-docs/getting-started/installation.md). Tests: `tests/unit/install/test_wrappers.py`. Per-OS CI invocation closed by [E1-S07](../stories/epic-stories/24-story.md) (2026-07-22).

**Implementation (E5-S09a, 2026-07-29):** `install/target_install.py` — Python 3.11+ gate, optional `.venv` beside the bundle (`--skip-venv`), `pip install zaumzeug` (runtime only — no `[dev]`/`[eval]`/DSPy/GEPA/DeepEval), `zaumzeug --version` smoke, seed `.env` from `.env.example` at bundle or project root (never overwrite), preflight `harness.yaml` + `manifest.json`, idempotent. Tests: `tests/integration/deploy/test_target_install.py` (`e5_s09_*`).

**Implementation (E5-S09c, 2026-07-29):** `--verify` runs `zaumzeug doctor <name> --deploy` then `zaumzeug serve <name> --deploy --dry-run` from the project root (non-zero exit on failure). Tests: `e5_s09_ac4` / `e5_s09_ac6` / `e5_s09c_*`.

**Implementation (E5-S09b, 2026-07-29):** Thin OS wrappers `install/target-install.sh` and `install/target-install.ps1` locate Python 3.11+, forward all args to sibling `target_install.py` (works under `install/` and inside `deploy/<name>/`), propagate exit code. Bundled by packager `TARGET_INSTALL_FILES`. Tests: `tests/integration/deploy/test_target_install.py` (`e5_s09b_*`) + `test_deploy.py::test_e5_s09_ac7_scripts_in_bundle`.

**Implementation (E1-S03, 2026-07-22; `--cursor-mcp` live write E7-S03, 2026-08-21):** `scaffold_project()` in `client_install.py` — copy-if-missing from `install/templates/` for `usr-harnesses/example/` (skip with `--no-example`), `config/models.yaml` (from `models.example.yaml`), `.env.example`, `.cursor/mcp.json.example`, `user-docs/` skeleton; seeds `.env` only when missing; merges `.gitignore` entries (`.venv`, `.env`, `deploy/`, `artifacts/`). `--cursor-mcp` writes live `.cursor/mcp.json` (copy-if-missing; never overwrite). Tests: `tests/unit/install/test_scaffolding.py`, `tests/unit/install/test_client_install.py::test_e7_s03_ac3_cursor_mcp_flag_writes_json`.

**Implementation (E5-S07, 2026-07-28):** Scaffolding also ensures `usr-harnesses/*/artifacts/` (Architecture §10.4). Release-commit / CI upload policy: [§10.4](07-deploy-packaging.md#104-git-and-gitignore).

**Implementation (E1-S04, 2026-07-22):** `zaumzeug init <name>` in `src/zaumzeug/cli.py` + `zaumzeug.scaffold` — scaffolds `usr-harnesses/<name>/` from `install/templates/harness/` (Phase 1 minimal harness with mock agent); safe name validation; fails if exists unless `--force`; prints `doctor` / `serve` hints. Tests: `tests/unit/cli/test_init.py`. Docs: [project-setup.md](../../user-docs/getting-started/project-setup.md).

**Implementation (E1-S07, 2026-07-22):** Cross-platform CI matrix at [`.github/workflows/ci-matrix.yml`](../../.github/workflows/ci-matrix.yml) — `windows-latest` / `ubuntu-latest` / `macos-latest`, Python **3.11**, pip cache, fail-fast, 30m timeout; per-OS install wrappers → `zaumzeug doctor` → `serve --dry-run` → `install/ci_serve_smoke.py` (ephemeral `--port`, mock only) → OpenAI contract pytest → unit+integration suite. Tests: `tests/unit/ci/test_ci_matrix_workflow.py`, `tests/unit/install/test_ci_serve_smoke.py`.

### 3.5 User documentation

End-user docs live in `user-docs/` (Markdown) — separate from internal `docs/`. Install copies skeleton:

```text
user-docs/
├── README.md
├── getting-started/   # installation, project-setup, first-harness
├── guides/
│   ├── multi-agent-workflow.md   # workflow.yaml, agents vs pipelines, control flow
│   ├── compile.md                # GEPA compile / export / rollback
│   ├── deploy.md                 # copy → target_install → .env → serve --deploy (E5-S05); git policy (E5-S07); platforms (E5-S08); target install + --verify (E5-S09a/b/c); mcp --deploy (E7-S06)
│   ├── custom-tools.md           # tools.custom → ComponentTool / Tool (E7-S02); builtin catalog calculator/read_file (E7-S07)
│   ├── cursor-mcp.md             # Cursor mcp.json → localhost:{mcp_port}/mcp (E7-S03); --deploy (E7-S06)
│   ├── web-deployment.md         # Chainlit /chat co-located with REST (E7-S04)
│   ├── acp.md                    # zaumzeug acp stdio JSON-RPC for Zed / JetBrains (E7-S05); MCP --deploy pointer (E7-S06)
│   └── testing.md                # unit, integration, eval; mock profile; CI tiers; mcp --deploy (E7-S06)
└── reference/cli.md
```

Install copies this tree from `install/templates/user-docs/` ([§3.4](02-repository-and-layout.md#34-install-scripts-dev-vs-target)). End-user guides: [installation.md](../../user-docs/getting-started/installation.md), [project-setup.md](../../user-docs/getting-started/project-setup.md), [first-harness.md](../../user-docs/getting-started/first-harness.md), [multi-agent-workflow.md](../../user-docs/guides/multi-agent-workflow.md), [compile.md](../../user-docs/guides/compile.md), [deploy.md](../../user-docs/guides/deploy.md), [custom-tools.md](../../user-docs/guides/custom-tools.md), [cursor-mcp.md](../../user-docs/guides/cursor-mcp.md), [web-deployment.md](../../user-docs/guides/web-deployment.md), [acp.md](../../user-docs/guides/acp.md), [testing.md](../../user-docs/guides/testing.md).

**Implementation (E1-S03, 2026-07-22):** Install copies `install/templates/user-docs/` into project `user-docs/` (copy-if-missing). Content completeness (installation prerequisites / troubleshooting) → [E1-S05](../stories/epic-stories/22-story.md).

**Implementation (E1-S05, 2026-07-22):** Full `user-docs/` skeleton per §3.5 — `getting-started/installation.md` expands [PRD §7.4](../prd.md#74-user-installation-guide-content-for-readme--phase-1) (prerequisites, effort, disk, extras, updates, troubleshooting); Architecture §3.4 linked for technical install behavior only. Tests: `tests/unit/docs/test_user_docs_skeleton.py`.

**Implementation (E5-S05, 2026-07-28):** [user-docs/guides/deploy.md](../../user-docs/guides/deploy.md) — target ship workflow (copy → `target_install` → `.env` → `zaumzeug serve --deploy`); Win/macOS/Linux table; runtime-only deps. Bundle mirror: `install/templates/deploy/README.deploy.md`. Tests: `tests/integration/deploy/test_target_install.py`.

**Implementation (E5-S08, 2026-07-29):** Platform matrix (§10.6) in the same `deploy.md` / `README.deploy.md` — Linux-first production, OS-neutral bundle, Win/macOS best-effort not CI-gated, E8-S05 Dockerfile forward ref. Linux CI: `deploy` → `serve --deploy` smoke.

**Implementation (E7-S03, 2026-08-21):** [user-docs/guides/cursor-mcp.md](../../user-docs/guides/cursor-mcp.md) — Cursor `mcp.json` → `http://localhost:{mcp_port}/mcp` (default 1417); install `--cursor-mcp` writes live `.cursor/mcp.json`; `uv` only for stdio `tools.mcp`. Tests: `tests/unit/install/test_scaffolding.py::test_e7_s03_ac2_mcp_json_example_scaffolded`, `tests/unit/install/test_client_install.py::test_e7_s03_ac3_cursor_mcp_flag_writes_json`.

**Implementation (E7-S04, 2026-08-21):** [user-docs/guides/web-deployment.md](../../user-docs/guides/web-deployment.md) — optional Chainlit at `/chat` (`serve.hayhooks.chainlit: true` + `pip install "hayhooks[chainlit]"`). Open #2 (primary web UI) remains open.

**Implementation (E7-S05, 2026-08-21):** [user-docs/guides/acp.md](../../user-docs/guides/acp.md) — `zaumzeug acp` Agent Client Protocol stdio JSON-RPC; Zed `agent_servers` and JetBrains `~/.jetbrains/acp.json` snippets; ACP ≠ IBM A2A; Cursor uses MCP. Tests: `tests/integration/acp/test_acp_stdio.py`.

**Implementation (E7-S07, 2026-08-21):** Phase 3 builtin catalog — `calculator` and `read_file` (`runtime/tools/`); `search_docs` stays Phase 4. User guide: [custom-tools.md](../../user-docs/guides/custom-tools.md#builtin-catalog). Tests: `tests/unit/runtime/tools/test_extended_builtins.py`, `tests/unit/runtime/tools/test_read_file.py`.

**Implementation (E1-S06, 2026-07-22):** Short new-contributor onboarding guide at root [`CONTRIBUTING.md`](../../CONTRIBUTING.md) (product `README.md` unchanged) — vision, install table, `< 15 min` / `~1–2.5 GB` planning ranges, mock-first serve, optional extras, updating dependencies, abbreviated layout; links to [installation.md](../../user-docs/getting-started/installation.md) for depth. Tests: `tests/unit/docs/test_contributing_guide.py`.

**Implementation (E1-S02, 2026-07-22):** [user-docs/getting-started/installation.md](../../user-docs/getting-started/installation.md) documents OS install wrappers and flags (command table from [PRD §7.4](../prd.md#74-user-installation-guide-content-for-readme--phase-1)). Full prerequisites / troubleshooting → [E1-S05](../stories/epic-stories/22-story.md). Install template: `install/templates/user-docs/getting-started/installation.md`.

**Implementation (E1-S04, 2026-07-22):** [user-docs/getting-started/project-setup.md](../../user-docs/getting-started/project-setup.md) documents `zaumzeug init` and project layout. Install template: `install/templates/user-docs/getting-started/project-setup.md`. Remaining user-docs depth → [E1-S05](../stories/epic-stories/22-story.md).

**Implementation (E2-S06, 2026-07-08):** [user-docs/reference/cli.md](../../user-docs/reference/cli.md) documents `HARNESS_LOG_LEVEL`, `--verbose` on serve/compile, and related CLI flags. Install template: `install/templates/user-docs/reference/cli.md`.

---
