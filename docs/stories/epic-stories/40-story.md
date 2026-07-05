# E6-S07 — GEPA ↔ DeepEval bridge

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/40-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E6-S07 |
| **Epic** | [E6 — Evaluation and Quality (Optional)](../05-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 5 of 8 |
| **Story sequence** | 40 of 63 (global build order) |
| **Source** | Extracted from [`05-epic.md`](../05-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E6](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) · [Architecture](../../architecture.md) |

---

## E6-S07 — GEPA ↔ DeepEval bridge

| Field | Value |
|---|---|
| **Feature** | E6.7 |
| **Persona** | Harness developer |
| **Priority** | P2 |
| **Prerequisites** | [E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts) · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command) |

### User story

As a **harness developer**, I want failed eval rows to feed compile training data, so that GEPA and DeepEval share one improvement loop.

### References

- [PRD E6.7](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §6.3 — GEPA ↔ DeepEval bridge](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)


### Implementation resources

**Internal spec**

- [Architecture §6.3 — GEPA ↔ DeepEval bridge](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)
- Reuse GEPA textual feedback format from [E4-S02b](27.2-story.md)

### Acceptance criteria

- [ ] **AC-1** Failed eval rows can append to `data/train.jsonl`
- [ ] **AC-2** Shared `data/val.jsonl` for compile and eval
- [ ] **AC-3** GEPA custom metric may delegate to DeepEval `.measure()` optionally
- [ ] **AC-4** Story seed: GEPA metric delegates to DeepEval optionally

### Implementation tasks (build)

- [ ] Document JSONL schemas for train/val
- [ ] Helper to append failed rows from eval report
- [ ] Example in `modules/metrics.py` template

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E6-S07 / E6.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_gepa_bridge.py::test_e6_s07_ac1_failed_rows_append_train_jsonl` |
| AC-2 | `tests/unit/eval/test_gepa_bridge.py::test_e6_s07_ac2_shared_val_jsonl` |
| AC-3 | `tests/unit/eval/test_gepa_bridge.py::test_e6_s07_ac3_gepa_metric_delegates_deepeval` |
| AC-4 | `tests/unit/eval/test_gepa_bridge.py::test_e6_s07_ac4_optional_deepeval_measure` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/eval/test_gepa_bridge.py -v` passes

### Definition of done

- [ ] Compile → eval → compile loop documented ([Journey C](../../prd.md#73-journey-c--improve-after-failure-phase-2))
- [ ] Verification checklist complete; all ACs traced to tests
