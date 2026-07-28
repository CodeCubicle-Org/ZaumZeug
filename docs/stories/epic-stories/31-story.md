# E4-S06 — `--dry-run` on compile

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/31-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E4-S06 |
| **Status** | Done |
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
| **Status** | Done (2026-07-28) |
| **Prerequisites** | [E4-S02a](27.1-story.md#e4-s02a-compile-cli-and-phase-2-schema) ✅ · [E4-S01](26-story.md#e4-s01-dspy-module-loader) ✅ |

### User story

As a **harness developer**, I want `zaumzeug compile --dry-run`, so that I can validate module imports and model registry without running GEPA or LLM calls.

### References

- [PRD E4.6](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)


### Implementation resources

**Internal spec**

- Same validation path as [E4-S02a](27.1-story.md) without invoking GEPA or writing artifacts

### Acceptance criteria

- [x] **AC-1** Validates compile config and Phase 2 schema
- [x] **AC-2** Resolves module imports successfully
- [x] **AC-3** Prints resolved model registry (task/reflection LM)
- [x] **AC-4** No GEPA run; no LLM API calls
- [x] **AC-5** Exit 0 on success

### Implementation tasks (build)

- [x] Add `--dry-run` to compile CLI
- [x] Reuse module loader + config validation
- [x] Human-readable summary output

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S06 / E4.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac1_validates_phase2_schema` |
| AC-2 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac2_resolves_module_import` |
| AC-3 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac3_prints_model_registry` |
| AC-4 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac4_no_gepa_no_llm_calls` |
| AC-5 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac5_exit_zero_on_success` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/compile/test_compile_dry_run.py -v` passes (5 passed, 0 skipped)

### Definition of done

- [x] Documented alongside serve dry-run in CLI reference
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- `run_compile(..., dry_run=True)` reuses the E4-S02a path (harness/workflow load, `resolve_agent_compile`, module import, LM preflight) and skips `invoke_gepa` / artifact writes.
- CLI: `zaumzeug compile <harness> --dry-run` prints `format_compile_dry_run()` (module + task/reflection registry, `gepa: skipped`).
- Docs: [CLI reference — compile](../../user-docs/reference/cli.md#zaumzeug-compile), [guides/compile.md](../../user-docs/guides/compile.md).
- Verification: **5 passed, 0 skipped** (`test_compile_dry_run.py`).

---
