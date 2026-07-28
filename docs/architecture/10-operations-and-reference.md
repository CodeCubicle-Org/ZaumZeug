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
| `zaumzeug doctor` | Preflight; `--verbose`, `--json`, `--deploy`; per-harness or project-wide |

**Implementation (E2-S04a, 2026-07-08):** `src/zaumzeug/doctor/` — `CheckResult` severity (`pass`/`warn`/`fail`), checks for Python version, package import, `.env`/live-model API keys, `harness.yaml`, `workflow.yaml`, merged model registries, runtime paths (`resolve_agent_serve`), and port availability. Exit code 1 when any check **fails**; warnings are non-blocking.

**Implementation (E2-S04b, 2026-07-08):** Additional warn-only checks: `eval` section present in Phase 1 (`eval_section`), MCP configured without `uv` on PATH (`mcp_uv`), stale or missing `docs/workflow-diagram.md` vs `workflow.yaml` (`workflow_diagram`). Doctor uses `load_harness_for_doctor()` to validate harness config while tolerating warned phase-gated keys.

**Implementation (E2-S04c, 2026-07-08):** `--deploy` flag (or `HARNESS_ROOT=deploy`) validates production bundles under `deploy/<name>/`. Checks deploy `manifest.json`, pinned artifact runs (`deploy_manifest`, `deploy_artifact`), and reuses E2-S04a core checks; skips dev-only warnings. Tests: `tests/integration/test_doctor.py` (`-k e2_s04c`).

**Implementation (E4-S05, 2026-07-28):** Warn-only `artifact_module` check — when a valid artifact is resolved and `compile.module` is set, compares current module `.py` SHA-256 to manifest `source_hash`. Drift suggests `zaumzeug compile <harness> --agent <name>` (exit code stays 0). Skipped in `--deploy` mode. Tests: `tests/integration/test_doctor.py::test_e4_s05_ac5_stale_artifact_warn`.

**Implementation (E2-S05, 2026-07-08):** `zaumzeug serve <harness> --dry-run [--deploy] [--json]` — `validate_serve()` in `src/zaumzeug/serve/validate.py`; prints port, entry agent, model id, runtime path, and tools; exit 1 on validation failure. No port bind or LLM. Tests: `tests/integration/test_serve_dry_run.py`.

**Implementation (E4-S06, 2026-07-28):** `zaumzeug compile <harness> --dry-run` — same validation path as full compile (`run_compile(..., dry_run=True)`): Phase 2 schema, module import, LM registry preflight; prints task/reflection models; no GEPA, no LLM API calls, no artifacts. Tests: `tests/integration/compile/test_compile_dry_run.py`.

**Implementation (E2-S06, 2026-07-08):** `src/zaumzeug/logging.py` — `configure_logging()` sets SDK (`zaumzeug`) and Haystack loggers to DEBUG when `zaumzeug serve|compile --verbose` or `HARNESS_LOG_LEVEL=DEBUG`. `log_request()` emits structured per-request context (`model_id`, `tool`, `artifact_path`). `SecretRedactingFilter` redacts API keys and bearer tokens. CLI reference: `user-docs/reference/cli.md`. Tests: `tests/unit/test_logging.py`.

**Implementation (E2-S07, 2026-07-08):** `workflow.yaml` schema validation via `load_workflow()` — `workflow_config` check in doctor; `validate_serve()` fails fast on invalid workflow before entry resolution. Tests: `tests/unit/config/test_workflow_schema.py`.

**Implementation (E3-S05, 2026-07-08):** Mock model profile — `MockChatGenerator` (`src/zaumzeug/integrations/mock.py`) returns fixture text from `tests/fixtures/responses/`; `ModelRouter` (`src/zaumzeug/runtime/model_router.py`) dispatches `provider: mock` without live API keys or provider integration packages. Shipped `install/templates/config/models.example.yaml`. Tests: `tests/unit/runtime/test_model_router.py` (`-k e3_s05`).

**Implementation (E3-S01, 2026-07-08):** Config-driven `ModelRouter` — `src/zaumzeug/integrations/haystack.py` (`PROVIDERS`, `build_chat_generator`); Phase 1 live providers `openrouter` and `openai_compatible` (LM Studio / local OpenAI-compatible APIs via `api_base_url`); lazy generator cache; install hints on missing packages. Tests: `tests/unit/runtime/test_model_router.py` (`-k e3_s01`), `tests/integration/test_openai_contract.py` (AC-8 routing).

**Implementation (E3-S06, 2026-07-20):** Test pyramid layout — `tests/unit/` (incl. `export/` placeholder), `tests/integration/`, `tests/usr-harnesses/fixture/` minimal harness, `tests/fixtures/responses/` + `cassettes/`, `tests/e2e/` gated by `HARNESS_LIVE_LLM=1`. Serve enforces localhost bind (`_enforce_localhost_bind`). Docs: `HARNESS_LIVE_LLM` + debugpy + Phase 1 security notes in `user-docs/reference/cli.md` and `user-docs/guides/testing.md`. Tests: `tests/usr-harnesses/fixture/test_fixture_harness.py`, `tests/integration/test_serve.py` (`-k e3_s06`).

**Implementation (E4-S03a, 2026-07-28):** Export golden snapshots live under `tests/compile/` (+ `tests/compile/golden/`) and `tests/unit/compile/test_export.py`. `tests/unit/export/` remains a layout placeholder pointing at those tests.

**Implementation (E3-S07, 2026-07-21):** OpenAI REST contract on ephemeral port — `tests/integration/conftest.py::ephemeral_serve_url`, `tests/integration/test_openai_contract.py` (`-k e3_s07`); HTTP `model_id` override wired in `serve/runner.py`. Cross-OS green closed by [E1-S07](../stories/epic-stories/24-story.md) (2026-07-22).

| `zaumzeug eval` | Optional regression; `--trace <file>` for single trace |
| `--dry-run` on serve | **Done** (E2-S05) — validate without Hayhooks or LLM |
| `zaumzeug serve` (dev) | **Done** (E3-S02, 2026-07-20) — Hayhooks runner, OpenAI REST, localhost bind |
| `--dry-run` on compile | **Done** (E4-S06, 2026-07-28) — validate without GEPA/LLM |
| `--verbose` on serve/compile | **Done** (E2-S06) — SDK + Haystack structured debug logging |
| `HARNESS_LOG_LEVEL=DEBUG` | **Done** (E2-S06) — equivalent to `--verbose`; SDK + Haystack request logging |
| `install --verify` | Doctor + optional dry-run serve |
| Mock `models.yaml` profile | **Done** (E3-S05) — CI and local dev without API keys |
| Phase 1 ModelRouter providers | **Done** (E3-S01) — `mock`, `openrouter`, `openai_compatible` (local LM Studio) |
| `tests/usr-harnesses/fixture/` | Minimal harness for SDK tests (not shipped) |
| debugpy | `python -m debugpy --listen 5678 -m zaumzeug.cli serve example` |
| Hayhooks escape hatch | **Done** (E3-S02) — documented in `user-docs/reference/cli.md`; raw `hayhooks run` for low-level debugging |
| Swagger `/docs` | Manual REST probes |

### 13.3 Test pyramid

```text
tests/
├── unit/                         # config merge, doctor checks, ModelRouter, export/ (Phase 2+)
├── integration/                  # doctor harness scans, serve HTTP contract, deploy smoke
├── usr-harnesses/                # SDK runs against fixture/example harness trees
│   ├── fixture/                  # minimal harness — not shipped to users ✅ (E3-S06)
│   └── example/                  # optional DeepEval pytest when [eval] installed
├── e2e/                          # HARNESS_LIVE_LLM=1 only; nightly / pre-release ✅ gate (E3-S06)
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
| 1 | doctor, config unit tests, serve `--dry-run` ✅ (E2-S05), structured logging ✅ (E2-S06), mock profile ✅ (E3-S05), ModelRouter ✅ (E3-S01), fixture harness + localhost security ✅ (E3-S06), OpenAI REST contract ✅ (E3-S07) |
| 2 | compile `--dry-run` (**E4-S06 Done** — `tests/integration/compile/test_compile_dry_run.py`), export golden tests (**E4-S03a Done** — `tests/compile/`), Pattern B adapter (**E4-S04 Done** — `tests/unit/compile/test_gepa_adapter.py`), trace → `LLMTestCase`, optional `zaumzeug eval` |
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
| Harness developer (quick) | `zaumzeug doctor`, `zaumzeug serve --dry-run`, `zaumzeug compile --dry-run` | CLI — no pytest required |

#### Environment gates

| Variable | When set | Effect |
|---|---|---|
| *(unset)* | Default CI and local dev | `mock` profile only; `tests/e2e/` skipped |
| `HARNESS_LIVE_LLM=1` | Nightly / pre-release / local opt-in | Enables `tests/e2e/` live provider tests |
| `HARNESS_LOG_LEVEL=DEBUG` | Debugging failing integration test | SDK + Haystack structured logs (`configure_logging` in `logging.py`) |
| `PYTEST_OPENAI_API_KEY` *(optional)* | Re-recording VCR cassettes | Real key for `pytest --record-mode=once`; filter auth headers from cassettes |

#### CI tiers (maps to epics)

| Tier | Trigger | Jobs | Epics |
|---|---|---|---|
| **Smoke** | Every push; `windows-latest`, `ubuntu-latest`, `macos-latest` | OS install wrappers (`client-install.sh` / `.ps1 --skip-venv --verify`), `zaumzeug doctor`, `serve --dry-run`, `install/ci_serve_smoke.py`, `pytest tests/integration/test_openai_contract.py`, unit+integration suite | [E1-S07](../stories/03-epic.md#e1-s07-cross-platform-ci-matrix) ✅ *(closes DoD from [E1-S02](../stories/epic-stories/19-story.md#definition-of-done), [E3-S07](../stories/02-epic.md#e3-s07-openai-rest-contract-tests))* |
| **Unit + integration** | Every push (same workflow or dedicated job) | `pytest tests/unit tests/integration tests/usr-harnesses -v` | [E2](../stories/01-epic.md), [E3-S06](../stories/02-epic.md#e3-s06-phase-1-test-infrastructure-and-security-baseline), [E3-S07](../stories/02-epic.md#e3-s07-openai-rest-contract-tests) ✅ |
| **Eval regression** | PR touching prompts/artifacts; nightly | `deepeval test run` on critical cases; `deploy.eval_gate` on release | [E6](../stories/05-epic.md), [E5-S06](../stories/06-epic.md#e5-s06-deploy-eval-gate) |
| **Live e2e** | Nightly / manual | `HARNESS_LIVE_LLM=1 pytest tests/e2e -v` | Optional — not Phase 1 CI gate |

**Implementation (E1-S07, 2026-07-22):** Workflow [`.github/workflows/ci-matrix.yml`](../../.github/workflows/ci-matrix.yml) — Python 3.11, pip cache, fail-fast, 30m timeout; mock-only (no `HARNESS_LIVE_LLM=1`); ephemeral serve smoke via `install/ci_serve_smoke.py` + `zaumzeug serve --port`. Tests: `tests/unit/ci/test_ci_matrix_workflow.py`, `tests/unit/install/test_ci_serve_smoke.py`.

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

**Implementation (E3-S06, 2026-07-20):** `serve/runner.py` defaults to and **enforces** `127.0.0.1` / `localhost` / `::1` — rejects `0.0.0.0`. User-facing notes: `user-docs/reference/cli.md` (Phase 1 security notes) and `user-docs/guides/testing.md`.

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
