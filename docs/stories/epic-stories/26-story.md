# E4-S01 — DSPy module loader

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/26-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E4-S01 |
| **Epic** | [E4 — Compile and GEPA Pipeline](../04-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 4 of 8 |
| **Story sequence** | 26 of 63 (global build order) |
| **Source** | Extracted from [`04-epic.md`](../04-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2) · [Architecture](../../architecture.md) |

---

## E4-S01 — DSPy module loader

| Field | Value |
|---|---|
| **Feature** | E4.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S03](04-story.md#e2-s03-runtime-agent-resolution-rules) · [E3-S00](12-story.md#e3-s00-runtime-factory-haystack-agent-builder) |

### User story

As a **harness developer**, I want the compile path to load my DSPy module from the harness folder, so that GEPA can optimize offline without touching the runtime request path.

### References

- [PRD E4.1](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §2.1 — Compile vs runtime](../../architecture/01-overview-and-principles.md#21-golden-rules)
- [Architecture §3.3 — `modules/`](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)


### Implementation resources

**Libraries & docs**

- [DSPy modules](https://dspy.ai/learn/programming/modules/)
- [DSPy signatures](https://dspy.ai/learn/programming/signatures/)
- [Architecture §4.2 — DSPy compile-time only](../../architecture/03-technology-stack.md#42-library-boundaries-when-to-use-what)

**Code sketch**

```python
import importlib
mod = importlib.import_module("usr_harnesses.example.modules.researcher")
dspy_module = mod.ResearchModule()
```

### Acceptance criteria

- [ ] **AC-1** Loads `compile.module` from `agents/<name>/agent.yaml`
- [ ] **AC-2** Runs only on `zaumzeug compile` — never during serve/MCP/ACP
- [ ] **AC-3** Import errors surface with module path and file hint
- [ ] **AC-4** Validates module is a DSPy `Module` subclass

### Implementation tasks (build)

- [ ] Implement loader in `src/zaumzeug/compile/module_loader.py`
- [ ] Add harness folder to `sys.path` safely (no traversal)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S01 / E4.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/compile/test_module_loader.py::test_e4_s01_ac1_valid_module_loads` |
| AC-2 | `tests/unit/compile/test_module_loader.py::test_e4_s01_ac2_not_imported_on_serve_path` |
| AC-3 | `tests/unit/compile/test_module_loader.py::test_e4_s01_ac3_invalid_path_actionable_error` |
| AC-4 | `tests/unit/compile/test_module_loader.py::test_e4_s01_ac4_requires_dspy_module_subclass` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/compile/test_module_loader.py -v` passes

### Definition of done

- [ ] Serve path has zero DSPy imports ([PRD G2](../../prd.md#3-goals))
- [ ] Verification checklist complete; all ACs traced to tests

---
