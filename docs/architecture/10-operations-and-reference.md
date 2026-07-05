# Operations and reference

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 13. Debug and test architecture

Goals: [PRD G6](../prd.md#3-goals). Epics: [E2, E4, E6](../prd.md#8-functional-requirements-epics).

### 13.1 Design principles

| Principle | SDK support |
|---|---|
| Fail fast, explain why | Pydantic + `zaumzeug doctor` actionable messages |
| Reproducible state | Harness = folder on disk; git-commit known config |
| Compile vs runtime split | Isolate prompt bugs (compile) vs serve bugs (runtime) |
| Observable loops | Structured logging, `track_stats`, optional OTel Phase 4 |
| Cheap CI | Mock LM + stub tools default; live API via `HARNESS_LIVE_LLM=1` (documented env; no separate epic — opt-in local/e2e only) |

### 13.2 Mechanisms

| Mechanism | Purpose |
|---|---|
| `zaumzeug doctor` | Preflight; `--verbose`, `--json`; per-harness or project-wide |
| `zaumzeug eval` | Optional regression; `--trace <file>` for single trace |
| `--dry-run` on serve/compile | Validate without server or GEPA/LLM |
| `HARNESS_LOG_LEVEL=DEBUG` | SDK + Haystack request logging |
| `install --verify` | Doctor + optional dry-run serve |
| Mock `models.yaml` profile | CI without API keys |
| `tests/usr-harnesses/fixture/` | Minimal harness for SDK tests (not shipped) |
| debugpy | `python -m debugpy --listen 5678 -m zaumzeug.cli serve example` |
| Hayhooks escape hatch | Raw `hayhooks run` to isolate Haystack vs config |
| Swagger `/docs` | Manual REST probes |

### 13.3 Test pyramid

```text
tests/
├── unit/                         # config merge, ModelRouter mock, export snapshots (Phase 2+)
├── integration/                  # serve HTTP contract, localhost bind, deploy smoke
├── usr-harnesses/                # SDK runs against fixture/example harness trees
│   ├── fixture/                  # minimal harness — not shipped to users
│   └── example/                  # optional DeepEval pytest when [eval] installed
├── e2e/                          # HARNESS_LIVE_LLM=1 only; nightly / pre-release
└── fixtures/
    ├── responses/                # canned mock LLM replies (mock profile)
    └── cassettes/                # optional VCR YAML (pytest-recording; Phase 2+)
```

| Directory | What runs here | Network | Typical marker |
|---|---|---|---|
| `tests/unit/` | Pydantic schemas, merge rules, export snapshots | None | default CI |
| `tests/integration/` | `zaumzeug serve` on ephemeral port, OpenAI REST shape | Localhost only | default CI |
| `tests/usr-harnesses/` | Full harness folder against SDK commands | Mock profile | default CI |
| `tests/e2e/` | Live provider smoke, cassette re-record | Real APIs (gated) | `HARNESS_LIVE_LLM=1` |

**Harness-level eval** (author-owned, not under `tests/`):

```text
usr-harnesses/<harness>/eval/
├── test_*.py          # DeepEval pytest — requires pip install "zaumzeug[eval]"
└── metrics.py         # custom metrics
```

Run harness eval: `zaumzeug eval <harness>` or `deepeval test run usr-harnesses/<harness>/eval/`. See [user-docs/guides/testing.md](../user-docs/guides/testing.md).

### 13.4 Trace capture (Phase 2+)

| Feature | Purpose |
|---|---|
| Trace export | Haystack run → JSONL in `data/traces/` |
| `zaumzeug eval --trace` | Score captured trace |
| `zaumzeug replay` (future) | Re-run tool loop with recorded outputs |

### 13.5 Phase mapping

| Phase | Debug/test deliverables |
|---|---|
| 1 | doctor, config unit tests, serve `--dry-run`, mock profile, fixture harness |
| 2 | compile `--dry-run`, export golden tests, trace → `LLMTestCase`, optional `zaumzeug eval` |
| 3 | MCP integration tests, tool correctness eval when DeepEval present |
| 4 | `@observe` on runtime; Confident AI sync; trace → dataset → GEPA ratchet |

Also compatible: Promptfoo, Ragas, custom pytest — no DeepEval lock-in.

### 13.6 Testing playbook

End-user walkthrough: [user-docs/guides/testing.md](../user-docs/guides/testing.md). Test dependency pins: [§4.5](03-technology-stack.md#45-test-dependencies).

#### Three layers — what to test where

| Layer | Scope | Mock strategy | Catches |
|---|---|---|---|
| **Unit** | Single module: config, merge, export mapping | No network; patch `ModelRouter` / file I/O at boundary | Schema bugs, merge mistakes, bad error messages |
| **Integration** | CLI + serve + workflow on fixture harness | **`mock`** profile + `respx` for outbound HTTP | REST contract drift, serve wiring, stage routing |
| **Eval / regression** | Output quality over golden cases | Real or judge LLM via DeepEval (optional) | Prompt/artifact regressions, relevance/hallucination drift |
| **E2E (opt-in)** | Live provider end-to-end | Real API keys via `.env` | Provider breakage, latency, rare tool paths |

**Rule:** Mock at **boundaries** (LLM, `web_fetch`, external MCP) — test ZaumZeug routing, config resolution, and artifact loading in unit/integration tiers. Do not assert on raw LLM creativity in unit tests.

#### Who writes what

| Author | Location | Runner |
|---|---|---|
| SDK maintainer | `tests/unit/`, `tests/integration/`, `tests/usr-harnesses/fixture/` | `pytest` from repo root |
| Harness developer | `usr-harnesses/<name>/eval/test_*.py` | `deepeval test run` or `zaumzeug eval` |
| Harness developer (quick) | `zaumzeug doctor`, `zaumzeug serve --dry-run` | CLI — no pytest required |

#### Environment gates

| Variable | When set | Effect |
|---|---|---|
| *(unset)* | Default CI and local dev | `mock` profile only; `tests/e2e/` skipped |
| `HARNESS_LIVE_LLM=1` | Nightly / pre-release / local opt-in | Enables `tests/e2e/` live provider tests |
| `HARNESS_LOG_LEVEL=DEBUG` | Debugging failing integration test | SDK + Haystack structured logs |
| `PYTEST_OPENAI_API_KEY` *(optional)* | Re-recording VCR cassettes | Real key for `pytest --record-mode=once`; filter auth headers from cassettes |

#### CI tiers (maps to epics)

| Tier | Trigger | Jobs | Epics |
|---|---|---|---|
| **Smoke** | Every push; `windows-latest`, `ubuntu-latest`, `macos-latest` | `client_install.py --verify`, `zaumzeug doctor`, `serve --dry-run`, mock serve smoke | [E1-S07](../stories/03-epic.md#e1-s07-cross-platform-ci-matrix), [E3-S07](../stories/02-epic.md#e3-s07-openai-rest-contract-tests) |
| **Unit + integration** | Every push (same workflow or dedicated job) | `pytest tests/unit tests/integration tests/usr-harnesses -v` | [E2](../stories/01-epic.md), [E3-S06](../stories/02-epic.md#e3-s06-phase-1-test-infrastructure-and-security-baseline) |
| **Eval regression** | PR touching prompts/artifacts; nightly | `deepeval test run` on critical cases; `deploy.eval_gate` on release | [E6](../stories/05-epic.md), [E5-S06](../stories/06-epic.md#e5-s06-deploy-eval-gate) |
| **Live e2e** | Nightly / manual | `HARNESS_LIVE_LLM=1 pytest tests/e2e -v` | Optional — not Phase 1 CI gate |

#### Common workflows

```bash
# Default — fast, no API keys
pytest tests/unit tests/integration tests/usr-harnesses -v

# Single story / module while developing
pytest tests/unit/config/test_schemas.py -v -k e2_s01

# Optional harness regression (requires [eval])
pip install -e ".[dev,eval]"
deepeval test run usr-harnesses/example/eval/

# Re-record HTTP cassettes (Phase 2+; requires keys)
PYTEST_OPENAI_API_KEY=sk-... pytest tests/integration --record-mode=once

# Live smoke (maintainers only)
HARNESS_LIVE_LLM=1 pytest tests/e2e -v
```

#### Starting eval cases

Begin with **20–50 cases from real failures** (production bugs, doctor errors, bad compile exports) — not synthetic thousand-case suites on day one. Append rows from traces (`data/traces/` → `zaumzeug eval --trace`) as the ratchet matures ([§13.4](#134-trace-capture-phase-2), [E8-S03](../stories/08-epic.md#e8-s03-trace-dataset-ratchet)).

---


## 14. Security (Phase 1 stance)

Requirements: [PRD E8.2](../prd.md#epic-e8--rag-and-production-hardening-phase-4).

- **Local dev:** bind `localhost`; no auth on Hayhooks.
- **Secrets:** `.env` only — never in yaml, artifacts, or deploy bundle.
- **Sandbox / tool isolation:** not Phase 1 ([PRD NG4](../prd.md#4-non-goals-v1)); future: E2B, Docker Sandboxes (see [§16](10-operations-and-reference.md#16-supporting-ecosystem-reference)).
- **Production auth (Phase 4, resolved):** **Traefik proxy-only** — TLS termination and auth middleware (bearer/API-key headers, ForwardAuth, or OAuth provider) in front of `zaumzeug serve`; Hayhooks stays unauthenticated behind the proxy; **no in-process auth in SDK v1**. Document in `README.deploy.md` and `user-docs/guides/production-auth.md`. Nginx/Caddy acceptable as documented alternatives; Traefik is the reference implementation.

---


## 15. Anti-patterns

Complements [PRD §6](../prd.md#6-product-principles) and [§4 non-goals](../prd.md#4-non-goals-v1).

| Anti-pattern | Why |
|---|---|
| DSPy `ReAct` + Haystack `Agent` same request | Double loops |
| Hand-edit post-GEPA artifacts | Prompt drift |
| Scalar-only GEPA metrics | Loses reflection |
| GEPA on live traffic | Cost/latency |
| Train/serve tool mismatch | Skew |
| Hardcoded LLM in code | Breaks model-agnostic rule |
| Edit `deploy/` by hand | Overwritten on next deploy |

---


## 16. Supporting ecosystem (reference)

Not core SDK scope — options for adjacent concerns:

| Concern | Options |
|---|---|
| Unified model API | OpenRouter, LiteLLM, custom ModelRouter |
| MCP serving | Self-hosted Hayhooks via `zaumzeug mcp` (canonical); Haystack Enterprise workspace MCP out of v1 scope |
| MCP gateway | AWS MCP Gateway, Kong, Cloudflare, ContextForge |
| Sandbox | E2B, Docker Sandboxes, Daytona |
| Durable workflows | Temporal |
| Production tracing | DeepEval + Confident AI, OpenTelemetry, Braintrust, Arize Phoenix |
| Regression testing | DeepEval (recommended), Promptfoo, Ragas, custom pytest |
| Alternative runtimes (not chosen) | LangGraph, Pydantic AI, Claude Agent SDK, OpenAI Agents SDK |

---


## References

- **[PRD](../prd.md)** — requirements, epics, acceptance criteria, phases
- **[cloudflare-harness.md](../cloudflare-harness.md)** — **illustrative example only** (external Cloudflare blog → ZaumZeug layout); not in ZaumZeug scope
- [Ideation archive](../ideation-stage.md) — full YAML examples, install walkthrough code snippets
- External: [Haystack Agents](https://docs.haystack.deepset.ai/docs/agents) · [Hayhooks](https://deepset-ai.github.io/hayhooks/) · [DSPy GEPA](https://dspy.ai/api/optimizers/GEPA/overview) · [GEPA optimize_anything](https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/) · [DeepEval](https://github.com/confident-ai/deepeval) · [Agent Client Protocol](https://agentclientprotocol.com)
