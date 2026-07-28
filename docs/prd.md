# ZaumZeug — Product Requirements Document

**Last updated:** 2026-07-28 (E6-S07 GEPA ↔ DeepEval bridge)  
**Status:** Phase 1 complete (E2 + E3 + E1-S01–S07); E1-S08 deferred (post–PyPI publish); Phase 2 in progress (E4 **Done**; E6-S01–S07 **Done**; E5-S06 **Done** early with E6-S03; next E5-S01 packager body)  

**Related:** [Architecture](architecture.md) · [Ideation archive](ideation-stage.md) · [Stories](stories/00-README.md)

**Document scope:** This PRD defines **what** to build — goals, users, journeys, epics, acceptance criteria, phases, and open decisions. Technical **how** (stack, flows, protocols, repo layout, SDK modules) lives in **[architecture.md](architecture.md)** and topic files under **[architecture/](architecture/00-README.md)**. Cross-reference; do not duplicate.

This PRD is structured for **epic → feature → story** breakdown. Each feature includes acceptance criteria (AC) ready to become tickets.

---

## 1. Executive summary

Build **ZaumZeug** — a harness library (SDK) and factory for configurable **multi-agent harnesses**. A harness is a **workflow** plus a **collection of named agents** (each with its own `agents-models.yaml`), not a relabeled single agent. Developers scaffold a folder, edit YAML, add Python only where needed, and ship a **production bundle** to any host without touching Haystack, DSPy, or GEPA internals.

**Formula:** `Harness = Workflow + Agents + Machinery`. We build the factory, not one harness.

See [Architecture §2.2.1](architecture/01-overview-and-principles.md#221-harness-vs-agent-terminology) for the multi-agent harness model. [cloudflare-harness.md](cloudflare-harness.md) is an **illustrative example only** (not a ZaumZeug deliverable).

---

## 2. Problem and opportunity

| Problem | Opportunity |
|---|---|
| Haystack + DSPy + GEPA integration is complex and easy to mix compile/runtime incorrectly | Single SDK with enforced golden rules and CLI workflow |
| No clear dev vs production artifact boundary | `usr-harnesses/` for dev, `deploy/` for shipping |
| Model provider lock-in in many agent codebases | Per-agent `agents-models.yaml` + stage-scoped `ModelRouter` |
| Cursor, web apps, and Zed need different protocols | One Haystack core, multiple serve surfaces |

---

## 3. Goals

| ID | Goal |
|---|---|
| G1 | Developer creates a working **multi-agent harness** from YAML + optional Python extensions (serial workflow first; parallel fan-out later) |
| G2 | Strict compile-time (DSPy/GEPA) vs runtime (Haystack) separation |
| G3 | Model-agnostic operation via configuration |
| G4 | One-command onboarding and local dev on Windows, macOS, and Linux (CI-verified) |
| G5 | Clear production deploy path (`zaumzeug deploy` → ship `deploy/` → `target_install` on target host) |
| G6 | Easy to debug and test (doctor, dry-run, mock LM, optional DeepEval) |

---

## 4. Non-goals (v1)

| ID | Non-goal |
|---|---|
| NG1 | Multi-tenant single Hayhooks process hosting many harnesses (deferred) |
| NG2 | Mandatory DeepEval for end users |
| NG3 | Compiling or running GEPA on production servers |
| NG4 | Sandbox / isolated code execution (Phase 4+ consideration) |
| NG5 | Building a hosted SaaS platform |
| NG6 | Replacing Haystack, DSPy, or GEPA — we integrate them |

---

## 5. Users and personas

| Persona | Needs |
|---|---|
| **Harness developer** | Scaffold harness, configure models/tools, compile, deploy |
| **SDK maintainer** | Extend SDK, example harness, CI, docs |
| **Ops / platform** | Run `deploy/<name>/` on server with `.env` and `zaumzeug serve --deploy` |
| **Client integrator** | Call harness via REST, MCP, or ACP from app or IDE |

---

## 6. Product principles

Product-facing rules. Technical implications: [Architecture §2](architecture/01-overview-and-principles.md#2-architectural-principles).

1. **Configuration first** — YAML wires capabilities; code only for custom logic.
2. **Compile ≠ runtime** — see Architecture golden rules.
3. **Dev ≠ deploy** — `usr-harnesses/` vs `deploy/`; see [Architecture §3](architecture/02-repository-and-layout.md#3-repository-structure).
4. **Models are config** — [Architecture §7](architecture/05-configuration.md#7-model-routing).
5. **Optional eval** — DeepEval helps development; not required to ship ([Architecture §13](architecture/10-operations-and-reference.md#13-debug-and-test-architecture)).
6. **Fail fast** — Pydantic + `zaumzeug doctor` ([Epic E2](#epic-e2--configuration-and-validation-phase-1)).

---

## 7. User journeys

### 7.1 Journey A — Config-only harness (Phase 1)

```text
install → zaumzeug serve example (mock model, no API keys) → REST chat
→ optional: set .env + default_model_id → live model
```

CI and first-run docs use **`default_model_id: mock`** in the example harness ([Architecture §6.6](architecture/05-configuration.md#66-phase-1-config-schema)).

### 7.2 Journey B — Full lifecycle (Phase 2–3)

```text
zaumzeug init → edit harness.yaml → zaumzeug compile → zaumzeug deploy
→ copy deploy/<name>/ to target → target_install (Win/macOS/Linux server or desktop)
→ zaumzeug serve --deploy → zaumzeug mcp for Cursor
```

### 7.3 Journey C — Improve after failure (Phase 2+)

```text
production trace → add to valset → zaumzeug eval (optional) → zaumzeug compile
→ zaumzeug deploy → redeploy
```

**Implementation (E6-S05, 2026-07-28):** Manual/API export via `zaumzeug.eval.trace.export_haystack_trace` → `data/traces/`; score with `zaumzeug eval --trace`; append with `append_trace_to_valset`. Walkthrough: [user-docs/guides/testing.md](user-docs/guides/testing.md#trace--test-case-journey-c).

**Implementation (E6-S07, 2026-07-28):** Failed eval → `data/train.jsonl` via `append_failed_eval_to_train`; shared val aliases; optional DeepEval GEPA metric in `modules/metrics.py`. Compile → eval → compile loop: [testing.md — GEPA ↔ DeepEval bridge](user-docs/guides/testing.md#gepa--deepeval-bridge-compile--eval--compile). Production auto-capture remains [E8-S03](stories/epic-stories/60-story.md).

### 7.4 User installation guide (content for README — Phase 1)

**When to publish:** Create root `README.md` in **Phase 1** when `install/client_install.py` and the `harness` CLI exist ([E1.6](#epic-e1--onboarding-and-project-setup-phase-1)). Do not ship install commands before the install path is stable.

**Doc split:**

| Audience need | Root `README.md` | `user-docs/getting-started/installation.md` |
|---|---|---|
| Quick start | Summary (this section, abbreviated) | Full walkthrough |
| Prerequisites, effort, disk | Short tables + links | Expanded notes and troubleshooting |
| OS-specific commands | Install command table | Step-by-step per OS |
| Optional extras | Bullet list | When to install each extra |
| **Updating dependencies** | Short “when / how” table + commands | Full scenarios, PyPI consumers, production |

Technical install behavior (script steps, flags, idempotency): [Architecture §3.4](architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target). This section defines **what users should read** about onboarding and dependency updates — not SDK internals.

#### Prerequisites

| Requirement | Required? | Notes |
|---|---|---|
| **Python 3.11+** | Yes | Only hard prerequisite for dev install |
| **Git** | Optional | Install script warns if missing; not blocking |
| **`uv` / `uvx`** | Optional | Needed when harness uses MCP tool servers; `zaumzeug doctor` warns — not blocking for Phase 1 serve |
| **API keys** (`.env`) | To run live models | Not part of install; user sets after scaffold from `.env.example` |

Users do **not** manually install Haystack, DSPy, GEPA, or LiteLLM for the default dev path — `client_install.py` runs `pip install -e ".[dev]"` inside a project `.venv`.

#### Effort and complexity (user expectations)

| Question | User-facing answer |
|---|---|
| Is setup complicated? | **No** — one install script, one venv, one editable install; idempotent re-run |
| How long to first harness? | **Target < 15 minutes** on CI and typical broadband (mock model, no API keys); **up to ~30 minutes** on slow networks — see [§11](#11-success-metrics) |
| What does install do? | Creates `.venv`, editable `[dev]` install, scaffolds `usr-harnesses/example/`, `user-docs/`, `config/models.yaml`, `.env.example` / seeded `.env` (never overwrite), `.cursor/mcp.json.example`, and `.gitignore` entries; optional `--verify` runs `zaumzeug doctor` |

**Install commands (must appear in README install table):**

| OS | Command |
|---|---|
| **Windows** (PowerShell) | `.\install\client-install.ps1` |
| **Windows** (cmd) | `python install\client_install.py` |
| **macOS / Linux** | `./install/client-install.sh` |
| **Any OS** | `python install/client_install.py` |

**First commands after install (README quick start):**

Use the **mock model** first (no API keys). Example harness ships with `default_model_id: mock` ([Architecture §6.6](architecture/05-configuration.md#66-phase-1-config-schema)).

```powershell
# Windows
.\.venv\Scripts\Activate.ps1
zaumzeug serve example              # mock model — no .env required
# optional live model: edit .env, set runtime.default_model_id in harness.yaml, pip install provider package
```

```bash
# macOS / Linux
source .venv/bin/activate
zaumzeug serve example              # mock model — no .env required
# optional live model: edit .env, set runtime.default_model_id in harness.yaml, pip install provider package
```

Optional install flags (same on all platforms): `--verify`, `--no-example`, `--skip-venv`, `--cursor-mcp` — see [Architecture §3.4](architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target).

#### Disk space (planning estimates — document as ranges, not guarantees)

No pinned size until `pyproject.toml` locks dependencies; README must set expectations with **approximate ranges** and note that first `pip install` dominates download time.

| Component | Approximate size |
|---|---|
| **Dev install** (`.venv`, editable `[dev]`: Haystack, Hayhooks, DSPy, GEPA, LiteLLM) | **~1–2.5 GB** |
| **+ `[eval]` / DeepEval** | **+200–500 MB** |
| **+ provider packages** (install only what you use) | **+50–200 MB** |
| **`uv`** (optional, separate from venv) | **~50–100 MB** |
| **Repo + harness folders** (excluding artifacts) | **< 50 MB** |
| **Compile artifacts** (`usr-harnesses/*/artifacts/`) | Variable over time |

**Production target install** (`target_install` on server/desktop after copying `deploy/<name>/`): runtime `zaumzeug` only — **no** DSPy, GEPA, or DeepEval — approximately **~500 MB–1.5 GB** for the venv. Python 3.11+ must already be on the target; see [E5.9](#epic-e5--deploy-packaging-phase-2).

#### Optional extras (not required to start a harness)

| Feature | Extra install | When needed |
|---|---|---|
| **Compile / GEPA** | Included in `[dev]` | Offline prompt optimization (`zaumzeug compile`) |
| **DeepEval** | `pip install "zaumzeug[eval]"` | Dev regression only — `[eval]` extra **Done** (E6-S01, 2026-07-28); `zaumzeug eval` CLI **Done** (E6-S02, 2026-07-28) |
| **Provider plugins** | e.g. `openai-haystack`, `anthropic-haystack` | Only configured providers |
| **MCP in Cursor** | `uv` + `--cursor-mcp` | Phase 3 IDE integration |
| **Chainlit UI** | `hayhooks[chainlit]` | Phase 3 embedded `/chat` |

#### Updating dependencies (must appear in README)

There is **no `zaumzeug update-deps` command in v1**. Updates stay **pip-based** and use the same install path where possible. README must include a short **“Updating dependencies”** subsection (link to `user-docs/getting-started/installation.md` for detail).

**Design principle:** Users do **not** manage Haystack, DSPy, GEPA, or LiteLLM versions individually on the default dev path — `zaumzeug` (`[dev]` extra) pulls the stack. Optional extras and provider plugins are installed separately.

| Situation | User-facing steps |
|---|---|
| **After `git pull`** (SDK repo clone) | Re-run the same client install command (idempotent); then `zaumzeug doctor` or install with `--verify` |
| **Refresh SDK + `[dev]` stack manually** | Activate `.venv`, then `pip install -e ".[dev]"`, then `zaumzeug doctor` |
| **Update optional extras** | `pip install -U "zaumzeug[eval]"`, provider packages, or `hayhooks[chainlit]` as needed |
| **Production server** | Ship new `deploy/<name>/` bundle → re-run bundled `target_install` (idempotent); do not `pip upgrade` ad hoc on server — see [E5.9](#epic-e5--deploy-packaging-phase-2) |
| **PyPI consumer project** (deferred — [E1-S08](stories/epic-stories/25-story.md); after package publish) | `pip install -U zaumzeug` then `zaumzeug install-project` (optionally pin `zaumzeug==x.y.z`) |

**README commands — dev machine after pull:**

```powershell
# Windows — refresh deps after git pull
git pull
.\install\client-install.ps1 --verify
```

```bash
# macOS / Linux — refresh deps after git pull
git pull
./install/client-install.sh --verify
```

**README commands — manual refresh in venv:**

```bash
source .venv/bin/activate   # or Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
zaumzeug doctor
```

**README note for production:** Runtime deps on the target are updated by **redeploying** (`zaumzeug deploy` → copy bundle → `target_install`), not by upgrading packages in place. The bundle pins harness config and artifacts; pip lockfiles for deploy are **not** required in v1.

Phase 1 minimum path: install → `zaumzeug serve example` with **mock model** (no `.env`) → optional `.env` + provider package for live models.

---

## 8. Functional requirements (epics)

Epic IDs map to phases. Features use `E#.#` IDs for story parent links.

---

### Epic E1 — Onboarding and project setup (Phase 1)

**Outcome:** Developer clones repo and runs a harness in one session.

| ID | Feature | Acceptance criteria |
|---|---|---|
| E1.1 | Cross-platform install | **Done** (E1-S01, 2026-07-21) — `install/client_install.py` runs on Win/macOS/Linux with Python 3.11+; creates `.venv`; `pip install -e ".[dev]"` succeeds per [Architecture §4.4](architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub); idempotent re-run. Supports flags: `--verify`, `--no-example`, `--skip-venv`, `--cursor-mcp` (see [Architecture §3.4](architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)). Three-OS CI matrix **Done** ([E1-S07](stories/epic-stories/24-story.md), 2026-07-22) — [`.github/workflows/ci-matrix.yml`](../.github/workflows/ci-matrix.yml). |
| E1.2 | Install wrappers | **Done** (E1-S02, 2026-07-22) — `client-install.sh` and `client-install.ps1` delegate to `client_install.py` with forwarded flags; no duplicated install logic. Command table: [user-docs/getting-started/installation.md](../user-docs/getting-started/installation.md). Per-OS CI wrapper invocation **Done** ([E1-S07](stories/epic-stories/24-story.md), 2026-07-22) — matrix runs wrappers on Win/macOS/Linux. |
| E1.3 | Project scaffolding | **Done** (E1-S03, 2026-07-22) — Install copies `usr-harnesses/example/`, `user-docs/` skeleton, `config/models.yaml`, `.env.example`, `.cursor/mcp.json.example`; updates `.gitignore` for `.venv`, `artifacts/`, `deploy/`, `.env`. Never overwrites existing `.env`. `--no-example` skips harness copy. Tests: `tests/unit/install/test_scaffolding.py`. |
| E1.4 | `zaumzeug init` | **Done** (E1-S04, 2026-07-22) — `zaumzeug init <name>` scaffolds `usr-harnesses/<name>/` from `install/templates/harness/` (minimal `harness.yaml` with serve + optional `models`, workflow, mock agent + system prompt). Safe name validation; fails if exists unless `--force`. Module: `zaumzeug.scaffold`. Tests: `tests/unit/cli/test_init.py`. Docs: [project-setup.md](../user-docs/getting-started/project-setup.md). |
| E1.5 | `user-docs/` skeleton | **Done** (E1-S05, 2026-07-22) — After install: `README.md`, `getting-started/` (installation, project-setup, first-harness), `reference/cli.md`, `guides/multi-agent-workflow.md`, `guides/testing.md`. **`getting-started/installation.md`** expands [§7.4](#74-user-installation-guide-content-for-readme--phase-1) (prerequisites, effort, disk ranges, optional extras, **updating dependencies**, troubleshooting). Structure per [Architecture §3.5](architecture/02-repository-and-layout.md#35-user-documentation). Tests: `tests/unit/docs/test_user_docs_skeleton.py`. |
| E1.6 | Root README / new-contributor guide | **Done** (E1-S06, 2026-07-22) — Short entry point as root [`CONTRIBUTING.md`](../CONTRIBUTING.md) (product [`README.md`](../README.md) kept as overview): vision one-liner; install command table and quick start from [§7.4](#74-user-installation-guide-content-for-readme--phase-1) (prerequisites summary, **< 15 min target** / **~1–2.5 GB** dev venv planning ranges, mock-first serve, optional extras bullet list, **updating dependencies** summary with post-`git pull` re-install commands); first commands (`zaumzeug serve example`); abbreviated project layout; links to `user-docs/getting-started/installation.md` for depth — not a duplicate of user-docs. Tests: `tests/unit/docs/test_contributing_guide.py`. |
| E1.7 | Cross-platform CI matrix | **Done** (E1-S07, 2026-07-22) — [`.github/workflows/ci-matrix.yml`](../.github/workflows/ci-matrix.yml) runs on `windows-latest`, `ubuntu-latest`, and `macos-latest` (Python 3.11, pip cache, fail-fast, 30m timeout). Each job: OS install wrappers with `--skip-venv --verify`, `zaumzeug doctor`, `zaumzeug serve example --dry-run`, mock serve smoke via `install/ci_serve_smoke.py` (ephemeral port, no live API keys), `pytest tests/integration/test_openai_contract.py`, and unit+integration suite. Story: [24-story.md](stories/epic-stories/24-story.md). |

**Deferred (E1-S08, decision resolved 2026-07-22):** `zaumzeug install-project` scaffolds `usr-harnesses/`, `user-docs/`, `.env` in a consumer cwd — reuses `client_install.py` scaffold logic without editable repo install. **Not Phase 1–4 v1;** implement when publishing `zaumzeug` to PyPI (templates must ship in the wheel). Until then, the supported path is clone + `install/client_install.py`.

**Story seeds:** Install on Windows; install in CI with `--skip-venv --verify`; init second harness; CI matrix fails fast on path or shell assumptions.

---

### Epic E2 — Configuration and validation (Phase 1)

**Outcome:** Multi-agent harness config loads, merges, and validates (`harness.yaml`, `workflow.yaml`, `agents/<name>/`, `agents-models.yaml`).

| ID | Feature | Acceptance criteria |
|---|---|---|
| E2.1 | Pydantic config schemas | **AC:** Invalid yaml fails with field-level errors; [Architecture §6.6](architecture/05-configuration.md#66-phase-1-config-schema) Phase 1 example passes; unknown sections/fields for current phase fail with phase hint. **Implemented** (E2-S01, 2026-07-08): `zaumzeug.config.load_harness`, `HarnessConfig`; tests in `tests/unit/config/test_schemas.py`. |
| E2.2 | Model registry merge | **AC:** Three-tier merge per [Architecture §6.1](architecture/05-configuration.md#61-model-registry-merge): global → harness `models.yaml` → per-agent `agents-models.yaml`; recursive dict merge; list replace; missing `default_model_id` per agent fails validation. |
| E2.3 | Runtime resolution | **AC:** Per-agent: serve loads `artifact` > `system_prompt` > error; compile requires `compile.module` in `agent.yaml`. Workflow `entry` agent used for interactive serve. ([Architecture §5.2](architecture/04-data-flows.md#52-runtime-agent-resolution).) |
| E2.4 | `zaumzeug doctor` | **AC:** Checks Python version, install, `.env`, config validity (including `eval` section when present — warn), every agent runtime path, every `agents-models.yaml`, workflow.yaml consistency, stale workflow diagram warn, ports (warn), uv when MCP configured. **Also (E4-S05):** warn when compiled artifact `source_hash` drifts from `compile.module` source. Supports `--verbose`, `--json`; optional harness name or project-wide. |
| E2.5 | `--dry-run` on serve | **AC:** Validates and prints resolved config without starting server or calling LLM. |
| E2.6 | Logging | **AC:** `--verbose` on serve/compile/run and `HARNESS_LOG_LEVEL=DEBUG` enable SDK + Haystack structured logging (harness, agent, model_id, tool, artifact path per request). |
| E2.7 | `workflow.yaml` schema | **AC:** Validates serial `stages` list (`agent` or `pipeline` refs); unique agent folder names; `entry` stage exists; rejects unknown agent refs. Parallelism field rejected in Phase 1 (phase hint). |

**Story seeds:** Unit tests for merge rules; doctor fails on missing artifact and system_prompt.

---

### Epic E3 — Runtime and local serve (Phase 1)

**Outcome:** Multi-agent harness runs locally: interactive serve (entry agent) and serial workflow execution.

| ID | Feature | Acceptance criteria |
|---|---|---|
| E3.1 | ModelRouter | **Done** (E3-S01, 2026-07-08; HTTP override E3-S07, 2026-07-21) — Stage-scoped `ModelRouter` reads active agent's merged `agents-models.yaml`; optional request `model_id` override on `POST /v1/chat/completions`; lazy-builds `ChatGenerator` per provider; OpenRouter when `provider: openrouter`; `openai_compatible` with `api_base_url` for local OpenAI-compatible servers (LM Studio, etc.); fails fast if provider package missing; no hardcoded models. ([Architecture §7](architecture/05-configuration.md#7-model-routing).) |
| E3.2 | `zaumzeug serve` (dev) | **Done** (E3-S02, 2026-07-20) — Loads `usr-harnesses/<name>/`; runs workflow `entry` agent; starts Hayhooks on configured port (optional `--port` override); `/v1/chat/completions` returns response. OpenAI contract suite **Done** ([E3-S07](stories/epic-stories/16-story.md), 2026-07-21). Three-OS CI matrix + mock serve smoke **Done** ([E1-S07](stories/epic-stories/24-story.md), 2026-07-22) — `install/ci_serve_smoke.py` in [`.github/workflows/ci-matrix.yml`](../.github/workflows/ci-matrix.yml). |
| E3.3 | Builtin tools | **AC:** Phase 1 ships `web_fetch`; catalog in [Architecture §6.5](architecture/05-configuration.md#65-builtin-tools-catalog). |
| E3.4 | Example harness | **AC:** `example` uses multi-agent layout ([Architecture §6.6](architecture/05-configuration.md#66-phase-1-config-schema)): `agents/researcher/`, `workflow.yaml` (one stage), `web_fetch`, `default_model_id: mock`; `zaumzeug serve example` works without `.env`. |
| E3.5 | Mock model profile | **AC:** `mock` provider in `agents-models.yaml`; canned responses from `tests/fixtures/responses/`; CI uses mock exclusively. |
| E3.6 | `zaumzeug run` (serial workflow) | **AC:** Executes `workflow.yaml` stages in order; each agent stage uses that agent's config and `agents-models.yaml`; passes prior stage output as context to next; pipeline stages invoke exposed Haystack pipelines (when present). Fails fast on missing agent. **Serial only** in Phase 1. |

**Story seeds:** Integration test with mock LM; OpenAI-shaped request/response contract test — **Done** (E3-S07, 2026-07-21).

---

### Epic E4 — Compile and GEPA pipeline (Phase 2)

**Outcome:** Offline GEPA per agent; harness workflow diagram regenerated at every compile.

| ID | Feature | Acceptance criteria |
|---|---|---|
| E4.1 | DSPy module loader | **Done** (E4-S01, 2026-07-28) — `zaumzeug.compile.module_loader.load_dspy_module()` loads `compile.module` (`module.path:ClassName`) from `agents/<name>/agent.yaml`; safe agent-dir `sys.path`; validates `dspy.Module` subclass; compile-only (not on serve/runtime import graph). Tests: `tests/unit/compile/test_module_loader.py`. |
| E4.2 | GEPA compile | **Done** (E4-S02a+b, 2026-07-28) — Phase 2 `CompileConfig`; `zaumzeug compile` loads modules, preflights LMs, runs `dspy.GEPA` (stub for mock/CI), writes `artifacts/<run_id>/` + `current`. Tests: `-k e4_s02`. |
| E4.3 | Export contract | **AC:** `dump_state()` maps to Haystack `system_prompt`, tool descriptions, pipeline Jinja templates; `artifact-manifest.json` per run; golden snapshot tests. Optional input rewrite template per agent. **E4-S03a Done** (2026-07-28); **E4-S03b Done** (2026-07-28) — runtime preprocess. |
| E4.4 | Haystack GEPA evaluator (Pattern B) | **Done** (E4-S04, 2026-07-28) — `compile/gepa_adapter.py`: `HaystackGepaAdapter` + `optimize_haystack_artifact`; modes `single-task` \| `multi-task` \| `generalization`; `CompileConfig` `optimizer`/`mode`/`seed_artifact`. CLI `zaumzeug compile` remains Pattern A. Tests: `tests/unit/compile/test_gepa_adapter.py` (5 passed, 0 skipped). |
| E4.5 | Post-compile serve | **Done** (E4-S05, 2026-07-28) — After compile, serve/run prefer valid `agent.artifact` over hand-edited `system_prompt`; `compile.module` not imported at serve; optional `input_rewrite` preprocess; doctor warns on stale `source_hash`. Tests: 12 passed, 0 skipped (`test_compile_serve.py` + `test_e4_s05_ac5_stale_artifact_warn`). Docs: [guides/compile.md — Serve after compile](user-docs/guides/compile.md#serve-after-compile). |
| E4.6 | `--dry-run` on compile | **Done** (E4-S06, 2026-07-28) — `zaumzeug compile --dry-run` validates Phase 2 schema, resolves module imports, prints task/reflection registry; no GEPA, no LLM calls, no artifacts. Tests: `tests/integration/compile/test_compile_dry_run.py` (5 passed). Docs: [CLI reference](user-docs/reference/cli.md#zaumzeug-compile). |
| E4.7 | Workflow diagram | **Done** (E4-S08, 2026-07-28) — Every `zaumzeug compile` regenerates `docs/workflow-diagram.md` (Mermaid) from `workflow.yaml` + resolved agents/models; `--workflow-diagram-only` skips GEPA; doctor warns if stale; deploy copies to `deploy/<harness>/docs/` (E5-S02). ([Architecture §5.4](architecture/04-data-flows.md#54-workflow-diagram-compile).) |

**Phase 2 compile scope (resolved):** **Pattern A** (`dspy.GEPA`) is the default `zaumzeug compile` path — optimize prompts/signatures via DSPy modules, export to Haystack artifacts. **Optional within Pattern A:** compile-time GEPA on **input rewrite/clarify templates** (how the harness preprocesses user messages — not optimization of end-user chat at runtime). **Pattern B** (`optimize_anything` / Haystack evaluator) **shipped early** (E4-S04, 2026-07-28) as a programmatic adapter + schema; not wired into the CLI compile path yet.

**Story seeds:** DSPy module loader **Done** (E4-S01). Compile CLI + GEPA runner + artifacts **Done** (E4-S02a/b, 2026-07-28). Export contract **Done** (E4-S03a, 2026-07-28). Runtime `input_rewrite` preprocess **Done** (E4-S03b, 2026-07-28). Haystack GEPA evaluator / Pattern B **Done** (E4-S04, 2026-07-28). Post-compile serve uses artifact **Done** (E4-S05, 2026-07-28). Compile `--dry-run` **Done** (E4-S06, 2026-07-28). Rollback to pinned `artifacts/<run_id>` **Done** (E4-S07, 2026-07-28) — immutable runs, doctor pin check, [rollback guide](user-docs/guides/compile.md#rollback-to-a-pinned-run). Workflow diagram at compile **Done** (E4-S08, 2026-07-28) — Mermaid `docs/workflow-diagram.md`, `--workflow-diagram-only`, golden snapshot.

---

### Epic E5 — Deploy packaging (Phase 2)

**Outcome:** Production bundle separated from dev workspace.

| ID | Feature | Acceptance criteria |
|---|---|---|
| E5.1 | `zaumzeug deploy` | **AC:** Writes `deploy/<name>/` with stripped yaml, `workflow.yaml`, per-agent runtime files, `docs/workflow-diagram.md`, pinned per-agent artifacts, `manifest.json`, `README.deploy.md`, target install scripts. |
| E5.2 | Exclude dev files | **AC:** Packager copy rules per [Architecture §10.1](architecture/07-deploy-packaging.md#101-dev-vs-deploy): `agents/<name>/` runtime subset; exclude `modules/`, `data/`, `eval/`, `skills/`; include `docs/workflow-diagram.md`. |
| E5.3 | `zaumzeug serve --deploy` | **AC:** Loads only from `deploy/<name>/`; same API as dev serve. |
| E5.4 | `HARNESS_ROOT=deploy` | **AC:** Env var forces deploy root for serve/mcp/acp/run. Default dev root is `usr-harnesses/`. |
| E5.5 | Target ship workflow | **AC:** Documented path: copy `deploy/<name>/` to target machine → run bundled `target_install` (or `install/target_install.py --deploy-dir …`) → create `.env` → `zaumzeug serve <name> --deploy`. Installs runtime deps only (`pip install zaumzeug` — Haystack/Hayhooks via SDK); **no** DSPy/GEPA/DeepEval. Python 3.11+ must already be on the target. |
| E5.6 | Deploy eval gate | **Done** (E5-S06 / E6-S03, 2026-07-28). **AC:** `deploy.eval_gate` (`skip` \| `warn` \| `block`) and `--eval-gate` CLI override behave per [Architecture §6.4](architecture/05-configuration.md#64-deploy-eval-gate). |
| E5.7 | Deploy git policy | **AC:** Default `.gitignore` includes `deploy/` and `usr-harnesses/*/artifacts/`; documented option to commit `deploy/<name>/` for audited releases; CI may build and upload bundle as artifact. |
| E5.8 | Deploy platform policy | **AC:** Documented platform matrix in `README.deploy.md` and [Architecture §10.6](architecture/07-deploy-packaging.md#106-deploy-platform-targets): **dev** (install, serve, compile, deploy CLI) on Win/macOS/Linux; **production serve** Linux-first (VM, bare metal, Docker/Kubernetes). Bundle is OS-neutral Python + pinned artifacts. Windows/macOS production serve is supported but not CI-gated in v1. Optional container path referenced (E8.5). |
| E5.9 | Target runtime install script | **AC:** `install/target_install.py` (+ `target-install.sh` / `target-install.ps1` wrappers) runs on the **target machine** (desktop PC or server) after the user copies `deploy/<name>/`. Assumes Python 3.11+ preinstalled; creates optional `.venv`; `pip install zaumzeug` (runtime only); runs `zaumzeug doctor <name> --deploy`; prints `.env` setup from `.env.example` if present (never overwrites `.env`). Idempotent; cross-platform Win/macOS/Linux. Supports `--skip-venv`, `--verify` (doctor + serve dry-run). Also shipped inside each `deploy/<name>/` bundle (E5.1). |

**Story seeds:** Deploy after compile; serve --deploy on clean venv without usr-harnesses folder; `target_install` on Windows desktop and Linux server; serve --deploy smoke on Linux CI (Phase 2).

---

### Epic E6 — Evaluation and quality (Phase 2, optional)

**Outcome:** Developers can regression-test; not required for end users.

| ID | Feature | Acceptance criteria |
|---|---|---|
| E6.1 | Optional `[eval]` extra | **Done** (E6-S01, 2026-07-28) — Core install has no `deepeval`; `[eval]` extra installs it; `zaumzeug.eval.require_deepeval()` friendly hint; documented in user-docs. |
| E6.2 | `zaumzeug eval` | **Done** (E6-S02, 2026-07-28). **AC:** Behavior per [Architecture §6.3](architecture/05-configuration.md#63-zaumzeug-eval-frameworks): `eval.framework: deepeval` requires `[eval]` extra; `eval.framework: builtin` runs JSONL checks without DeepEval; missing `eval` section → clear error. |
| E6.3 | Eval gate on deploy | **Done** (E6-S03, 2026-07-28) — covered by E5.6; packager invokes `run_eval` when gate is `warn`/`block`; shared tests in `tests/unit/deploy/test_eval_gate.py`. |
| E6.4 | `eval/` pytest scaffold | **Done** (E6-S04, 2026-07-28). **AC:** Optional `usr-harnesses/<name>/eval/test_*.py` runs via `deepeval test run`; custom metrics in `eval/metrics.py`; `eval/` excluded from deploy (`copy_rules`); `zaumzeug init --with-eval`. |
| E6.5 | Trace → test case | **Done** (E6-S05, 2026-07-28). **AC:** Haystack trace export to JSONL (`data/traces/`); score single trace with `zaumzeug eval --trace`; schema documented for valset append. |
| E6.6 | HTTP black-box eval | **Done** (E6-S06, 2026-07-28). **AC:** Optional Mode C — eval against running `zaumzeug serve` via `/v1/chat/completions` (staging/debug); `--base-url` / `eval.base_url`. |
| E6.7 | GEPA ↔ DeepEval bridge | **Done** (E6-S07, 2026-07-28). **AC:** Failed eval rows can append to `data/train.jsonl`; shared `data/val.jsonl`; GEPA custom metric may delegate to DeepEval `.measure()`. |

**Story seeds:** Eval without deepeval shows install hint ✅ (E6-S01 `require_deepeval()`); Mode C `--base-url` vs running serve ✅ (E6-S06); GEPA metric delegates to DeepEval `.measure()` optionally ✅ (E6-S07).

---

### Epic E7 — Tools, MCP, and ACP (Phase 3)

**Outcome:** Full tool surface and IDE integrations.

| ID | Feature | Acceptance criteria |
|---|---|---|
| E7.1 | MCP tool config | **AC:** `tools.mcp` in yaml wires `MCPToolset`; `zaumzeug mcp` serves `{port}/mcp`. (Protocols: [Architecture §9](architecture/06-runtime-and-protocols.md#9-client-access-and-protocols).) |
| E7.2 | Custom tool loader | **AC:** `tools.custom` imports from harness folder; registered as Haystack tools. |
| E7.3 | Cursor MCP setup | **AC:** Documented `mcp.json` → `http://localhost:{mcp_port}/mcp`; install may write `.cursor/mcp.json.example` or `--cursor-mcp` for live file. |
| E7.4 | Chainlit | **AC:** `serve.hayhooks.chainlit: true` serves `/chat` on same port (embedded GUI). |
| E7.5 | ACP adapter | **AC:** `zaumzeug acp <name>` stdio process; Zed/JetBrains can register command. |
| E7.6 | MCP + deploy | **AC:** `zaumzeug mcp <name> --deploy` works from production bundle. |
| E7.7 | Extended builtin catalog | **AC:** Phase 3 builtins beyond `web_fetch` per [Architecture §6.5](architecture/05-configuration.md#65-builtin-tools-catalog). |
| E7.8 | Web client layouts | **AC:** Document co-located deployment patterns (Chainlit embedded, Open WebUI + Hayhooks, SPA + Nginx proxy) per [Architecture §9.4](architecture/06-runtime-and-protocols.md#94-web-deployment-layouts). |

**Story seeds:** MCP integration test with stub transport; tool correctness eval when DeepEval present.

---

### Epic E8 — RAG and production hardening (Phase 4)

**Outcome:** Pipelines, auth, observability, optional A2A.

| ID | Feature | Acceptance criteria |
|---|---|---|
| E8.1 | Pipeline exposure | **AC:** User `pipelines/` exposed via `serve.expose`; RAG path documented. |
| E8.2 | Production auth | **AC:** Documented **Traefik proxy-only** pattern for production serve (TLS termination, bearer/API-key or ForwardAuth middleware in front of Hayhooks); ZaumZeug does **not** implement in-process auth in v1; ops guide in `README.deploy.md` + `user-docs/guides/production-auth.md`. |
| E8.3 | Trace → dataset ratchet | **AC:** Production traces append to dataset; feed compile loop. Future: `zaumzeug replay <name> --trace` (recorded tool outputs). |
| E8.4 | Optional A2A | **AC:** `serve.a2a: true` hosts agent card (if prioritized). |
| E8.5 | Dockerfile template | **AC:** Optional generated `deploy/<name>/Dockerfile`. |
| E8.6 | DeepEval production observe | **AC:** Optional `@observe` + Confident AI sync (opt-in). |

---

## 9. CLI surface (epic mapping)

Command semantics, source roots (`usr-harnesses/` vs `deploy/`), Hayhooks layering, and env overrides: **[Architecture §8](architecture/06-runtime-and-protocols.md#8-cli-and-runtime-layering)**.

| Command | Phase | Epic |
|---|---|---|
| `zaumzeug init` | 1 | E1 |
| `zaumzeug doctor` | 1 | E2 |
| `zaumzeug serve [--deploy]` | 1 | E3, E5 |
| `zaumzeug run [--deploy]` | 1 | E3 |
| `zaumzeug compile [--workflow-diagram-only]` | 2 | E4 |
| `zaumzeug deploy` | 2 | E5 |
| `zaumzeug eval` | 2 | E6 (optional) |
| `zaumzeug mcp` / `zaumzeug acp` | 3 | E7 |

**Future commands (not Phase 1–4 v1):** `zaumzeug export <name>` (tarball of `deploy/`); `zaumzeug replay <name> --trace` (trace replay); `zaumzeug install-project` (PyPI consumer scaffold — [E1-S08](stories/epic-stories/25-story.md); deferred until package publish).

---

## 10. Delivery phases (milestones)

| Phase | Milestone | Epics |
|---|---|---|
| **0** | Ideation complete → PRD + architecture | — |
| **1** | SDK skeleton, install, multi-agent serve + serial `run`, example harness | E1, E2, E3 — [Architecture topics](architecture/00-README.md#architecture-topics) |
| **2** | Compile, deploy, optional eval | E4, E5, E6 — **in progress:** E4 **Done** 2026-07-28; [E6-S01](stories/epic-stories/34-story.md)–[E6-S07](stories/epic-stories/40-story.md) **Done** 2026-07-28 ([E5-S06](stories/epic-stories/46-story.md) early); next [E5-S01](stories/epic-stories/41-story.md) |
| **3** | MCP, ACP, custom tools, Chainlit | E7 |
| **4** | RAG, auth, production ratchet, A2A | E8 |

---

## 11. Success metrics

| Metric | Target (post Phase 1) |
|---|---|
| Time to first `zaumzeug serve` after clone | **< 15 minutes** on CI matrix and typical broadband (mock model, no API keys); up to ~30 minutes acceptable on slow home networks |
| Install success rate (CI matrix) | 100% on Win/macOS/Linux |
| Runtime smoke (CI matrix) | 100% on Win/macOS/Linux — `zaumzeug doctor`, `--dry-run`, mock-model serve (E1.7) |
| Config validation error clarity | User can fix without reading SDK source |
| Compile → deploy → target_install → serve --deploy | Documented happy path on clean target machine; production serve validated on Linux CI (Phase 2+) |

---

## 12. Open decisions (blockers for some stories)

| # | Decision | Impact |
|---|---|---|
| 1 | Compile cadence (PR, nightly, on failure) | CI design |
| 2 | Primary web UI (Chainlit vs Open WebUI vs custom) | E7 docs |
| 4 | MCP granularity (per agent vs per pipeline) | E7 |
| 5 | A2A in Phase 4 or defer | E8.4 |
| 6 | Multi-tenant Hayhooks | NG1 / future |

**Resolved:** **`install/` vs `zaumzeug install-project` (open #3, 2026-07-22)** — **both paths coexist** with distinct roles: (1) **SDK repo / Phase 1** — `install/client_install.py` (+ wrappers) is the supported path (venv, editable `[dev]`, scaffold from `install/templates/`); (2) **PyPI consumers** — after `zaumzeug` is published, `pip install zaumzeug` then `zaumzeug install-project` scaffolds `usr-harnesses/`, `user-docs/`, `.env` in an arbitrary cwd by reusing scaffold logic **without** editable repo install; templates must ship in the wheel. **Implementation deferred** with PyPI package creation/publishing ([E1-S08](stories/epic-stories/25-story.md)) — not required for Phase 1–4 v1 clone-based workflows. **Production auth (Phase 4)** — **proxy-only via Traefik** in front of `zaumzeug serve --deploy`; TLS + bearer/API-key or ForwardAuth at the edge; **no in-process `serve.auth` in SDK v1** (document patterns, do not build auth into Hayhooks wrapper). **Hayhooks self-hosted** — `zaumzeug serve|mcp` wraps pip-installed Hayhooks on the target host (bare metal, VM, or Docker/Kubernetes via E8.5); Haystack Enterprise Platform is **not** in v1 scope. **Product name ZaumZeug** (PyPI `zaumzeug`, import `zaumzeug`, CLI `zaumzeug`); **GEPA Phase 2** — Pattern A (`dspy.GEPA`) is the CLI default; optional **input rewrite/clarify templates** at compile time (not runtime user-chat optimization); **`optimize_anything` / Pattern B shipped** (E4.4 / E4-S04, 2026-07-28) as adapter + schema (CLI remains Pattern A); example harness = **general research agent** (E3.4); `zaumzeug eval` frameworks (`builtin` \| `deepeval`); `deploy.eval_gate`; builtin tools catalog; multi-tenant deferred (NG1); **dev workspace folder = `usr-harnesses/`** (fixed name in v1); **target runtime install** via `target_install.py` (E5.9); **ModelRouter** = custom Haystack wrapper with optional OpenRouter provider entry ([Architecture §7](architecture/05-configuration.md#7-model-routing)); **config surface** = YAML primary + optional Python in `modules/`, `tools/`, `hooks.py` only — no `harness.py` entry point in v1 ([Architecture §3.3](architecture/02-repository-and-layout.md#33-harness-folder-layout)). Technical rules: [Architecture §2](architecture/01-overview-and-principles.md#2-architectural-principles), [§6.3–6.6](architecture/05-configuration.md#63-zaumzeug-eval-frameworks), [§9](architecture/06-runtime-and-protocols.md#9-client-access-and-protocols).

---

## 13. Validation notes (PRD review 2026-06-24)

All items below were addressed in PRD + Architecture updates.

| # | Finding | Resolution |
|---|---|---|
| V1 | `zaumzeug eval` without DeepEval undefined | [Architecture §6.3](architecture/05-configuration.md#63-zaumzeug-eval-frameworks): `eval.framework: builtin` \| `deepeval` |
| V2 | Missing `## CLI` header in ideation | Fixed in ideation; CLI: Architecture §8, epic map: PRD §9 |
| V3 | Multi-tenant serving inconsistent | NG1 + open #6; [Architecture §8.3](architecture/06-runtime-and-protocols.md#83-multi-harness-serving) |
| V4 | Production server deps unclear | Architecture §10 dependency table; E5.5 AC |
| V5 | Example harness use case open | **Resolved:** general research agent (E3.4) |
| V6 | Eval gate on deploy not config-shaped | `deploy.eval_gate` + `--eval-gate`; Architecture §6.4, E5.6 |
| V7 | Builtin catalog underspecified | Architecture §6.5 catalog; E3.3, E7.7 |
| V8 | Ideation mixed product + architecture | Split: PRD + architecture.md + ideation archive |
| V9 | Ideation parity gaps (2026-06-24) | Full requirement-level port to PRD + Architecture (extension points, install flags, eval modes, deploy policy, debug, client layouts, ecosystem reference) |
| V10 | Cross-platform scope limited to install only | E1.7 CI matrix; E3.2 runtime AC; E5.8 deploy platform policy; PRD §14 table; Architecture §2.5, §10.6 |
| V11 | Deploy bundle missing target dependency installer | E5.9 `target_install.py`; bundled in deploy; Journey B updated; folder rename `usr-harnesses/` |
| V12 | User install effort/disk not specified for README | [§7.4](#74-user-installation-guide-content-for-readme--phase-1); E1.5, E1.6 AC updated |
| V13 | Dependency update path not specified for README | [§7.4](#74-user-installation-guide-content-for-readme--phase-1) “Updating dependencies”; E1.5, E1.6 AC updated |
| V14 | Phase 1 `harness.yaml` / mock `models.yaml` only in ideation | [Architecture §6.6](architecture/05-configuration.md#66-phase-1-config-schema); E2.1, E3.4, E3.5 AC |
| V15 | `pyproject.toml` / `[dev]` deps unspecified | [Architecture §4.4](architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub); E1.1 AC |
| V16 | Time target conflict (< 15 min vs 15–30 min) | §7.4 + §11 aligned: < 15 min target, ~30 min slow networks |
| V17 | `dspy` vs `dspy-ai` package name | [Architecture §4.1](architecture/03-technology-stack.md#41-core-libraries), §4.4 — canonical **`dspy-ai`** |
| V18 | Two `manifest.json` meanings conflated | [Architecture §5.3](architecture/04-data-flows.md#53-artifact-layout) `artifact-manifest.json` vs §10.3 deploy `manifest.json` |
| V19 | Deploy copy rules vague (“runtime-referenced”) | [Architecture §10.1](architecture/07-deploy-packaging.md#101-dev-vs-deploy) matrix; E5.2 AC |
| V20 | Journey A implied live API keys | Journey A + §7.4 mock-first path |
| V21 | Dependency updates missing from architecture | [Architecture §3.4](architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target) → PRD §7.4 |
| V22 | Open #5 ModelRouter, #7 harness.py blocked E2/E3 | Resolved in PRD §12 + Architecture §7, §3.3 |

---

## 14. Dependencies and constraints

### Languages and runtimes

| Layer | Language / format | Required? | Role |
|---|---|---|---|
| SDK & stack | **Python 3.11+** | Yes | Haystack, DSPy, GEPA, `zaumzeug` |
| Harness config | **YAML** | Yes | `harness.yaml`, `workflow.yaml`, `agents/<name>/agent.yaml`, `agents/<name>/agents-models.yaml`, optional harness `models.yaml` |
| Prompts & docs | Markdown | Optional | `prompts/`, `user-docs/` |

| Harness style | Languages | When |
|---|---|---|
| Config-only | YAML (+ optional `.md` prompts) | Builtin tools, hand-authored `system_prompt` — no Python in harness folder |
| Custom harness | Python in `agents/<name>/modules/`, `tools/`, `hooks.py` | DSPy modules, custom tools, GEPA metrics, lifecycle hooks per agent — **no `harness.py` entry point in v1** |
| Pipelines (Phase 4) | YAML and/or Python | Haystack pipeline definitions |

**Clients** calling a deployed harness are not limited to Python — any HTTP/MCP/ACP client applies ([Architecture §9](architecture/06-runtime-and-protocols.md#9-client-access-and-protocols)).

### Cross-platform support

| Surface | Windows | macOS | Linux | CI-gated (v1) |
|---|---|---|---|---|
| Install + onboarding (E1) | Yes | Yes | Yes | Yes — all three |
| Local serve + doctor (E2–E3) | Yes | Yes | Yes | Yes — mock model smoke |
| Compile + eval (E4–E6) | Yes | Yes | Yes | Dev/CI; Linux optional for heavy jobs |
| Production serve (E5) | Best-effort | Best-effort | **Primary** | Linux smoke in Phase 2+ |

Portable path handling (`pathlib`, no hardcoded separators), OS-aware venv activation hints, and documented env/port differences: [Architecture §2.5](architecture/01-overview-and-principles.md#25-cross-platform-portability).

### Stack constraints

See [Architecture §4](architecture/03-technology-stack.md#4-technology-stack) and [§4.4 `pyproject.toml`](architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub). Compile-time libs (`dspy-ai`, `gepa`) in `[dev]` extra only; runtime core excludes them. DeepEval optional via `[eval]` extra. Alternative eval frameworks (Promptfoo, Ragas, custom pytest) are compatible — no lock-in to DeepEval.

---

## 15. Documentation map

| Doc | Owns | Does not duplicate |
|---|---|---|
| **`prd.md`** (this file) | Goals, epics, AC, phases, open decisions, success metrics | Stack diagrams, protocol tables, SDK module paths |
| **`architecture.md`** | Hub: context diagram, doc map, legacy anchor index | User stories, acceptance criteria |
| **`architecture/`** | Topic files: structure, flows, protocols, golden rules, SDK modules | Same as hub — see [00-README](architecture/00-README.md) |
| **`cloudflare-harness.md`** | **Illustrative example only** — Cloudflare blog mapped to ZaumZeug concepts; not in product scope | Epic AC, implementation tasks |
| **`ideation-stage.md`** | Research archive, full YAML examples | Requirement-level content now mirrored in PRD + architecture |
| **`user-docs/`** | End-user guides | Internal design |
| **Root `README.md`** | Product overview, positioning, CLI snapshot | Full install/update guide |
| **Root `CONTRIBUTING.md`** (Phase 1 / E1.6) | New-contributor onboarding + dependency update summary per [§7.4](#74-user-installation-guide-content-for-readme--phase-1) | Full install/update guide (→ `user-docs/`), architecture, epics |

---

## 16. References

- **[Architecture](architecture.md)** — primary technical reference ([topic index](architecture/00-README.md))
- [Ideation archive](ideation-stage.md) — full config YAML examples until `user-docs/reference/` exists
- External: [Haystack](https://docs.haystack.deepset.ai/docs/agents) · [DSPy](https://dspy.ai/) · [GEPA](https://github.com/gepa-ai/gepa) · [DeepEval](https://github.com/confident-ai/deepeval)
