# E2-S03 — Runtime agent resolution rules

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/04-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-20 |
| **Status** | Done |
| **Epic** | [E2 — Configuration and Validation](../01-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 1 of 8 |
| **Story sequence** | 4 of 63 (global build order) |
| **Source** | Extracted from [`01-epic.md`](../01-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E2](../../prd.md#epic-e2--configuration-and-validation-phase-1) · [Architecture](../../architecture.md) |

---

## E2-S03 — Runtime agent resolution rules

| Field | Value |
|---|---|
| **Feature** | E2.3 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E2-S02](03-story.md#e2-s02-modelsyaml-merge) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want runtime agent resolution enforced by mode, so that compile/runtime separation is enforced.

### References

- [PRD E2.3](../../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §5.2](../../architecture/04-data-flows.md#52-runtime-agent-resolution)
- [Architecture §2.1 — Golden rules](../../architecture/01-overview-and-principles.md#21-golden-rules)
- [PRD G2](../../prd.md#3-goals)


### Implementation resources

**Internal spec**

- [Architecture §5.2 — runtime vs compile resolution](../../architecture/04-data-flows.md#52-runtime-agent-resolution)
- [Architecture §2.1 — golden rules (no DSPy on serve)](../../architecture/01-overview-and-principles.md#21-golden-rules)

**Code**

- `src/zaumzeug/config/resolver.py` — `resolve_agent_serve()`, `resolve_agent_compile()`, `resolve_serve_entry()`
- Exported from `zaumzeug.config` for doctor, serve, and compile stories

### Acceptance criteria

- [x] **AC-1** **Serve/run (per agent):** loads `artifact` > `system_prompt` > actionable error
- [x] **AC-2** **Compile (per agent):** requires `compile.module` in `agents/<name>/agent.yaml` (Phase 2+)
- [x] **AC-3** **Serve entry:** uses workflow `entry` agent for interactive `zaumzeug serve`
- [x] **AC-4** Error messages name missing path and suggest fix

### Implementation tasks (build)

- [x] Implement resolver in `src/zaumzeug/config/resolver.py`
- [x] Validate artifact has `artifact-manifest.json` when artifact path set

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S03 / E2.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_resolver.py::test_e2_s03_ac1_serve_artifact_over_system_prompt` |
| AC-1 | `tests/unit/config/test_resolver.py::test_e2_s03_ac1_serve_system_prompt_fallback` |
| AC-1 | `tests/unit/config/test_resolver.py::test_e2_s03_ac1_serve_both_missing_actionable_error` |
| AC-2 | `tests/unit/config/test_resolver.py::test_e2_s03_ac2_compile_requires_module` |
| AC-3 | `tests/unit/config/test_resolver.py::test_e2_s03_ac3_serve_entry_from_workflow` |
| AC-4 | `tests/unit/config/test_resolver.py::test_e2_s03_ac4_error_names_path_and_suggests_fix` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/config/test_resolver.py -v` passes

### Definition of done

- [x] Doctor uses same resolution logic via `resolve_agent_serve()` ([E2-S04a](05.1-story.md), 2026-07-08)
- [x] Serve uses same resolution logic via `resolve_agent_serve()` in `runtime/factory.build_agent()` ([E3-S00](12-story.md), 2026-07-20) and `serve/runner.py` ([E3-S02](13-story.md), 2026-07-20)
- [x] No DSPy import on serve path
- [x] Verification checklist complete; all ACs traced to tests

---
