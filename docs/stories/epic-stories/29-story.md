# E4-S04 — Haystack GEPA evaluator wrapper

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/29-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E4-S04 |
| **Status** | Done |
| **Epic** | [E4 — Compile and GEPA Pipeline](../04-epic.md) |
| **Phase** | 2 (shipped early; originally Phase 4+) |
| **Epic build order** | 4 of 8 |
| **Story sequence** | 29 of 63 (global build order) |
| **Source** | Extracted from [`04-epic.md`](../04-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2) · [Architecture](../../architecture.md) |

---

## E4-S04 — Haystack GEPA evaluator wrapper

| Field | Value |
|---|---|
| **Feature** | E4.4 |
| **Persona** | SDK maintainer |
| **Priority** | P1 (shipped; was Deferred Phase 4+) |
| **Status** | Done (2026-07-28) |
| **Prerequisites** | [E4-S02b](27.2-story.md) ✅ · Haystack runtime factory [E3-S00](12-story.md) ✅ |

### User story

As an **SDK maintainer**, I want a Haystack adapter for GEPA `optimize_anything`, so that we can optimize pipeline YAML and other native artifacts without a DSPy module path.

### References

- [PRD E4.4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §12 Pattern B](../../architecture/08-compile-and-optimization.md#pattern-b-optimize-anything-deferred-phase-4)
- [GEPA optimize_anything](https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/)

### Acceptance criteria

- [x] **AC-1** Evaluator wrapper supports `optimize_anything` pattern
- [x] **AC-2** Modes: `single-task`, `multi-task`, `generalization`
- [x] **AC-3** Integrates with Haystack agent execution for trace collection

### Implementation tasks (build)

- [x] Implement in `src/zaumzeug/compile/gepa_adapter.py` ([Architecture §11 #8](../../architecture/09-sdk-module-map.md#11-sdk-modules-to-build))
- [x] Document mode selection in compile config schema

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S04 / E4.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/compile/test_gepa_adapter.py::test_e4_s04_ac1_optimize_anything_pattern` (+ stub path) |
| AC-2 | `tests/unit/compile/test_gepa_adapter.py::test_e4_s04_ac2_modes_single_multi_generalization` · `::test_e4_s04_ac2_compile_schema_mode_selection` |
| AC-3 | `tests/unit/compile/test_gepa_adapter.py::test_e4_s04_ac3_haystack_agent_trace_collection` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/compile/test_gepa_adapter.py -v` passes (5 passed, 0 skipped)

### Definition of done

- [x] Documented as Pattern B alongside Pattern A in user-docs compile guide
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- `zaumzeug.compile.gepa_adapter` provides `HaystackGepaAdapter` + `optimize_haystack_artifact` (Pattern B). Prefer `gepa.optimize_anything` when installed; otherwise map modes onto `gepa.optimize` + adapter.
- `CompileConfig` accepts `optimizer: optimize_anything` with required `mode` + `seed_artifact` (and train/val rules per mode). Pattern A (`dspy.GEPA` + `module`) unchanged.
- `zaumzeug compile` remains Pattern A-only; Pattern B configs get an actionable CLI error pointing at `optimize_haystack_artifact`.
- User docs: [guides/compile.md](../../user-docs/guides/compile.md) documents both patterns and mode selection.
