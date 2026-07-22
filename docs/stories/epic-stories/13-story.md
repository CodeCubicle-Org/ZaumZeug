# E3-S02 — `zaumzeug serve` (dev mode)

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/13-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-22 |
| **Story ID** | E3-S02 |
| **Status** | Done |
| **Epic** | [E3 — Runtime and Local Serve](../02-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 2 of 8 |
| **Story sequence** | 13 of 63 (global build order) |
| **Source** | Extracted from [`02-epic.md`](../02-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1) · [Architecture](../../architecture.md) · **Closes open DoD from** [E3-S00](12-story.md#definition-of-done) · **Open ACs closed by** [E1-S07](24-story.md) · **Closed by** [E3-S04](14-story.md) (*serve example*) |

---

## E3-S02 — `zaumzeug serve` (dev mode)

| Field | Value |
|---|---|
| **Feature** | E3.2 |
| **Persona** | Harness developer · Client integrator |
| **Priority** | P0 |
| **Prerequisites** | [E3-S00](12-story.md#e3-s00-runtime-factory-haystack-agent-builder) · [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) |
| **Carries forward (closed here)** | [E3-S00 DoD](12-story.md#definition-of-done): *Used by `serve/runner.py` — not duplicated in serve layer* (closed 2026-07-20) |
| **Open — carried forward** | — |
| **Closed by E1-S07** | [AC-6](#acceptance-criteria) · [AC-7](#acceptance-criteria) → [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) (2026-07-22) |
| **Closed by E3-S04** | [DoD *serve example*](#definition-of-done) → [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent) (2026-07-20) |

### User story

As a **harness developer**, I want `zaumzeug serve <name>` to start Hayhooks from my dev harness folder, so that I can chat via OpenAI-compatible REST locally.

### References

- [PRD E3.2](../../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §8.1 — Source roots](../../architecture/06-runtime-and-protocols.md#81-source-roots)
- [Architecture §8.2 — harness vs hayhooks](../../architecture/06-runtime-and-protocols.md#82-harness-vs-raw-hayhooks)
- [Architecture §9.1 — OpenAI REST](../../architecture/06-runtime-and-protocols.md#91-protocol-selection)
- [Architecture §14 — localhost bind](../../architecture/10-operations-and-reference.md#14-security-phase-1-stance)


### Implementation resources

**Libraries & docs**

- [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks)
- [Hayhooks OpenAI-compatible endpoints](https://docs.haystack.deepset.ai/docs/hayhooks#openai-compatible-endpoints)
- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat)
- [Architecture §9.1 — protocol selection](../../architecture/06-runtime-and-protocols.md#91-protocol-selection)
- [Architecture §14 — localhost bind Phase 1](../../architecture/10-operations-and-reference.md#14-security-phase-1-stance)

**Test client sketch**

```python
import httpx
r = httpx.post(f"{base}/v1/chat/completions", json={
    "model": "mock", "messages": [{"role": "user", "content": "hi"}]
})
```

### Acceptance criteria

- [x] **AC-1** Loads `usr-harnesses/<name>/` by default
- [x] **AC-2** Starts Hayhooks on port from `serve.hayhooks.port`
- [x] **AC-3** Binds **localhost** in Phase 1 (no wide-open `0.0.0.0` without explicit config)
- [x] **AC-4** `/v1/chat/completions` returns valid OpenAI-shaped JSON
- [x] **AC-5** Also exposes `GET /v1/models` per Architecture §9.4
- [x] **AC-6** Identical behavior on Windows, macOS, Linux *(closed by [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) — Done 2026-07-22)*
- [x] **AC-7** Smoke-tested in CI matrix with mock model *(closed by [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) — Done 2026-07-22)*

### Implementation tasks (build)

- [x] Implement `src/zaumzeug/serve/runner.py` — canonical entry (not raw `hayhooks run`)
- [x] Call `runtime/factory.build_agent()` then pass to Hayhooks — **closes** [E3-S00 DoD](12-story.md#definition-of-done) (*Used by `serve/runner.py` — not duplicated in serve layer*); do **not** reimplement Agent construction in the serve layer
- [x] Register OpenAI-compatible routes via Hayhooks API
- [x] Call `validate_serve()` from runner before Hayhooks bind ([E2-S05](06-story.md#e2-s05-dry-run-on-serve) — `validate_serve()` available)
- [x] Document Hayhooks escape hatch in `user-docs/reference/cli.md`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S02 / E3.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_serve.py::test_e3_s02_ac1_loads_usr_harnesses_path` |
| AC-2 | `tests/integration/test_serve.py::test_e3_s02_ac2_hayhooks_port_from_config` |
| AC-3 | `tests/integration/test_serve.py::test_e3_s02_ac3_localhost_bind_default` |
| AC-4 | `tests/integration/test_openai_contract.py::test_e3_s02_ac4_chat_completions_shape` *(shared E3-S07)* |
| AC-5 | `tests/integration/test_serve.py::test_e3_s02_ac5_get_v1_models` |
| AC-6 | **closed by** [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) (three-OS matrix — Done 2026-07-22) |
| AC-7 | **closed by** [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) (serve smoke via `install/ci_serve_smoke.py` — Done 2026-07-22) |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/test_serve.py tests/integration/test_openai_contract.py -v -k e3_s02` passes locally

### Definition of done

- [x] `zaumzeug serve example` works with templates from E3-S04 (mock, no `.env`) *(closed by [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent) 2026-07-20)*
- [x] `serve/runner.py` uses `runtime/factory.build_agent()` only — check off [E3-S00](12-story.md#definition-of-done) DoD *Used by `serve/runner.py`*
- [x] Verification checklist complete; all ACs traced to tests

---
