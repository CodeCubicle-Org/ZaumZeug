# E8-S03 — Trace → dataset ratchet

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/60-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E8-S03 |
| **Epic** | [E8 — RAG and Production Hardening](../08-epic.md) |
| **Phase** | 4 |
| **Epic build order** | 8 of 8 |
| **Story sequence** | 60 of 63 (global build order) |
| **Source** | Extracted from [`08-epic.md`](../08-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E8](../../prd.md#epic-e8--rag-and-production-hardening-phase-4) · [Architecture](../../architecture.md) |

---

## E8-S03 — Trace → dataset ratchet

| Field | Value |
|---|---|
| **Feature** | E8.3 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E6-S05](38-story.md#e6-s05-trace-test-case) |

### User story

As a **harness developer**, I want production traces to feed back into datasets, so that the compile loop improves from real failures.

### References

- [PRD E8.3](../../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §5.5](../../architecture/04-data-flows.md#55-continuous-improvement-loop)
- [E6-S05 — Trace export](../05-epic.md#e6-s05-trace-test-case)


### Implementation resources

**Libraries & docs**

- [DeepEval datasets](https://docs.confident-ai.com/docs/evaluation-datasets)
- [Architecture §5.5 — trace → dataset loop](../../architecture/04-data-flows.md#55-continuous-improvement-loop)

### Acceptance criteria

- [ ] **AC-1** Production traces append to dataset (JSONL under `data/`)
- [ ] **AC-2** Feeds compile loop: trace → valset → eval → compile → deploy
- [ ] **AC-3** Future: `harness replay <name> --trace` documented as deferred ([PRD §9](../../prd.md#9-cli-surface-epic-mapping))

### Implementation tasks (build)

- [ ] Production trace export hook (Haystack `track_stats` or OTel stub)
- [ ] Helper to merge traces into `data/val.jsonl` / `data/train.jsonl`
- [ ] Document ratchet workflow in user-docs

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E8-S03 / E8.3`.

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
