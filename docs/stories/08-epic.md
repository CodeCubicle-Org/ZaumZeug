# Epic E8 — RAG and Production Hardening

| | |
|---|---|
| **Document** | Epic E8 user stories |
| **File** | `docs/stories/08-epic.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-14 (E8-S07 AC-5 follow-up: `tools.custom` unblocked by E7-S02) |
| **Status** | Backlog |
| **Build order** | **8 of 8** |
| **Related** | [PRD](../prd.md) · [Architecture](../architecture.md) · [Index](00-README.md) |

---
| Field | Value |
|---|---|
| **Phase** | 4 |
| **Epic** | E8 |
| **Outcome** | Pipelines, auth, observability, optional A2A. Pattern B / `optimize_anything` is **Done** in E4 ([E4-S04](../04-epic.md#e4-s04-haystack-gepa-evaluator-wrapper)); optional deeper pipeline-artifact use with RAG remains open. |
| **Depends on** | [E5](06-epic.md) · [E6](05-epic.md) · [E7](07-epic.md) |
| **Blocks** | — (completes v1 roadmap) |
| **PRD** | [Epic E8](../prd.md#epic-e8--rag-and-production-hardening-phase-4) |
| **Architecture** | [§6.2 pipelines](../architecture/05-configuration.md#62-config-sections) · [§10.1 deploy copy](../architecture/07-deploy-packaging.md#101-dev-vs-deploy) · [§12 Pattern B](../architecture/08-compile-and-optimization.md#pattern-b-optimize-anything-deferred-phase-4) · [§13.5 Phase 4](../architecture/10-operations-and-reference.md#135-phase-mapping) |
| **Journey** | [Journey C](../prd.md#73-journey-c--improve-after-failure-phase-2) |
| **Open decisions** | [#5 A2A](../prd.md#12-open-decisions-blockers-for-some-stories) |

### Story implementation order (within this epic)

1. **E8-S07** — Workflow run reliability and stage transparency ✅ *(2026-08-01; P0 pull-forward)*
2. **E8-S01** — Pipeline exposure / RAG
3. **E8-S03** — Trace → dataset ratchet
4. **E8-S02** — Production auth *(Traefik proxy-only — resolved)*
5. **E8-S05** — Dockerfile template
6. **E8-S06** — DeepEval observe
7. **E8-S04** — A2A *(if open #5 resolves to Phase 4)*

*(E4-S04 Pattern B evaluator ✅ 2026-07-28 — no longer queued under E8.)*
*(E8-S07 added 2026-08-01 from adoption evaluation — run-path retry, typed live errors, INFO logs with structured `stage`, `output.format: json` only, doctor fail on phase-gated MCP in default + `--deploy`, docs AC-6. No OTel / no JSON Schema / serve path follow-up.)*

---

## E8-S01 — Pipeline exposure via `serve.expose`

| Field | Value |
|---|---|
| **Feature** | E8.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |

### User story

As a **harness developer**, I want user pipelines exposed via config, so that I can ship RAG and batch flows alongside the agent.

### References

- [PRD E8.1](../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §3.3 — `pipelines/`](../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- [Architecture §10.1 — pipeline copy rules](../architecture/07-deploy-packaging.md#101-dev-vs-deploy)
- [Haystack Pipelines](https://docs.haystack.deepset.ai/docs/pipelines)

### Acceptance criteria

- [ ] **AC-1** User `pipelines/` exposed via `serve.expose` in yaml
- [ ] **AC-2** RAG path documented with retriever → prompt → generator pattern
- [ ] **AC-3** Pipelines listed in `serve.expose` copied to deploy bundle *(packager row **Done** early with [E5-S02](epic-stories/42-story.md), 2026-07-28; Phase 4 serve remains this story)*
- [ ] **AC-4** `POST /{pipeline}/run` available per Architecture §9.1

### Implementation tasks (build)

- [ ] Extend serve runner to register exposed pipelines
- [ ] Add Phase 4 config schema for `serve.expose`
- [ ] Example RAG harness in user-docs (optional)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E8-S01 / E8.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/pipelines/test_serve_expose.py::test_e8_s01_ac1_pipelines_registered_from_yaml` |
| AC-2 | **manual:** user-docs RAG pattern documented |
| AC-3 | **shared early:** `tests/unit/deploy/test_copy_rules.py::test_e8_s01_ac3_exposed_pipelines_in_deploy` *(packager copy landed with [E5-S02](epic-stories/42-story.md), 2026-07-28)* |
| AC-4 | `tests/integration/pipelines/test_serve_expose.py::test_e8_s01_ac4_post_pipeline_run_endpoint` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/pipelines/test_serve_expose.py -v` passes

### Definition of done

- [ ] `search_docs` builtin can attach when RAG pipeline present (§6.5 Phase 4)
- [ ] Verification checklist complete; all ACs traced to tests

---

## E8-S02 — Production auth

| Field | Value |
|---|---|
| **Feature** | E8.2 |
| **Persona** | Ops / platform |
| **Priority** | P1 |

### User story

As **ops**, I want an auth story for production serve, so that harness endpoints are not wide open on the public internet.

### References

- [PRD E8.2](../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §14 — Security](../architecture/10-operations-and-reference.md#14-security-phase-1-stance)
- [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/) · [Traefik Headers middleware](https://doc.traefik.io/traefik/middlewares/http/headers/)

### Decision (resolved)

**Proxy-only via Traefik** — production auth lives at the edge, not in ZaumZeug/Hayhooks. Traefik terminates TLS and applies bearer/API-key or ForwardAuth middleware; harness process binds behind the proxy (e.g. `127.0.0.1` or Docker internal network). **No `serve.auth` in SDK v1.**

### Acceptance criteria

- [ ] **AC-1** `user-docs/guides/production-auth.md` documents Traefik as the **reference** production pattern
- [ ] **AC-2** Cover REST (`/v1/chat/completions`), MCP (`/mcp`), and Chainlit (`/chat`) path routing
- [ ] **AC-3** Example Traefik static/dynamic config: TLS, Headers middleware (bearer validation) or ForwardAuth
- [ ] **AC-4** `README.deploy.md` links to guide; notes Hayhooks has no built-in auth in v1
- [ ] **AC-5** Document Nginx/Caddy as optional alternatives (same proxy-only principle)
- [ ] **AC-6** No secrets in yaml or deploy bundle; auth credentials only in Traefik/env on target host

### Implementation tasks (build)

- [ ] Author `user-docs/guides/production-auth.md` with Traefik examples
- [ ] Add `deploy/<name>/` optional `traefik/` snippet or comment block in `README.deploy.md`
- [ ] Cross-link from [E7-S08](07-epic.md) web-deployment guide — **forward link already in** [web-deployment.md](../../user-docs/guides/web-deployment.md) (2026-08-21); this task is the reverse link from `production-auth.md`
- [ ] **Do not** add in-process auth to serve layer in v1

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). **Docs-only** — manual checklist; confirm no SDK auth code added.

| AC | Verification |
|---|---|
| AC-1 | **manual:** production-auth.md exists with Traefik as reference |
| AC-2 | **manual:** REST, MCP, Chainlit paths documented |
| AC-3 | **manual:** example Traefik config blocks present and valid YAML |
| AC-4 | **manual:** README.deploy.md links to guide |
| AC-5 | **manual:** Nginx/Caddy alternatives noted |
| AC-6 | `tests/integration/deploy/test_deploy.py::test_e8_s02_ac6_no_secrets_in_bundle` *(extends deploy tests)* |

- [ ] Manual checklist completed; no in-process auth in codebase

### Definition of done

- [ ] Ops can deploy harness behind Traefik with TLS + bearer auth using docs only
- [ ] Verification checklist complete

---

## E8-S03 — Trace → dataset ratchet

| Field | Value |
|---|---|
| **Feature** | E8.3 |
| **Persona** | Harness developer |
| **Priority** | P1 |

### User story

As a **harness developer**, I want production traces to feed back into datasets, so that the compile loop improves from real failures.

### References

- [PRD E8.3](../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §5.5](../architecture/04-data-flows.md#55-continuous-improvement-loop)
- [E6-S05 — Trace export](../05-epic.md#e6-s05-trace-test-case) ✅ (2026-07-28)

### Acceptance criteria

- [ ] **AC-1** Production traces append to dataset (JSONL under `data/`)
- [ ] **AC-2** Feeds compile loop: trace → valset → eval → compile → deploy
- [ ] **AC-3** Future: `harness replay <name> --trace` documented as deferred ([PRD §9](../prd.md#9-cli-surface-epic-mapping))

### Implementation tasks (build)

- [ ] Production trace export hook (Haystack `track_stats` or OTel stub)
- [ ] Helper to merge traces into `data/val.jsonl` / `data/train.jsonl`
- [ ] Document ratchet workflow in user-docs

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E8-S03 / E8.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_trace_ratchet.py::test_e8_s03_ac1_production_trace_appends_jsonl` |
| AC-2 | `tests/integration/eval/test_journey_c.py::test_e8_s03_ac2_trace_to_compile_loop` |
| AC-3 | **manual:** user-docs notes replay as deferred |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/eval/test_trace_ratchet.py -v` passes

### Definition of done

- [ ] Journey C complete with production trace source
- [ ] Verification checklist complete; all ACs traced to tests

---

## E8-S04 — Optional A2A agent card

| Field | Value |
|---|---|
| **Feature** | E8.4 |
| **Persona** | Client integrator |
| **Priority** | P3 (defer per open #5) |

### User story

As an **integrator building agent fleets**, I want optional A2A hosting, so that other agents can discover and delegate to my harness.

### References

- [PRD E8.4](../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §9.1 — A2A row](../architecture/06-runtime-and-protocols.md#91-protocol-selection)
- [PRD open #5](../prd.md#12-open-decisions-blockers-for-some-stories)

### Blocker

- [ ] Resolve A2A in Phase 4 vs defer before implementation

### Acceptance criteria (when prioritized)

- [ ] **AC-1** `serve.a2a: true` hosts agent card endpoint
- [ ] **AC-2** Documented separately from MCP and ACP
- [ ] **AC-3** Does not conflict with NG1 multi-tenant scope

### Implementation tasks (when unblocked)

- [ ] Evaluate Haystack/A2A integration path
- [ ] Add config schema and serve registration
- [ ] Document agent fleet layout

### Verification (when unblocked)

Apply [Story verification](00-README.md#story-verification-required). `tests/integration/a2a/` with AC-1–AC-3 mapping.

### Definition of done

- [ ] Explicit phase gate in PRD updated when shipped or deferred

---

## E8-S05 — Dockerfile template

| Field | Value |
|---|---|
| **Feature** | E8.5 |
| **Persona** | Ops / platform |
| **Priority** | P2 |

### User story

As **ops**, I want an optional generated Dockerfile in the deploy bundle, so that I can containerize production serve quickly.

### References

- [PRD E8.5](../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [E5-S08 — Platform policy](../06-epic.md#e5-s08-deploy-platform-policy) ✅ (2026-07-29)
- [Architecture §10.6](../architecture/07-deploy-packaging.md#106-deploy-platform-targets)

### Acceptance criteria

- [ ] **AC-1** Optional generated `deploy/<name>/Dockerfile` (config flag or deploy flag)
- [ ] **AC-2** Base image Python 3.11+; runs `target_install` pattern or pre-baked venv
- [ ] **AC-3** Document `zaumzeug serve <name> --deploy` as container CMD
- [ ] **AC-4** `.env` injected at runtime, not baked into image

### Implementation tasks (build)

- [ ] Add Dockerfile template to deploy packager
- [ ] Document build/run in `README.deploy.md`
- [ ] Example docker-compose for Open WebUI + harness (optional) — **layout recipe already in** [web-deployment.md](../../user-docs/guides/web-deployment.md) (E7-S08, 2026-08-21); this story still owns a generated bundle Dockerfile

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E8-S05 / E8.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_dockerfile.py::test_e8_s05_ac1_dockerfile_generated_when_flagged` |
| AC-2 | `tests/integration/deploy/test_dockerfile.py::test_e8_s05_ac2_python311_base_and_target_install` |
| AC-3 | **manual:** README.deploy.md documents CMD |
| AC-4 | `tests/integration/deploy/test_dockerfile.py::test_e8_s05_ac4_no_env_baked_in_image` |
| AC-1–4 | **optional CI:** Linux container smoke test |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/deploy/test_dockerfile.py -v` passes

### Definition of done

- [ ] Linux container smoke test on CI (optional)
- [ ] Verification checklist complete; all ACs traced to tests

---

## E8-S06 — DeepEval production observe (opt-in)

| Field | Value |
|---|---|
| **Feature** | E8.6 |
| **Persona** | Harness developer |
| **Priority** | P3 |

### User story

As a **harness developer**, I want optional DeepEval `@observe` in production, so that I can sync traces to Confident AI when explicitly opted in.

### References

- [PRD E8.6](../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §6.3 — Mode B tracing](../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)
- [DeepEval](https://github.com/confident-ai/deepeval)

### Acceptance criteria

- [ ] **AC-1** Opt-in only — not default for production ([PRD NG2](../prd.md#4-non-goals-v1))
- [ ] **AC-2** `@observe` + Confident AI sync when `eval.confident_ai.enabled`
- [ ] **AC-3** Requires `deepeval login` and `[eval]` extra on server if enabled
- [ ] **AC-4** Document privacy and cost implications
- [ ] **AC-5** Default production deploy has no DeepEval dependency (E5-S05)

### Implementation tasks (build)

- [ ] Wrap agent run path with optional observe decorator
- [ ] Config gate: explicit `serve.observability.deepeval: true` or similar
- [ ] Warn in doctor when enabled without credentials

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E8-S06 / E8.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_observe.py::test_e8_s06_ac1_observe_off_by_default` |
| AC-2 | `tests/unit/eval/test_observe.py::test_e8_s06_ac2_observe_when_confident_ai_enabled` |
| AC-3 | `tests/unit/cli/test_doctor.py::test_e8_s06_ac3_doctor_warns_missing_deepeval_login` |
| AC-4 | **manual:** user-docs privacy and cost section |
| AC-5 | **shared:** `tests/integration/deploy/test_target_install.py::test_e5_s05_ac3_no_dspy_gepa_deepeval` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/eval/test_observe.py -v` passes

### Definition of done

- [ ] Default production deploy has no DeepEval dependency (E5-S05)
- [ ] Verification checklist complete; all ACs traced to tests

---

## E8-S07 — Workflow run reliability and stage transparency

| Field | Value |
|---|---|
| **Feature** | E8.7 |
| **Persona** | Client integrator · Harness developer · Ops |
| **Priority** | P0 |
| **Prerequisites** | [E3-S08](epic-stories/17-story.md) ✅ · [E2-S06](epic-stories/07-story.md) ✅ · [E2-S04b](epic-stories/05.2-story.md) ✅ |
| **Pull-forward** | Yes — after E5; does **not** require E7 |

### User story

As a **client integrator running local or flaky model backends**, I want `run_workflow` to surface stage-scoped failures, optionally retry them, validate JSON stage outputs, and emit structured stage logs — so batch reviews are reliable without OpenTelemetry or call-site workarounds.

### References

- [PRD E8.7](../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §2.4 — failure ladder](../architecture/01-overview-and-principles.md#24-industry-patterns)
- Full story: [64-story.md](epic-stories/64-story.md)

### Acceptance criteria

- [x] **AC-1** Live generation failures on `run_workflow` → typed `WorkflowError` with harness/agent/stage
- [x] **AC-2** Harness-level `runtime.retry` (`max_attempts >= 1`, default 1); build + message prep once; retry only `agent.run` + JSON check
- [x] **AC-3** Stage lifecycle via `log_request()` at INFO with structured `stage` key; reconstructible with INFO / `--verbose`
- [x] **AC-4** Optional agent `output.format: json` (parse + fence strip; empty fails; no JSON Schema)
- [x] **AC-5** Doctor **and** `doctor --deploy` **fail** on phase-gated `tools.mcp` / `tools.custom` *(shipped 2026-08-01; superseded: `tools.mcp` allowed as of [E7-S01](epic-stories/50-story.md); `tools.custom` allowed as of [E7-S02](epic-stories/51-story.md) — doctor `custom_tools` fails on import errors instead)*
- [x] **AC-6** User-docs + Architecture §6 document `runtime` / `output` and log contract

### Implementation tasks (build)

- [x] See [64-story.md](epic-stories/64-story.md) for tasks, config sketches, retry boundary, and verification table — **Done** (2026-08-01)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E8-S07 / E8.7`.

| AC | Test |
|---|---|
| AC-1–4 | `tests/unit/runtime/test_workflow_reliability.py` · `tests/integration/test_workflow_reliability.py` (`-k e8_s07`) |
| AC-5 | `tests/unit/cli/test_doctor.py` (`test_e8_s07_ac5_*`, incl. deploy mode) |
| AC-6 | **manual:** user-docs + Architecture §6 |
| Regression | `tests/integration/test_workflow_run.py` (E3-S08 defaults) |

- [x] `pytest … -k e8_s07 -v` and `pytest tests/integration/test_workflow_run.py -v` pass

### Definition of done

- [x] Defaults preserve pre-story behavior; E3-S08 regression green; run-path only; no OTel / no `jsonschema`
- [x] User-docs + Architecture §6 cover `runtime.retry` and `output.format`
- [x] Verification checklist complete; all ACs traced to tests
