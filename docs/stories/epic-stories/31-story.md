# E4-S06 — `--dry-run` on compile

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/31-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E4-S06 |
| **Epic** | [E4 — Compile and GEPA Pipeline](../04-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 4 of 8 |
| **Story sequence** | 31 of 63 (global build order) |
| **Source** | Extracted from [`04-epic.md`](../04-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2) · [Architecture](../../architecture.md) |

---

## E4-S06 — `--dry-run` on compile

| Field | Value |
|---|---|
| **Feature** | E4.6 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E4-S02a](27.1-story.md#e4-s02a-compile-cli-and-phase-2-schema) · [E4-S01](26-story.md#e4-s01-dspy-module-loader) |

### User story

As a **harness developer**, I want `zaumzeug compile --dry-run`, so that I can validate module imports and model registry without running GEPA or LLM calls.

### References

- [PRD E4.6](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)


### Implementation resources

**Internal spec**

- Same validation path as [E4-S02a](27.1-story.md) without invoking GEPA or writing artifacts

### Acceptance criteria

- [ ] **AC-1** Validates compile config and Phase 2 schema
- [ ] **AC-2** Resolves module imports successfully
- [ ] **AC-3** Prints resolved model registry (task/reflection LM)
- [ ] **AC-4** No GEPA run; no LLM API calls
- [ ] **AC-5** Exit 0 on success

### Implementation tasks (build)

- [ ] Add `--dry-run` to compile CLI
- [ ] Reuse module loader + config validation
- [ ] Human-readable summary output

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S06 / E4.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac1_validates_phase2_schema` |
| AC-2 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac2_resolves_module_import` |
| AC-3 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac3_prints_model_registry` |
| AC-4 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac4_no_gepa_no_llm_calls` |
| AC-5 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac5_exit_zero_on_success` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/compile/test_compile_dry_run.py -v` passes

### Definition of done

- [ ] Documented alongside serve dry-run in CLI reference
- [ ] Verification checklist complete; all ACs traced to tests

---
