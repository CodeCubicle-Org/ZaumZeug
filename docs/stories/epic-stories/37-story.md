# E6-S04 — `eval/` pytest scaffold

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/37-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E6-S04 |
| **Epic** | [E6 — Evaluation and Quality (Optional)](../05-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 5 of 8 |
| **Story sequence** | 37 of 63 (global build order) |
| **Source** | Extracted from [`05-epic.md`](../05-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E6](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) · [Architecture](../../architecture.md) |

---

## E6-S04 — `eval/` pytest scaffold

| Field | Value |
|---|---|
| **Feature** | E6.4 |
| **Persona** | Harness developer |
| **Priority** | P2 |
| **Prerequisites** | [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command) · [E6-S01](34-story.md#e6-s01-optional-eval-extra) ✅ |

### User story

As a **harness developer**, I want optional pytest files under `eval/`, so that I can run DeepEval tests with familiar tooling.

### References

- [PRD E6.4](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §3.3 — `eval/`](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)


### Implementation resources

**Libraries & docs**

- [DeepEval pytest integration](https://docs.confident-ai.com/docs/testing-pytest)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html) for optional `[eval]` jobs

### Acceptance criteria

- [ ] **AC-1** Optional `usr-harnesses/<name>/eval/test_*.py` runs via `deepeval test run`
- [ ] **AC-2** Custom metrics in `eval/metrics.py` importable
- [ ] **AC-3** `eval/` excluded from deploy bundle (E5-S02)

### Implementation tasks (build)

- [ ] Add eval template in zaumzeug init (optional flag)
- [ ] Document `deepeval test run` workflow in user-docs

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E6-S04 / E6.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/eval/test_deepeval_scaffold.py::test_e6_s04_ac1_deepeval_test_run` *(requires [eval] extra in CI job)* |
| AC-2 | `tests/integration/eval/test_deepeval_scaffold.py::test_e6_s04_ac2_custom_metrics_importable` |
| AC-3 | **shared:** `tests/unit/deploy/test_copy_rules.py::test_e5_s02_excludes_eval` *(E5-S02)* |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/eval/test_deepeval_scaffold.py -v` passes (with eval extra)

### Definition of done

- [ ] Example metric file in example harness (optional, dev-only)
- [ ] Verification checklist complete; all ACs traced to tests

---
