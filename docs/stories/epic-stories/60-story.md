# E8-S03 — Trace → dataset ratchet

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/60-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-26 |
| **Story ID** | E8-S03 |
| **Status** | Done (2026-08-26) |
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
| **Prerequisites** | [E6-S05](38-story.md#e6-s05-trace-test-case) ✅ (2026-07-28) |
| **Status** | Done (2026-08-26) |

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

- [x] **AC-1** Production traces append to dataset (JSONL under `data/`)
- [x] **AC-2** Feeds compile loop: trace → valset → eval → compile → deploy
- [x] **AC-3** Future: `harness replay <name> --trace` documented as deferred ([PRD §9](../../prd.md#9-cli-surface-epic-mapping))

### Implementation tasks (build)

- [x] Production trace export hook (Haystack `track_stats` or OTel stub)
- [x] Helper to merge traces into `data/val.jsonl` / `data/train.jsonl`
- [x] Document ratchet workflow in user-docs

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E8-S03 / E8.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_trace_ratchet.py::test_e8_s03_ac1_production_trace_appends_jsonl` |
| AC-2 | `tests/integration/eval/test_journey_c.py::test_e8_s03_ac2_trace_to_compile_loop` |
| AC-3 | `tests/unit/eval/test_trace_ratchet.py::test_e8_s03_ac3_replay_deferred_documented` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/eval/test_trace_ratchet.py tests/integration/eval/test_journey_c.py -v` passes

### Definition of done

- [x] Journey C complete with production trace source
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-26)

- `eval/ratchet.py`: `ProductionTraceHook` wraps Haystack `Agent.run`; `haystack_track_stats` + in-memory `OTelTraceStub` (no `opentelemetry` dep); `merge_traces_into_datasets` appends `data/val.jsonl` / `data/train.jsonl`.
- Opt-in: `eval.trace_capture.enabled` or `ZAUMZEUG_TRACE_CAPTURE=1`. Export failures never fail the live request.
- Serve: `AgentPipelineWrapper` installs the hook when capture is enabled.
- Docs: [testing.md — Journey C](../../../user-docs/guides/testing.md#trace--test-case-journey-c); [cli.md — zaumzeug replay (deferred)](../../../user-docs/reference/cli.md#zaumzeug-replay-deferred).
- Tests: `tests/unit/eval/test_trace_ratchet.py`, `tests/integration/eval/test_journey_c.py`. Full suite 2026-08-26: **365 passed, 2 skipped**.

---
