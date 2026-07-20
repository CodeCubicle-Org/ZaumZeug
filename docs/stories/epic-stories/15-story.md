# E3-S06 — Phase 1 test infrastructure and security baseline

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/15-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-20 |
| **Story ID** | E3-S06 |
| **Status** | Done |
| **Epic** | [E3 — Runtime and Local Serve](../02-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 2 of 8 |
| **Story sequence** | 15 of 63 (global build order) |
| **Source** | Extracted from [`02-epic.md`](../02-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1) · [Architecture](../../architecture.md) |

---

## E3-S06 — Phase 1 test infrastructure and security baseline

| Field | Value |
|---|---|
| **Feature** | Architecture §13, §14 (Phase 1) |
| **Persona** | SDK maintainer |
| **Priority** | P1 |
| **Prerequisites** | [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) |
| **Status** | Done (2026-07-20) |

### User story

As an **SDK maintainer**, I want a test pyramid and Phase 1 security defaults, so that CI stays cheap and local dev does not expose unauthenticated endpoints broadly.

### References

- [Architecture §13.3 — Test pyramid](../../architecture/10-operations-and-reference.md#133-test-pyramid)
- [Architecture §13.2 — Mechanisms](../../architecture/10-operations-and-reference.md#132-mechanisms)
- [Architecture §14 — Security Phase 1](../../architecture/10-operations-and-reference.md#14-security-phase-1-stance)
- [PRD G6](../../prd.md#3-goals)


### Implementation resources

**Libraries & docs**

- [pytest](https://docs.pytest.org/) · [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Architecture §13.3 — test pyramid layout](../../architecture/10-operations-and-reference.md#133-test-pyramid)
- [Architecture §13.6 — testing playbook](../../architecture/10-operations-and-reference.md#136-testing-playbook)
- [User guide — testing](../../../install/templates/user-docs/guides/testing.md)
- [debugpy — IDE attach](https://github.com/microsoft/debugpy)

### Acceptance criteria

- [x] **AC-1** `tests/unit/` for config merge, ModelRouter mock, export snapshots (later); layout per [Architecture §13.3](../../architecture/10-operations-and-reference.md#133-test-pyramid)
- [x] **AC-2** `tests/usr-harnesses/fixture/` minimal harness; `tests/fixtures/responses/` for mock profile
- [x] **AC-3** `HARNESS_LIVE_LLM=1` documented env for optional live API e2e ([Architecture §13.1](../../architecture/10-operations-and-reference.md#131-design-principles))
- [x] **AC-4** Phase 1 serve binds localhost; documented in security notes
- [x] **AC-5** `debugpy` invocation documented for IDE attach ([Architecture §13.2](../../architecture/10-operations-and-reference.md#132-mechanisms))

### Implementation tasks (build)

- [x] Create `tests/usr-harnesses/fixture/` with minimal valid Phase 1 yaml
- [x] Add `tests/unit/` structure per Architecture §13.3
- [x] Document `HARNESS_LIVE_LLM` and debugpy in `user-docs/reference/cli.md` and [user-docs/guides/testing.md](../../user-docs/guides/testing.md)
- [x] Verify serve runner defaults to localhost bind

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S06`.

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
