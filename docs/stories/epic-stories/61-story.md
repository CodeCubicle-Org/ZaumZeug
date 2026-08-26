# E8-S04 — Optional A2A agent card

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/61-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-26 |
| **Story ID** | E8-S04 |
| **Status** | Done (2026-08-26) |
| **Epic** | [E8 — RAG and Production Hardening](../08-epic.md) |
| **Phase** | 4 |
| **Epic build order** | 8 of 8 |
| **Story sequence** | 61 of 63 (global build order) |
| **Source** | Extracted from [`08-epic.md`](../08-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E8](../../prd.md#epic-e8--rag-and-production-hardening-phase-4) · [Architecture](../../architecture.md) |

---

## E8-S04 — Optional A2A agent card

| Field | Value |
|---|---|
| **Feature** | E8.4 |
| **Persona** | Client integrator |
| **Priority** | P3 |
| **Status** | Done (2026-08-26) |

### User story

As an **integrator building agent fleets**, I want optional A2A hosting, so that other agents can discover and delegate to my harness.

### References

- [PRD E8.4](../../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §9.1 — A2A row](../../architecture/06-runtime-and-protocols.md#91-protocol-selection)
- [PRD open #5](../../prd.md#12-open-decisions-blockers-for-some-stories) — **Resolved: ship Phase 4** (2026-08-26)

### Blocker

- [x] Resolve A2A in Phase 4 vs defer before implementation — **ship Phase 4** (open #5, 2026-08-26)

### Acceptance criteria

- [x] **AC-1** `serve.a2a: true` hosts agent card endpoint
- [x] **AC-2** Documented separately from MCP and ACP
- [x] **AC-3** Does not conflict with NG1 multi-tenant scope

### Implementation tasks (build)

- [x] Evaluate Haystack/A2A integration path — Hayhooks `hayhooks[a2a]` / `create_a2a_app`
- [x] Add config schema and serve registration — `A2aConfig`, `zaumzeug a2a`, registry `skip_a2a=False`
- [x] Document agent fleet layout — [a2a.md](../../../user-docs/guides/a2a.md)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E8-S04 / E8.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/a2a/test_a2a_agent_card.py::test_e8_s04_ac1_serve_a2a_hosts_agent_card` (+ disabled-without-config) |
| AC-2 | `tests/integration/a2a/test_a2a_agent_card.py::test_e8_s04_ac2_documented_separately_from_mcp_and_acp` |
| AC-3 | `tests/integration/a2a/test_a2a_agent_card.py::test_e8_s04_ac3_does_not_conflict_with_ng1` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/a2a/ tests/unit/config/test_schemas.py -k a2a -v` passes

### Definition of done

- [x] Explicit phase gate in PRD updated when shipped or deferred — open #5 resolved; E8.4 Done
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-26)

- Config: `serve.a2a: true` or `{enabled, port}` (default port **1418**); unblocked from `PHASE_GATED_FIELDS`.
- Serve: `zaumzeug a2a <name>` → Hayhooks `create_a2a_app`; agent card at `/{harness}/.well-known/agent-card.json`. Requires `pip install "hayhooks[a2a]"`.
- Docs: [a2a.md](../../../user-docs/guides/a2a.md) (fleet layout; ≠ MCP/ACP; NG1 one harness per process).
- Tests: `tests/integration/a2a/test_a2a_agent_card.py`.

---
