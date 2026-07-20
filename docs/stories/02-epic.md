# Epic E3 — Runtime and Local Serve

| | |
|---|---|
| **Document** | Epic E3 user stories |
| **File** | `docs/stories/02-epic.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-20 (E3-S04 done) |
| **Status** | Backlog |
| **Build order** | **2 of 8** |
| **Related** | [PRD](../prd.md) · [Architecture](../architecture.md) · [Index](00-README.md) |

---
| Field | Value |
|---|---|
| **Phase** | 1 |
| **Epic** | E3 |
| **Outcome** | Multi-agent harness runs locally: `zaumzeug serve` (entry agent) and serial `zaumzeug run` |
| **Depends on** | [E2](01-epic.md) (config, doctor, resolver) |
| **Blocks** | [E1](03-epic.md) (install `--verify`, CI serve smoke) |
| **PRD** | [Epic E3](../prd.md#epic-e3--runtime-and-local-serve-phase-1) |
| **Architecture** | [§7 Model routing](../architecture/05-configuration.md#7-model-routing) · [§8 CLI](../architecture/06-runtime-and-protocols.md#8-cli-and-runtime-layering) · [§11 SDK modules #3–5](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build) · [§13–14 Debug/security](../architecture/10-operations-and-reference.md#13-debug-and-test-architecture) |
| **Journey** | [Journey A](../prd.md#71-journey-a--config-only-harness-phase-1) |
| **External** | [Haystack Agents](https://docs.haystack.deepset.ai/docs/agents) · [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks) |

### Story implementation order (within this epic)

1. **E3-S05** — Mock model profile *(enables CI without API keys)*
2. **E3-S01** — ModelRouter
3. **E3-S03** — `web_fetch` builtin
4. **E3-S00** — Runtime factory (Haystack Agent builder)
5. **E3-S02** — `zaumzeug serve`
6. **E3-S04** — Example harness templates ✅ *(unblocks E1 scaffolding)*
7. **E3-S06** — Test infrastructure + Phase 1 security
8. **E3-S07** — OpenAI REST contract tests
9. **E3-S08** — `zaumzeug run` (serial workflow)

---

## E3-S05 — Mock model profile

| Field | Value |
|---|---|
| **Feature** | E3.5 |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S02](../01-epic.md#e2-s02-modelsyaml-merge) |
| **Status** | Done (2026-07-08) |

### User story

As an **SDK maintainer**, I want a mock model in the registry, so that CI and first-run docs never require live API keys.

### References

- [PRD E3.5](../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §6.6](../architecture/05-configuration.md#66-phase-1-config-schema)
- [Architecture §7 — Mock profile](../architecture/05-configuration.md#7-model-routing)
- [Architecture §13.2 — Mock profile](../architecture/10-operations-and-reference.md#132-mechanisms)

### Acceptance criteria

- [x] **AC-1** `models.yaml` defines `mock` provider per §6.6
- [x] **AC-2** Canned responses from `tests/fixtures/responses/`
- [x] **AC-3** CI matrix uses mock exclusively ([E1-S07](../03-epic.md#e1-s07-cross-platform-ci-matrix))
- [x] **AC-4** Mock works without provider Haystack integration packages

### Implementation tasks (build)

- [x] Implement mock `ChatGenerator` in `src/zaumzeug/integrations/mock.py`; wire via `src/zaumzeug/runtime/model_router.py`
- [x] Add fixture JSON/text under `tests/fixtures/responses/` for deterministic assertions
- [x] Ship `mock` entry in `install/templates/config/models.example.yaml`

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E3-S05 / E3.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/test_model_router.py::test_e3_s05_ac1_mock_provider_in_registry` |
| AC-2 | `tests/unit/runtime/test_model_router.py::test_e3_s05_ac2_returns_fixture_response` |
| AC-3 | `tests/unit/runtime/test_model_router.py::test_e3_s05_ac3_ci_uses_mock_exclusively` *(E1-S07 also validates workflow steps)* |
| AC-4 | `tests/unit/runtime/test_model_router.py::test_e3_s05_ac4_no_provider_package_required` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/runtime/test_model_router.py -v -k e3_s05` passes

### Definition of done

- [x] ModelRouter returns fixture response for `model_id: mock`
- [x] Verification checklist complete; all ACs traced to tests

---

## E3-S01 — ModelRouter

| Field | Value |
|---|---|
| **Feature** | E3.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E3-S05](#e3-s05-mock-model-profile) · [E2-S02](../01-epic.md#e2-s02-modelsyaml-merge) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want a config-driven ModelRouter, so that I can switch LLM providers without code changes.

### References

- [PRD E3.1](../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §7](../architecture/05-configuration.md#7-model-routing)
- [Architecture §4.4](../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)
- [Architecture §11 #3](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build)

### Acceptance criteria

- [x] **AC-1** Stage-scoped `ModelRouter` reads active agent's merged `agents-models.yaml`
- [x] **AC-2** Lazy-builds Haystack `ChatGenerator` per provider
- [x] **AC-3** OpenRouter via `openrouter-haystack` when registry entry uses `provider: openrouter`
- [x] **AC-4** `openai_compatible` via `openai-haystack` when registry entry uses `provider: openai_compatible`; `api_base_url` from YAML (or `OPENAI_API_BASE` in `.env`); suitable for LM Studio and other local OpenAI-compatible servers
- [x] **AC-5** Caches generator instances per provider + endpoint (distinct `api_base_url` values do not share a cache entry)
- [x] **AC-6** Fails fast with actionable message if provider package missing (include `pip install …` hint)
- [x] **AC-7** No hardcoded model names in SDK source
- [x] **AC-8** OpenAI API: optional request `model_id` selects LLM; harness name remains agent identity *(routing layer — full HTTP in E3-S07)*

### Implementation tasks (build)

- [x] Extend `src/zaumzeug/runtime/model_router.py` *(mock provider done in E3-S05)*
- [x] Implement provider map in `src/zaumzeug/integrations/haystack.py` (`provider` → import + generator class)
- [x] Add optional `api_base_url` to `ModelEntryConfig` (non-secret; required for `openai_compatible`)
- [x] Load secrets from `.env` via stdlib `os.environ` — never from YAML

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E3-S01 / E3.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac1_config_model_id_and_request_override` |
| AC-2 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac2_lazy_build_generator` |
| AC-3 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac3_openrouter_provider_path` |
| AC-4 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac4_openai_compatible_local_provider_path` |
| AC-5 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac5_generator_cache_per_provider_endpoint` |
| AC-6 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac6_missing_package_install_hint` |
| AC-7 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac7_no_hardcoded_model_names` |
| AC-8 | `tests/integration/test_openai_contract.py::test_e3_s01_ac8_request_model_id_override` *(shared with E3-S07)* |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/runtime/test_model_router.py -v -k e3_s01` passes

### Definition of done

- [x] Missing provider packages produce install hint, not stack trace
- [x] Verification checklist complete; all ACs traced to tests

---

## E3-S03 — Builtin tool: `web_fetch`

| Field | Value |
|---|---|
| **Feature** | E3.3 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E2-S01](../01-epic.md#e2-s01-pydantic-config-schemas) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want a built-in `web_fetch` tool, so that my research agent can retrieve URL content without custom Python.

### References

- [PRD E3.3](../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §6.5](../architecture/05-configuration.md#65-builtin-tools-catalog)

### Acceptance criteria

- [x] **AC-1** Phase 1 ships `web_fetch` in SDK tool catalog
- [x] **AC-2** HTTPS only; 30s timeout; 1 MB response cap
- [x] **AC-3** Blocks private/link-local IPs (SSRF guard)
- [x] **AC-4** Referenced via `tools.builtin: [web_fetch]` in yaml
- [x] **AC-5** Unknown builtin ID fails validation with list of available IDs for current phase

### Implementation tasks (build)

- [x] Implement `src/zaumzeug/runtime/tools/web_fetch.py`
- [x] Register in `src/zaumzeug/runtime/tools/catalog.py` (phase-aware catalog)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E3-S03 / E3.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/tools/test_web_fetch.py::test_e3_s03_ac1_catalog_lists_web_fetch_phase1` |
| AC-2 | `tests/unit/runtime/tools/test_web_fetch.py::test_e3_s03_ac2_https_only_timeout_and_size_cap` |
| AC-3 | `tests/unit/runtime/tools/test_web_fetch.py::test_e3_s03_ac3_ssrf_blocks_private_ips` |
| AC-4 | `tests/integration/test_runtime_factory.py::test_e3_s03_ac4_yaml_builtin_reference` |
| AC-5 | `tests/unit/config/test_schemas.py::test_e3_s03_ac5_unknown_builtin_id_fails_with_list` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/runtime/tools/test_web_fetch.py -v` passes

### Definition of done

- [x] Catalog loader wired into runtime factory (`runtime/factory.py`; full serve wiring in E3-S02)
- [x] Verification checklist complete; all ACs traced to tests

---

## E3-S00 — Runtime factory (Haystack Agent builder)

| Field | Value |
|---|---|
| **Feature** | Foundation (Architecture §11 #4) |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E3-S01](#e3-s01-modelrouter) · [E3-S03](#e3-s03-builtin-tool-web-fetch) · [E2-S03](../01-epic.md#e2-s03-runtime-agent-resolution-rules) |

### User story

As an **SDK maintainer**, I want a runtime factory that builds a Haystack `Agent` from resolved config, so that serve/MCP/ACP share one code path.

### References

- [Architecture §11 #4 — Runtime factory](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build)
- [Architecture §2.1 — Golden rules](../architecture/01-overview-and-principles.md#21-golden-rules)
- [Architecture §2.3 — Agent loop](../architecture/01-overview-and-principles.md#23-harness-layer-mapping-guides-and-sensors)
- [Haystack Agents](https://docs.haystack.deepset.ai/docs/agents)

### Acceptance criteria

- [ ] **AC-1** `src/zaumzeug/runtime/factory.py` builds Haystack `Agent` from harness config
- [ ] **AC-2** Injects `ModelRouter` as chat generator backend
- [ ] **AC-3** Registers builtin tools from `tools.builtin`
- [ ] **AC-4** Loads `system_prompt` from resolved file path (E2-S03)
- [ ] **AC-5** **No DSPy or GEPA imports** in this module
- [ ] **AC-6** **No double agent loops** — single Haystack Agent only

### Implementation tasks (build)

- [ ] Implement `build_agent(harness_config, harness_root) -> Agent` in `runtime/factory.py`
- [ ] Wire `config/resolver.py` for prompt path
- [ ] Wire `runtime/tools/catalog.py` for builtins

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E3-S00`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac1_builds_agent_from_config` |
| AC-2 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac2_injects_model_router` |
| AC-3 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac3_registers_builtin_tools` |
| AC-4 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac4_loads_system_prompt_from_path` |
| AC-5 | `tests/unit/runtime/test_factory_imports.py::test_e3_s00_ac5_no_dspy_gepa_imports` |
| AC-6 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac6_single_agent_no_nested_loops` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/test_runtime_factory.py tests/unit/runtime/test_factory_imports.py -v` passes

### Definition of done

- [x] Used by `serve/runner.py` (E3-S02, 2026-07-20) — not duplicated in serve layer
- [x] Verification checklist complete; all ACs traced to tests

---

## E3-S02 — `zaumzeug serve` (dev mode)

| Field | Value |
|---|---|
| **Feature** | E3.2 |
| **Persona** | Harness developer · Client integrator |
| **Priority** | P0 |
| **Prerequisites** | [E3-S00](#e3-s00-runtime-factory-haystack-agent-builder) · [E2-S04a](../01-epic.md#e2-s04--zaumzeug-doctor-split-into-sub-stories) |
| **Status** | Done (2026-07-20) |
| **Open — carried forward** | [AC-6](#acceptance-criteria) · [AC-7](#acceptance-criteria) → [E1-S07](../03-epic.md#e1-s07-cross-platform-ci-matrix) |
| **Closed by E3-S04** | [DoD *serve example*](#definition-of-done) → [E3-S04](#e3-s04-example-harness-general-research-agent) (2026-07-20) |

### User story

As a **harness developer**, I want `zaumzeug serve <name>` to start Hayhooks from my dev harness folder, so that I can chat via OpenAI-compatible REST locally.

### References

- [PRD E3.2](../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §8.1 — Source roots](../architecture/06-runtime-and-protocols.md#81-source-roots)
- [Architecture §8.2 — harness vs hayhooks](../architecture/06-runtime-and-protocols.md#82-harness-vs-raw-hayhooks)
- [Architecture §9.1 — OpenAI REST](../architecture/06-runtime-and-protocols.md#91-protocol-selection)
- [Architecture §14 — localhost bind](../architecture/10-operations-and-reference.md#14-security-phase-1-stance)

### Acceptance criteria

- [x] **AC-1** Loads `usr-harnesses/<name>/` by default
- [x] **AC-2** Starts Hayhooks on port from `serve.hayhooks.port`
- [x] **AC-3** Binds **localhost** in Phase 1 (no wide-open `0.0.0.0` without explicit config)
- [x] **AC-4** `/v1/chat/completions` returns valid OpenAI-shaped JSON
- [x] **AC-5** Also exposes `GET /v1/models` per Architecture §9.4
- [ ] **AC-6** Identical behavior on Windows, macOS, Linux *(open — carried to [E1-S07](../03-epic.md#e1-s07-cross-platform-ci-matrix))*
- [ ] **AC-7** Smoke-tested in CI matrix with mock model *(open — carried to [E1-S07](../03-epic.md#e1-s07-cross-platform-ci-matrix))*

### Implementation tasks (build)

- [x] Implement `src/zaumzeug/serve/runner.py` — canonical entry (not raw `hayhooks run`)
- [x] Call `runtime/factory.build_agent()` then pass to Hayhooks
- [x] Register OpenAI-compatible routes via Hayhooks API
- [x] Add `--dry-run` integration with E2-S05 `validate_serve()` ([06-story.md](06-story.md#e2-s05-dry-run-on-serve) — Done; wired in E3-S02 runner)
- [x] Document Hayhooks escape hatch in `user-docs/reference/cli.md`

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E3-S02 / E3.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_serve.py::test_e3_s02_ac1_loads_usr_harnesses_path` |
| AC-2 | `tests/integration/test_serve.py::test_e3_s02_ac2_hayhooks_port_from_config` |
| AC-3 | `tests/integration/test_serve.py::test_e3_s02_ac3_localhost_bind_default` |
| AC-4 | `tests/integration/test_openai_contract.py::test_e3_s02_ac4_chat_completions_shape` *(shared E3-S07)* |
| AC-5 | `tests/integration/test_serve.py::test_e3_s02_ac5_get_v1_models` |
| AC-6 | **open — carried to** [E1-S07](../03-epic.md#e1-s07-cross-platform-ci-matrix) (three-OS matrix) |
| AC-7 | **open — carried to** [E1-S07](../03-epic.md#e1-s07-cross-platform-ci-matrix) (serve smoke job with mock model) |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/test_serve.py tests/integration/test_openai_contract.py -v -k e3_s02` passes locally

### Definition of done

- [x] `zaumzeug serve example` works with templates from E3-S04 (mock, no `.env`) *(closed by [E3-S04](#e3-s04-example-harness-general-research-agent) 2026-07-20)*
- [x] Verification checklist complete; all ACs traced to tests

---

## E3-S04 — Example harness (general research agent)

| Field | Value |
|---|---|
| **Feature** | E3.4 |
| **Persona** | Harness developer · SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](../01-epic.md#e2-s01-pydantic-config-schemas) · [E3-S03](#e3-s03-builtin-tool-web-fetch) · [E3-S02](#e3-s02-zaumzeug-serve-dev-mode) ✅ |
| **Status** | Done (2026-07-20) |
| **Closes open from** | [E3-S02 DoD](#e3-s02-zaumzeug-serve-dev-mode): *zaumzeug serve example works with templates* (closed 2026-07-20) |

### User story

As a **new user**, I want a reference example harness, so that I can learn config-only agents and run CI without API keys.

### References

- [PRD E3.4](../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §6.6](../architecture/05-configuration.md#66-phase-1-config-schema)
- [PRD Journey A](../prd.md#71-journey-a--config-only-harness-phase-1)

### Acceptance criteria

- [x] **AC-1** `example` uses `agents/researcher/` per Architecture §6.6
- [x] **AC-2** Includes `workflow.yaml` with one stage (`researcher`)
- [x] **AC-3** `agents/researcher/agents-models.yaml` with `default_model_id: mock`
- [x] **AC-4** `zaumzeug serve example` works without `.env`
- [x] **AC-5** No RAG until Epic E8
- [x] **AC-6** Templates under `install/templates/usr-harnesses/example/` for E1-S03

### Implementation tasks (build)

- [x] Author multi-agent template tree per Architecture §6.6 (`harness.yaml`, `workflow.yaml`, `agents/researcher/`)
- [x] Document in `user-docs/getting-started/first-harness.md`; link to [user-docs/guides/multi-agent-workflow.md](../../user-docs/guides/multi-agent-workflow.md) for workflow and pipelines (template copied by E1-S05)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E3-S04 / E3.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/usr-harnesses/fixture/test_example_harness.py::test_e3_s04_ac1_researcher_agent_layout` |
| AC-2 | `tests/usr-harnesses/fixture/test_example_harness.py::test_e3_s04_ac2_workflow_yaml_single_stage` |
| AC-3 | `tests/usr-harnesses/fixture/test_example_harness.py::test_e3_s04_ac3_agents_models_mock_default` |
| AC-4 | `tests/integration/test_serve.py::test_e3_s04_ac4_serve_example_without_env` |
| AC-5 | `tests/usr-harnesses/fixture/test_example_harness.py::test_e3_s04_ac5_no_rag_sections` |
| AC-6 | **manual:** template files exist under `install/templates/usr-harnesses/example/` — also asserted by `test_e3_s04_ac6_install_template_mirrors_example` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/usr-harnesses/fixture/test_example_harness.py -v` passes

### Definition of done

- [x] `zaumzeug doctor example` passes (exit 0; Phase 1 warnings only) with committed `usr-harnesses/example/` — install scaffolding copy path remains [E1-S03](../03-epic.md#e1-s03-project-scaffolding-on-install)
- [x] Closes [E3-S02 DoD](#e3-s02-zaumzeug-serve-dev-mode): *`zaumzeug serve example` works with templates* (mock, no `.env`)
- [x] Verification checklist complete; all ACs traced to tests

---

## E3-S06 — Phase 1 test infrastructure and security baseline

| Field | Value |
|---|---|
| **Feature** | Architecture §13, §14 (Phase 1) |
| **Persona** | SDK maintainer |
| **Priority** | P1 |
| **Prerequisites** | [E3-S02](#e3-s02-zaumzeug-serve-dev-mode) |
| **Status** | Done (2026-07-20) |

### User story

As an **SDK maintainer**, I want a test pyramid and Phase 1 security defaults, so that CI stays cheap and local dev does not expose unauthenticated endpoints broadly.

### References

- [Architecture §13.3 — Test pyramid](../architecture/10-operations-and-reference.md#133-test-pyramid)
- [Architecture §13.2 — Mechanisms](../architecture/10-operations-and-reference.md#132-mechanisms)
- [Architecture §14 — Security Phase 1](../architecture/10-operations-and-reference.md#14-security-phase-1-stance)
- [PRD G6](../prd.md#3-goals)

### Acceptance criteria

- [x] **AC-1** `tests/unit/` for config merge, ModelRouter mock, export snapshots (later); layout per [Architecture §13.3](../architecture/10-operations-and-reference.md#133-test-pyramid)
- [x] **AC-2** `tests/usr-harnesses/fixture/` minimal harness; `tests/fixtures/responses/` for mock profile
- [x] **AC-3** `HARNESS_LIVE_LLM=1` documented env for optional live API e2e ([Architecture §13.1](../architecture/10-operations-and-reference.md#131-design-principles))
- [x] **AC-4** Phase 1 serve binds localhost; documented in security notes
- [x] **AC-5** `debugpy` invocation documented for IDE attach ([Architecture §13.2](../architecture/10-operations-and-reference.md#132-mechanisms))

### Implementation tasks (build)

- [x] Create `tests/usr-harnesses/fixture/` with minimal valid Phase 1 yaml
- [x] Add `tests/unit/` structure per Architecture §13.3
- [x] Document `HARNESS_LIVE_LLM` and debugpy in `user-docs/reference/cli.md` and [user-docs/guides/testing.md](../../user-docs/guides/testing.md)
- [x] Verify serve runner defaults to localhost bind

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E3-S06`.

| AC | Test |
|---|---|
| AC-1 | **manual:** `tests/unit/` tree matches Architecture §13.3 layout (`config/`, `runtime/`, `export/` placeholder) |
| AC-2 | `tests/usr-harnesses/fixture/test_fixture_harness.py::test_e3_s06_ac2_minimal_harness_valid` |
| AC-3 | **manual:** `user-docs/reference/cli.md` documents `HARNESS_LIVE_LLM=1` |
| AC-4 | `tests/integration/test_serve.py::test_e3_s06_ac4_localhost_bind_enforced` |
| AC-5 | **manual:** CLI reference includes debugpy one-liner |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/usr-harnesses/fixture/ -v` passes

### Definition of done

- [x] CI uses mock only — no live LLM keys in default workflow (`tests/e2e/` skipped unless `HARNESS_LIVE_LLM=1`; `live_llm` marker registered)
- [x] Verification checklist complete; all ACs traced to tests or manual rows

---

## E3-S07 — OpenAI REST contract tests

| Field | Value |
|---|---|
| **Feature** | PRD E3 story seed |
| **Persona** | SDK maintainer |
| **Priority** | P1 |
| **Prerequisites** | [E3-S02](#e3-s02-zaumzeug-serve-dev-mode) · [E3-S05](#e3-s05-mock-model-profile) |

### User story

As an **SDK maintainer**, I want automated OpenAI-shaped request/response tests, so that client integrators can rely on a stable REST contract.

### References

- [PRD E3 story seeds](../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §9.4 — OpenAI-compatible](../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)

### Acceptance criteria

- [ ] **AC-1** Integration test POST `/v1/chat/completions` with mock model returns expected JSON shape (`choices`, `message`, `role`, `content`)
- [ ] **AC-2** Test accepts optional `model_id` in request body for ModelRouter override
- [ ] **AC-3** Test runs in CI without network (mock model, stub `web_fetch` if tool invoked)

### Implementation tasks (build)

- [ ] Add `tests/integration/test_openai_contract.py`
- [ ] Start serve on ephemeral port via subprocess or test fixture
- [ ] Stub HTTP for `web_fetch` when tool invoked in contract tests

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E3-S07`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_openai_contract.py::test_e3_s07_ac1_chat_completions_openai_shape` |
| AC-2 | `tests/integration/test_openai_contract.py::test_e3_s07_ac2_request_model_id_override` |
| AC-3 | `tests/integration/test_openai_contract.py::test_e3_s07_ac3_no_network_mock_and_stub_fetch` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/test_openai_contract.py -v` passes

### Definition of done

- [ ] Green on all three OS in CI matrix ([E1-S07](../03-epic.md#e1-s07-cross-platform-ci-matrix))
- [ ] Verification checklist complete; all ACs traced to tests

---

## E3-S08 — `zaumzeug run` (serial workflow)

| Field | Value |
|---|---|
| **Feature** | E3.6 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S07](../01-epic.md#e2-s07-workflowyaml-schema-serial) · [E3-S00](#e3-s00-runtime-factory-haystack-agent-builder) · [E3-S01](#e3-s01-modelrouter) |

### User story

As a **harness developer**, I want `zaumzeug run` to execute my harness workflow serially, so that multiple agents cooperate without manual orchestration.

### References

- [PRD E3.6](../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §5.2](../architecture/04-data-flows.md#52-runtime-agent-resolution)
- [Architecture §8.2](../architecture/06-runtime-and-protocols.md#82-harness-vs-raw-hayhooks)

### Acceptance criteria

- [ ] **AC-1** Executes `workflow.yaml` stages in order (serial only Phase 1)
- [ ] **AC-2** Each agent stage loads `agents/<name>/` config and merged `agents-models.yaml`
- [ ] **AC-3** Prior stage output passed as context to next agent stage
- [ ] **AC-4** Pipeline stages invoke exposed pipeline when `serve.expose` lists id (Phase 4+; stub OK in Phase 1)
- [ ] **AC-5** `--from <stage>` runs partial workflow for debugging
- [ ] **AC-6** Fails fast with harness + agent name on resolution errors
- [ ] **AC-7** Integration test: two-agent serial workflow with mock models

### Implementation tasks (build)

- [ ] Implement `src/zaumzeug/runtime/workflow.py` serial executor
- [ ] Add `run` subcommand in `src/zaumzeug/cli.py`
- [ ] Reuse runtime factory per stage with stage-scoped ModelRouter

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E3-S08 / E3.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_workflow_run.py::test_e3_s08_ac1_serial_stage_order` |
| AC-2 | `tests/integration/test_workflow_run.py::test_e3_s08_ac2_per_agent_models_registry` |
| AC-3 | `tests/integration/test_workflow_run.py::test_e3_s08_ac3_stage_output_forwarded` |
| AC-4 | **manual:** pipeline stage deferred Phase 4 |
| AC-5 | `tests/integration/test_workflow_run.py::test_e3_s08_ac5_from_stage_partial_run` |
| AC-6 | `tests/integration/test_workflow_run.py::test_e3_s08_ac6_actionable_agent_error` |
| AC-7 | `tests/integration/test_workflow_run.py::test_e3_s08_ac7_two_agent_mock_workflow` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/test_workflow_run.py -v` passes

### Definition of done

- [ ] `zaumzeug run example` works with single-stage workflow
- [ ] Verification checklist complete; all ACs traced to tests
