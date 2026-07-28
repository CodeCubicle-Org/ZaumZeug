# E4-S05 — Post-compile serve uses artifact

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/30-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E4-S05 |
| **Epic** | [E4 — Compile and GEPA Pipeline](../04-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 4 of 8 |
| **Story sequence** | 30 of 63 (global build order) |
| **Source** | Extracted from [`04-epic.md`](../04-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2) · [Architecture](../../architecture.md) |

---

## E4-S05 — Post-compile serve uses artifact

| Field | Value |
|---|---|
| **Feature** | E4.5 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest) ✅ (2026-07-28) · [E4-S03b](28.2-story.md#e4-s03b-runtime-input_rewrite-preprocess) ✅ (2026-07-28) · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) ✅ |

### User story

As a **harness developer**, I want serve to prefer compiled artifacts over hand-edited prompts, so that what I ship matches what GEPA optimized.

### References

- [PRD E4.5](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §5.2](../../architecture/04-data-flows.md#52-runtime-agent-resolution)


### Implementation resources

**Internal spec**

- [Architecture §5.2 — artifact > system_prompt priority](../../architecture/04-data-flows.md#52-runtime-agent-resolution)
- [E4-S03b preprocess](28.2-story.md) — no `import dspy` on serve path

### Acceptance criteria

- [ ] **AC-1** After compile, `zaumzeug serve` uses artifact path
- [ ] **AC-2** Ignores `compile.module` at serve/run time
- [ ] **AC-3** Ignores hand-edited `system_prompt` when valid artifact present
- [ ] **AC-4** When artifact includes optional `input_rewrite`, applies preprocess before agent loop (E4-S03b) — no GEPA at runtime
- [ ] **AC-5** Doctor warns if artifact stale vs module hash (optional warn)

### Implementation tasks (build)

- [ ] Ensure runtime factory honors resolver priority
- [ ] If `artifact-manifest.json` lists `input_rewrite`, run preprocess step then pass result to agent

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S05 / E4.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/compile/test_compile_serve.py::test_e4_s05_ac1_serve_uses_artifact_after_compile` |
| AC-2 | `tests/integration/compile/test_compile_serve.py::test_e4_s05_ac2_no_module_import_at_serve` |
| AC-3 | `tests/integration/compile/test_compile_serve.py::test_e4_s05_ac3_artifact_over_hand_edited_prompt` |
| AC-4 | `tests/integration/compile/test_compile_serve.py::test_e4_s05_ac4_input_rewrite_preprocess_no_dspy` |
| AC-5 | `tests/integration/test_doctor.py::test_e4_s05_ac5_stale_artifact_warn` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/compile/test_compile_serve.py -v` passes

### Definition of done

- [ ] Compile → serve happy path documented in user-docs
- [ ] Verification checklist complete; all ACs traced to tests

---
