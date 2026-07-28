# E6-S03 — Eval gate on deploy

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/36-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E6-S03 |
| **Epic** | [E6 — Evaluation and Quality (Optional)](../05-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 5 of 8 |
| **Story sequence** | 36 of 63 (global build order) |
| **Source** | Extracted from [`05-epic.md`](../05-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E6](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) · [Architecture](../../architecture.md) |

---

## E6-S03 — Eval gate on deploy

| Field | Value |
|---|---|
| **Feature** | E6.3 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Traceability slice — **implementation owner: [E5-S06](46-story.md#e5-s06-deploy-eval-gate)** |
| **Prerequisites** | [E5-S06](46-story.md#e5-s06-deploy-eval-gate) *(implementation owner)* · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command) ✅ |

### User story

As a **harness developer**, I want deploy to respect eval gates, so that failed regression tests can block releases.

### References

- [PRD E6.3](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [E5-S06 — Deploy eval gate](../06-epic.md#e5-s06-deploy-eval-gate)


### Implementation resources

**Internal spec**

- Implementation owner: [E5-S06](46-story.md) — this story is traceability only
- [Architecture §6.4 — deploy eval gate](../../architecture/05-configuration.md#64-deploy-eval-gate)

### Acceptance criteria

- [ ] **AC-1** Covered by E5-S06 implementation
- [ ] **AC-2** Eval runner invoked from deploy packager when gate is `warn` or `block`

### Implementation tasks (build)

- [ ] Cross-link tests between E5 and E6
- [ ] Document in harness.yaml `deploy.eval_gate` examples

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **Cross-story** — primary tests live under E5-S06.

| AC | Test |
|---|---|
| AC-1 | **shared:** [E5-S06](46-story.md#e5-s06-deploy-eval-gate) Verification table |
| AC-2 | `tests/unit/deploy/test_eval_gate.py::test_e6_s03_ac2_packager_invokes_eval_runner` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] E5-S06 and E6-S03 verification tables both reference same tests

### Definition of done

- [ ] Single source of truth in deploy packager (no duplicate gate logic)
- [ ] Verification checklist complete

---
