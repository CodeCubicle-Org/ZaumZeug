# Technology stack

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 4. Technology stack

### 4.1 Core libraries

| Library | Layer | Package | Responsibility |
|---|---|---|---|
| [Haystack](https://github.com/deepset-ai/haystack) | Runtime | `haystack-ai`, `hayhooks` | Agent loop, RAG, tools, MCP client, REST/MCP serve; ACP stdio is SDK-owned (`serve/acp.py`, not Hayhooks) |
| [Jinja2](https://jinja.palletsprojects.com/) | Runtime | `jinja2` | Optional artifact `input_rewrite` template render before `Agent.run` ([E4-S03b](../stories/epic-stories/28.2-story.md) ✅) |
| [DSPy](https://dspy.ai/) | Specification | `dspy-ai` | Modules, signatures — compile-time only |
| [GEPA](https://github.com/gepa-ai/gepa) | Optimization | `gepa` | `dspy.GEPA`, `optimize_anything` — offline |
| [DeepEval](https://github.com/confident-ai/deepeval) | Dev eval (optional) | `deepeval` via `[eval]` extra ✅ (E6-S01); `zaumzeug eval` ✅ (E6-S02); deploy gate ✅ (E6-S03 / E5-S06); `eval/` pytest scaffold ✅ (E6-S04); trace → test case ✅ (E6-S05); Mode C HTTP `--base-url` ✅ (E6-S06); GEPA ↔ DeepEval bridge ✅ (E6-S07) | Regression tests; not required for production serve |

Optional: Hayhooks `[chainlit]` extra for embedded GUI at `/chat` ✅ (E7-S04, 2026-08-21) — **primary MCP serving** is via Hayhooks (`zaumzeug mcp`). `mcp-haystack` is a **runtime** dependency for `MCPToolset` (E7-S01). **ACP** (`zaumzeug acp`) is stdio JSON-RPC in `serve/acp.py` ✅ (E7-S05, 2026-08-21) — no extra package.

### 4.2 Library boundaries (when to use what)

| Library | Use for | Do not use for |
|---|---|---|
| **Haystack** | Hot path: `Agent`, pipelines, `ComponentTool`, `MCPToolset`, Hayhooks REST/MCP, HITL/state | Offline prompt optimization |
| **DSPy** | Signatures, `Module`s, `ReAct` during compile/eval only; authoring environment | Production request path |
| **GEPA** | Evolving text params via execution traces; `dspy.GEPA`, `gepa.optimize()`, `gepa.optimize_anything()` | Live traffic; scalar-only metrics |
| **DeepEval** | Optional dev regression, agentic/RAG metrics, tracing, Confident AI | Mandatory ship gate; production default |

GEPA requires **task LM** and **reflection LM** as separate config roles (LiteLLM strings from `models.yaml`). Budget: `auto="light"|"medium"|"heavy"` or `max_metric_calls`.

**Implementation (E4-S01, 2026-07-28):** DSPy enters the SDK only via `zaumzeug.compile.module_loader` (lazy import). Serve/runtime keep zero DSPy imports (verified by unit tests). **2026-08-14:** loader invalidates import caches and drops the cached dotted-name chain before load so two harnesses (or pytest tmp dirs) that share `modules.researcher` do not collide.

**Implementation (E4-S02a, 2026-07-28):** `zaumzeug compile` loads modules and preflights LMs without invoking GEPA.

**Implementation (E4-S06, 2026-07-28):** `zaumzeug compile --dry-run` exposes that validate-only path on the CLI (no GEPA, no LLM calls, no artifacts).

**Implementation (E4-S02b, 2026-07-28):** `invoke_gepa()` runs `dspy.GEPA` (or `StubGEPA` for mock/CI), wires LiteLLM strings from the agent registry, respects budget config, and writes `artifacts/<run_id>/` + `artifacts/current`.

**Implementation (E4-S07, 2026-07-28):** Existing `<run_id>/` directories are immutable (never overwritten); pin/rollback via `agent.artifact` or retargeting `current`. Doctor validates pins (`check_pinned_artifact`). Docs: [user-docs/guides/compile.md](../user-docs/guides/compile.md#rollback-to-a-pinned-run).

**Implementation (E4-S08, 2026-07-28):** `compile/workflow_diagram.py` regenerates Mermaid `docs/workflow-diagram.md` on full compile and `--workflow-diagram-only` (no GEPA/LLM). Docs: [user-docs/guides/compile.md](../user-docs/guides/compile.md#workflow-diagram).

### 4.3 Languages and key packages

| Layer | Format | Notes |
|---|---|---|
| SDK | Python 3.11+ | Required on dev and server |
| Config | YAML | `harness.yaml`, `models.yaml` |
| Custom harness code | Python | Only when exceeding config-only harness |
| Clients | Any | HTTP/MCP/ACP to deployed harness |

```bash
pip install -e ".[dev]"              # repo clone — full dev stack (see §4.4)
pip install zaumzeug              # runtime only (production / PyPI)
pip install "zaumzeug[eval]"      # optional DeepEval
pip install openai-haystack anthropic-haystack openrouter-haystack  # per configured provider
# Chainlit (Phase 3 / E7-S04): pip install "hayhooks[chainlit]"
```

Model choice lives in **`models.yaml`**, not source code. Users do **not** pin Haystack/DSPy/GEPA/LiteLLM individually on the default path — versions come from `zaumzeug` extras ([PRD §7.4](../prd.md#74-user-installation-guide-content-for-readme--phase-1)).

### 4.4 `pyproject.toml` dependency groups (Phase 1 stub)

Canonical package layout. Root `pyproject.toml` exists as of E2-S00 (2026-07-08); this section remains the dependency-group reference. Exact pins may tighten later; ranges below are intentional until lockfile policy is decided (v1: no committed lockfile).

| Group | Install command | Includes | Excludes |
|---|---|---|---|
| **Runtime** (core) | `pip install zaumzeug` | `haystack-ai`, `hayhooks`, `mcp>=1.8.0,<2`, `mcp-haystack`, `httpx`, `litellm`, `pydantic`, `pyyaml`, CLI entry `zaumzeug` | `dspy-ai`, `gepa`, `deepeval`, Chainlit (`hayhooks[chainlit]`) |
| **`[dev]`** extra | `pip install -e ".[dev]"` | Runtime + **`dspy-ai`**, **`gepa`**, test stack ([§4.5](#45-test-dependencies)), `debugpy`, editable SDK | Provider Haystack integrations (user-installed) |
| **`[eval]`** extra | `pip install "zaumzeug[eval]"` | `deepeval` (requires runtime core) | — |

**Implementation (E6-S01, 2026-07-28):** `eval = ["deepeval"]` in root `pyproject.toml`; core install excludes `deepeval`. `zaumzeug.eval.require_deepeval()` raises the §6.3 install hint when missing. Doctor does not import `deepeval`. Docs: [user-docs/getting-started/installation.md](../user-docs/getting-started/installation.md#optional-extras).

**Implementation (E7-S04, 2026-08-21):** Optional Chainlit GUI is **not** a `zaumzeug` extra — install `pip install "hayhooks[chainlit]"` then set `serve.hayhooks.chainlit: true`. `zaumzeug.serve.chainlit.require_chainlit()` fails serve with that hint when missing. Docs: [web-deployment.md](../user-docs/guides/web-deployment.md).

**Implementation (E7-S05, 2026-08-21):** `zaumzeug acp` is in-process Agent Client Protocol JSON-RPC on stdio — not a Hayhooks extra and not IBM ACP/A2A. Docs: [acp.md](../user-docs/guides/acp.md). Tests: `tests/integration/acp/test_acp_stdio.py`.

**Implementation (E6-S02, 2026-07-28):** `zaumzeug eval` CLI via `eval/runner.py` — `EvalConfig` on `HarnessConfig`; `framework: builtin` (JSONL exact/substring, no DeepEval) or `deepeval` (default when omitted); CLI `--framework` override. Tests: `tests/unit/eval/test_runner.py`.

**Implementation (E6-S03 / E5-S06, 2026-07-28):** Deploy eval gate in `deploy/packager.py` — `deploy.eval_gate` (`skip` \| `warn` \| `block`) + CLI `--eval-gate`; invokes `run_eval` when configured. Tests: `tests/unit/deploy/test_eval_gate.py`.

**Implementation (E6-S04, 2026-07-28):** Harness `eval/` pytest scaffold — `zaumzeug init --with-eval`, example `usr-harnesses/example/eval/`, `deepeval test run`; `deploy/copy_rules.py` excludes `eval/`. Tests: `tests/integration/eval/test_deepeval_scaffold.py`, `tests/unit/deploy/test_copy_rules.py`.

**Implementation (E6-S05, 2026-07-28):** Trace export helper `eval/trace.py` → `data/traces/*.jsonl`; CLI `zaumzeug eval --trace` scores captured turns without re-running the agent. Tests: `tests/unit/eval/test_trace.py`. Journey C: [user-docs/guides/testing.md](../user-docs/guides/testing.md#trace--test-case-journey-c).

**Implementation (E6-S06, 2026-07-28):** Mode C HTTP black-box — `zaumzeug eval --base-url` / `eval.base_url` against running serve `/v1/chat/completions` (staging/debug). Tests: `tests/integration/eval/test_http_eval.py`. Docs: [user-docs/guides/testing.md](../user-docs/guides/testing.md#mode-c--http-black-box-stagingdebug).

**Implementation (E6-S07, 2026-07-28):** GEPA ↔ DeepEval bridge — `eval/gepa_bridge.py` (`append_failed_eval_to_train`, shared val aliases, `deepeval_gepa_metric`); compile auto-loads optional `agents/<agent>/modules/metrics.py`. Tests: `tests/unit/eval/test_gepa_bridge.py`. Docs: [testing.md — GEPA ↔ DeepEval bridge](../user-docs/guides/testing.md#gepa--deepeval-bridge-compile--eval--compile).

**Provider integrations** (`openai-haystack`, `anthropic-haystack`, `openrouter-haystack`, …): **not** in core or `[dev]`. Install only providers referenced in `models.yaml`. `ModelRouter` fails at startup with an actionable message if a configured provider package is missing.

**`[project]` fragment (matches repo `pyproject.toml`):**

```toml
[project]
name = "zaumzeug"
requires-python = ">=3.11"
dependencies = [
  "haystack-ai",
  "hayhooks",
  "httpx",
  "litellm",
  "mcp>=1.8.0,<2",
  "mcp-haystack",
  "pydantic>=2",
  "pyyaml",
]

[project.optional-dependencies]
dev = [
  "dspy-ai",
  "gepa",
  "pytest",
  "pytest-asyncio",
  "respx",
  "debugpy",
]
eval = ["deepeval"]

[project.scripts]
zaumzeug = "zaumzeug.cli:main"
```

Repo clone install runs `pip install -e ".[dev]"` via `client_install.py`. Target install runs `pip install zaumzeug` only ([§10.5](07-deploy-packaging.md#105-production-server-dependencies)).

### 4.5 Test dependencies

Test libraries ship in **`[dev]`** (SDK repo) and **`[eval]`** (optional harness regression). Production runtime (`pip install zaumzeug`) includes **none** of these.

| Package | Layer | Phase | Purpose |
|---|---|---|---|
| **pytest** | All SDK tests | 1+ | Test runner, fixtures, parametrization, markers |
| **pytest-asyncio** | Integration, serve | 1+ | Async Hayhooks/Haystack serve and workflow tests |
| **httpx** | Runtime + integration | 1+ | Outbound HTTP for builtin `web_fetch`; OpenAI contract tests against ephemeral serve ([E3-S07](../stories/02-epic.md#e3-s07-openai-rest-contract-tests) ✅) |
| **respx** | Integration | 1+ | Mock outbound HTTP at boundary (`web_fetch` stubs in unit + E3-S07 contract tests) |
| **debugpy** | Local debug | 1+ | IDE attach to `zaumzeug serve` ([§13.2](10-operations-and-reference.md#132-mechanisms)) |
| **syrupy** *(optional)* | Unit | 2+ | Golden snapshots for compile export / `artifact-manifest.json` ([E4-S03a](../stories/epic-stories/28.1-story.md) ✅ uses checked-in golden JSON under `tests/compile/golden/` without requiring syrupy) |
| **pytest-recording** *(optional)* | Integration | 2+ | VCR cassettes for re-recordable provider HTTP when mock profile is insufficient |
| **deepeval** | Harness eval | 2+ (`[eval]`) ✅ E6-S01 / CLI ✅ E6-S02 / deploy gate ✅ E6-S03 / pytest scaffold ✅ E6-S04 / trace ✅ E6-S05 / Mode C ✅ E6-S06 / GEPA bridge ✅ E6-S07 | Optional LLM regression via `zaumzeug eval` or `usr-harnesses/<name>/eval/test_*.py` ([E6](../stories/05-epic.md)); import guard in `zaumzeug.eval`; `deploy.eval_gate` on release ([E5-S06](../stories/epic-stories/46-story.md)); `init --with-eval` scaffold; `eval --trace`; Mode C `--base-url` staging/debug; failed→train + optional DeepEval GEPA metric |

**Not in v1 `[dev]` pins (bring your own if needed):** `pytest-cov` (coverage signal), `freezegun` (time determinism). MCP serve tests use Starlette `TestClient` against `zaumzeug mcp` (**Done** [E7-S01](../stories/07-epic.md#e7-s01-mcp-tool-configuration) — `tests/integration/mcp/`); custom tool loader tests import fixture modules under `agents/<name>/tools/` (**Done** [E7-S02](../stories/07-epic.md#e7-s02-custom-tool-loader) — `tests/unit/runtime/tools/test_custom_loader.py`); ACP stdio tests drive `serve/acp.py` in-process and via `python -m zaumzeug.cli acp` (**Done** [E7-S05](../stories/07-epic.md#e7-s05--acp-adapter) — `tests/integration/acp/test_acp_stdio.py`); no extra stub-transport pin.

**Mock-first default:** CI and local default runs use the **`mock`** model profile and file fixtures under `tests/fixtures/responses/` — no API keys. Live LLM and cassette re-record are opt-in ([§13.6](10-operations-and-reference.md#136-testing-playbook)).

---
