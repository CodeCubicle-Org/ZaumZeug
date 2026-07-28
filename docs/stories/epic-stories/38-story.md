# E6-S05 — Trace → test case

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/38-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E6-S05 |
| **Status** | Done |
| **Epic** | [E6 — Evaluation and Quality (Optional)](../05-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 5 of 8 |
| **Story sequence** | 38 of 63 (global build order) |
| **Source** | Extracted from [`05-epic.md`](../05-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E6](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) · [Architecture](../../architecture.md) |

---

## E6-S05 — Trace → test case

| Field | Value |
|---|---|
| **Feature** | E6.5 |
| **Persona** | Harness developer |
| **Priority** | P2 |
| **Status** | Done (2026-07-28) |
| **Prerequisites** | [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command) ✅ |

### User story

As a **harness developer**, I want to score a production trace as a test case, so that I can turn failures into regression tests ([Journey C](../../prd.md#73-journey-c--improve-after-failure-phase-2)).

### References

- [PRD E6.5](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §5.5](../../architecture/04-data-flows.md#55-continuous-improvement-loop)


### Implementation resources

**Libraries & docs**

- [DeepEval — trace to test case](https://docs.confident-ai.com/docs/evaluation-datasets)
- [Architecture §5.5 — improvement loop](../../architecture/04-data-flows.md#55-continuous-improvement-loop)

### Acceptance criteria

- [x] **AC-1** Haystack trace export to JSONL under `data/traces/`
- [x] **AC-2** `zaumzeug eval --trace <path>` scores single trace
- [x] **AC-3** Trace format documented for append to valset

### Implementation tasks (build)

- [x] Implement trace export helper
- [x] Add `--trace` CLI flag to eval command

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E6-S05 / E6.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_trace.py::test_e6_s05_ac1_trace_export_jsonl` |
| AC-2 | `tests/unit/eval/test_trace.py::test_e6_s05_ac2_eval_trace_flag_scores` |
| AC-3 | **manual:** user-docs documents trace JSONL schema for valset append |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/eval/test_trace.py -v` passes (4 passed, 0 skipped)

### Definition of done

- [x] Journey C documented end-to-end in user-docs
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- `eval/trace.py`: `export_haystack_trace` → `data/traces/*.jsonl`; `load_trace_jsonl` / `append_trace_to_valset` / `trace_to_valset_row`.
- `run_eval(..., trace=…)` + CLI `--trace` score captured `actual_output` without re-running the agent.
- Docs: [testing.md — Trace → test case](../../../user-docs/guides/testing.md#trace--test-case-journey-c), [cli.md — zaumzeug eval](../../../user-docs/reference/cli.md#zaumzeug-eval).

---
