# E8-S04 — Optional A2A agent card

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/61-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E8-S04 |
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
| **Priority** | P3 (defer per open #5) |

### User story

As an **integrator building agent fleets**, I want optional A2A hosting, so that other agents can discover and delegate to my harness.

### References

- [PRD E8.4](../../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §9.1 — A2A row](../../architecture/06-runtime-and-protocols.md#91-protocol-selection)
- [PRD open #5](../../prd.md#12-open-decisions-blockers-for-some-stories)

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

Apply [Story verification](../00-README.md#story-verification-required). `tests/integration/a2a/` with AC-1–AC-3 mapping.

### Definition of done

- [ ] Explicit phase gate in PRD updated when shipped or deferred

---
