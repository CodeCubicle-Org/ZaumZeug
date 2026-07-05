# E4-S04 — Haystack GEPA evaluator wrapper *(deferred)*

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/29-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E4-S04 |
| **Epic** | [E4 — Compile and GEPA Pipeline](../04-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 4 of 8 |
| **Story sequence** | 29 of 63 (global build order) |
| **Source** | Extracted from [`04-epic.md`](../04-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2) · [Architecture](../../architecture.md) |

---

## E4-S04 — Haystack GEPA evaluator wrapper *(deferred)*

| Field | Value |
|---|---|
| **Feature** | E4.4 |
| **Persona** | SDK maintainer |
| **Priority** | Deferred (Phase 4+) |
| **Status** | Not in Phase 2 v1 — Pattern B (`optimize_anything`) |

### User story

As an **SDK maintainer**, I want a Haystack adapter for GEPA `optimize_anything`, so that we can optimize pipeline YAML and other native artifacts without a DSPy module path.

### References

- [PRD E4.4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §12 Pattern B](../../architecture/08-compile-and-optimization.md#pattern-b-optimize-anything-deferred-phase-4)
- [GEPA optimize_anything](https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/)

### When to implement

- [ ] **Phase 4+** — after RAG / pipeline exposure (E8.1) or when a concrete use case requires direct artifact optimization
- [ ] Phase 2 ships **Pattern A only** (`dspy.GEPA` → export); this story is optional until then

### Acceptance criteria (when shipped)

- [ ] **AC-1** Evaluator wrapper supports `optimize_anything` pattern
- [ ] **AC-2** Modes: `single-task`, `multi-task`, `generalization`
- [ ] **AC-3** Integrates with Haystack agent execution for trace collection

### Implementation tasks (when unblocked)

- [ ] Implement in `src/zaumzeug/compile/gepa_adapter.py` ([Architecture §11 #8](../../architecture/09-sdk-module-map.md#11-sdk-modules-to-build))
- [ ] Document mode selection in compile config schema

### Verification (when unblocked)

Apply [Story verification](../00-README.md#story-verification-required). `tests/unit/compile/test_gepa_adapter.py` with AC-1–AC-3 mapping.

### Definition of done

- [ ] Documented as Pattern B alongside Pattern A in user-docs compile guide

---
