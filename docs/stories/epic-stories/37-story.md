# E6-S04 — `eval/` pytest scaffold

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/37-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E6-S04 |
| **Status** | Done |
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
| **Status** | Done (2026-07-28) |
| **Prerequisites** | [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command) ✅ · [E6-S01](34-story.md#e6-s01-optional-eval-extra) ✅ |

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

- [x] **AC-1** Optional `usr-harnesses/<name>/eval/test_*.py` runs via `deepeval test run`
- [x] **AC-2** Custom metrics in `eval/metrics.py` importable
- [x] **AC-3** `eval/` excluded from deploy bundle (E5-S02)

### Implementation tasks (build)

- [x] Add eval template in zaumzeug init (optional flag)
- [x] Document `deepeval test run` workflow in user-docs

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E6-S04 / E6.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/eval/test_deepeval_scaffold.py::test_e6_s04_ac1_deepeval_test_run` *(requires [eval] extra)* |
| AC-2 | `tests/integration/eval/test_deepeval_scaffold.py::test_e6_s04_ac2_custom_metrics_importable` |
| AC-3 | **shared:** `tests/unit/deploy/test_copy_rules.py::test_e5_s02_excludes_eval` *(E5-S02)* |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/eval/test_deepeval_scaffold.py tests/unit/deploy/test_copy_rules.py tests/unit/cli/test_init_eval.py -v` passes (9 passed with eval extra; AC-1/AC-2 skip via `importorskip` without it)

### Definition of done

- [x] Example metric file in example harness (optional, dev-only)
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- `zaumzeug init --with-eval` copies `install/templates/harness/eval/` (`metrics.py` + `test_smoke.py`); default init omits `eval/`.
- Example harness ships `usr-harnesses/example/eval/` with `ContainsSubstringMetric` (no LLM judge) + `test_researcher.py`.
- Deploy exclusion policy in `deploy/copy_rules.py` (`is_excluded_from_deploy`); shared test for E5-S02 AC matrix.
- Docs: [testing.md](../../../user-docs/guides/testing.md#deepeval-pytest-scaffold), [cli.md](../../../user-docs/reference/cli.md#zaumzeug-init).

---
