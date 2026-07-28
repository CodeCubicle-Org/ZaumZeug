# E6-S01 — Optional `[eval]` extra

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/34-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E6-S01 |
| **Status** | Done |
| **Epic** | [E6 — Evaluation and Quality (Optional)](../05-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 5 of 8 |
| **Story sequence** | 34 of 63 (global build order) |
| **Source** | Extracted from [`05-epic.md`](../05-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E6](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) · [Architecture](../../architecture.md) |

---

## E6-S01 — Optional `[eval]` extra

| Field | Value |
|---|---|
| **Feature** | E6.1 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Done (2026-07-28) |
| **Prerequisites** | [E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation) ✅ |

### User story

As a **harness developer**, I want DeepEval as an optional extra, so that core install stays lean for users who do not run eval.

### References

- [PRD E6.1](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §4.4](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)


### Implementation resources

**Libraries & docs**

- [DeepEval PyPI](https://pypi.org/project/deepeval/)
- [Architecture §4.4 — `[eval]` extra](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)

### Acceptance criteria

- [x] **AC-1** Core `zaumzeug` install has no `deepeval` dependency
- [x] **AC-2** `[eval]` extra installs `deepeval`
- [x] **AC-3** `pip install "zaumzeug[eval]"` documented in user-docs

### Implementation tasks (build)

- [x] Add `eval = ["deepeval"]` to `pyproject.toml` optional-dependencies *(already present from E2-S00; re-asserted)*
- [x] Guard imports in eval module with friendly error

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E6-S01 / E6.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_eval_extra.py::test_e6_s01_ac1_core_has_no_deepeval_dependency` |
| AC-2 | `tests/unit/eval/test_eval_extra.py::test_e6_s01_ac2_eval_extra_installs_deepeval` |
| AC-3 | `tests/unit/eval/test_eval_extra.py::test_e6_s01_ac3_user_docs_document_eval_extra` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/eval/test_eval_extra.py -v` passes (6 passed, 0 skipped)

### Definition of done

- [x] `zaumzeug doctor` does not require deepeval unless eval configured
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- `pyproject.toml` already declared `eval = ["deepeval"]` (E2-S00); core `dependencies` still exclude `deepeval`.
- `zaumzeug.eval.require_deepeval()` / `is_deepeval_available()` — package import stays lean; missing DeepEval raises Architecture §6.3 install hint.
- User-docs already document `pip install "zaumzeug[eval]"` in `getting-started/installation.md` (live + install template).
- Doctor checks/runner have no `deepeval` import; full `zaumzeug eval` landed in [E6-S02](35-story.md) ✅ (2026-07-28).

---
