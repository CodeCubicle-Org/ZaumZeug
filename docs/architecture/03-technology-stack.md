# Technology stack

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 4. Technology stack

### 4.1 Core libraries

| Library | Layer | Package | Responsibility |
|---|---|---|---|
| [Haystack](https://github.com/deepset-ai/haystack) | Runtime | `haystack-ai`, `hayhooks` | Agent loop, RAG, tools, MCP client, REST/MCP serve |
| [DSPy](https://dspy.ai/) | Specification | `dspy-ai` | Modules, signatures — compile-time only |
| [GEPA](https://github.com/gepa-ai/gepa) | Optimization | `gepa` | `dspy.GEPA`, `optimize_anything` — offline |
| [DeepEval](https://github.com/confident-ai/deepeval) | Dev eval (optional) | `deepeval` via `[eval]` extra | Regression tests; not required for deploy |

Optional: `mcp-haystack` only if a specific Haystack MCP integration requires it — **primary MCP serving** is via Hayhooks (`zaumzeug mcp`).

### 4.2 Library boundaries (when to use what)

| Library | Use for | Do not use for |
|---|---|---|
| **Haystack** | Hot path: `Agent`, pipelines, `ComponentTool`, `MCPToolset`, Hayhooks REST/MCP, HITL/state | Offline prompt optimization |
| **DSPy** | Signatures, `Module`s, `ReAct` during compile/eval only; authoring environment | Production request path |
| **GEPA** | Evolving text params via execution traces; `dspy.GEPA`, `gepa.optimize()`, `gepa.optimize_anything()` | Live traffic; scalar-only metrics |
| **DeepEval** | Optional dev regression, agentic/RAG metrics, tracing, Confident AI | Mandatory ship gate; production default |

GEPA requires **task LM** and **reflection LM** as separate config roles (LiteLLM strings from `models.yaml`). Budget: `auto="light"|"medium"|"heavy"` or `max_metric_calls`.

**Implementation (E4-S01, 2026-07-28):** DSPy enters the SDK only via `zaumzeug.compile.module_loader` (lazy import). Serve/runtime keep zero DSPy imports (verified by unit tests).

**Implementation (E4-S02a, 2026-07-28):** `zaumzeug compile` loads modules and preflights LMs without invoking GEPA.

**Implementation (E4-S02b, 2026-07-28):** `invoke_gepa()` runs `dspy.GEPA` (or `StubGEPA` for mock/CI), wires LiteLLM strings from the agent registry, respects budget config, and writes `artifacts/<run_id>/` + `artifacts/current`.

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
# Chainlit (Phase 3): pip install "hayhooks[chainlit]"
```

Model choice lives in **`models.yaml`**, not source code. Users do **not** pin Haystack/DSPy/GEPA/LiteLLM individually on the default path — versions come from `zaumzeug` extras ([PRD §7.4](../prd.md#74-user-installation-guide-content-for-readme--phase-1)).

### 4.4 `pyproject.toml` dependency groups (Phase 1 stub)

Canonical package layout. Root `pyproject.toml` exists as of E2-S00 (2026-07-08); this section remains the dependency-group reference. Exact pins may tighten later; ranges below are intentional until lockfile policy is decided (v1: no committed lockfile).

| Group | Install command | Includes | Excludes |
|---|---|---|---|
| **Runtime** (core) | `pip install zaumzeug` | `haystack-ai`, `hayhooks`, `httpx`, `litellm`, `pydantic`, `pyyaml`, CLI entry `zaumzeug` | `dspy-ai`, `gepa`, `deepeval` |
| **`[dev]`** extra | `pip install -e ".[dev]"` | Runtime + **`dspy-ai`**, **`gepa`**, test stack ([§4.5](#45-test-dependencies)), `debugpy`, editable SDK | Provider Haystack integrations (user-installed) |
| **`[eval]`** extra | `pip install "zaumzeug[eval]"` | `deepeval` (requires runtime core) | — |

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
| **syrupy** *(optional)* | Unit | 2+ | Golden snapshots for compile export / `artifact-manifest.json` ([E4-S03](../stories/04-epic.md#e4-s03-export-contract-haystack-artifacts)) |
| **pytest-recording** *(optional)* | Integration | 2+ | VCR cassettes for re-recordable provider HTTP when mock profile is insufficient |
| **deepeval** | Harness eval | 2+ (`[eval]`) | Optional LLM regression via `usr-harnesses/<name>/eval/test_*.py` ([E6](../stories/05-epic.md)) |

**Not in v1 `[dev]` pins (bring your own if needed):** `pytest-cov` (coverage signal), `freezegun` (time determinism), MCP stub transports (Phase 3 — see [E7-S01](../stories/07-epic.md#e7-s01-mcp-tool-configuration)).

**Mock-first default:** CI and local default runs use the **`mock`** model profile and file fixtures under `tests/fixtures/responses/` — no API keys. Live LLM and cassette re-record are opt-in ([§13.6](10-operations-and-reference.md#136-testing-playbook)).

---
