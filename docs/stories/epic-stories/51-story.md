# E7-S02 — Custom tool loader

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/51-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E7-S02 |
| **Epic** | [E7 — Tools, MCP, and ACP](../07-epic.md) |
| **Phase** | 3 |
| **Epic build order** | 7 of 8 |
| **Story sequence** | 51 of 63 (global build order) |
| **Source** | Extracted from [`07-epic.md`](../07-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E7](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3) · [Architecture](../../architecture.md) |

---

## E7-S02 — Custom tool loader

| Field | Value |
|---|---|
| **Feature** | E7.2 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E3-S03](11-story.md#e3-s03-builtin-tool-web_fetch) |

### User story

As a **harness developer**, I want Python tools under `tools/` loaded from config, so that I can extend agents beyond builtins.

### References

- [PRD E7.2](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §3.3 — `tools/`](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)


### Implementation resources

**Libraries & docs**

- [Haystack custom components / tools](https://docs.haystack.deepset.ai/docs/custom-components)
- [Architecture §3.3 — `agents/<name>/tools/`](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)

**Tool sketch**

```python
from haystack.tools import Tool

def search_docs(query: str) -> str: ...

search_tool = Tool(name="search_docs", function=search_docs, description="...")
```

### Acceptance criteria

- [ ] **AC-1** `tools.custom` imports modules from harness folder
- [ ] **AC-2** Tools registered as Haystack `ComponentTool` (or equivalent)
- [ ] **AC-3** Import errors fail at doctor/ serve with module path
- [ ] **AC-4** Custom tools copied to deploy when listed in yaml (E5-S02)

### Implementation tasks (build)

- [ ] Implement loader in `src/zaumzeug/runtime/tools/custom.py`
- [ ] Validate tool registration at startup
- [ ] Example custom tool in user-docs guide

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S02 / E7.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/tools/test_custom_loader.py::test_e7_s02_ac1_imports_custom_modules` |
| AC-2 | `tests/unit/runtime/tools/test_custom_loader.py::test_e7_s02_ac2_registers_component_tool` |
| AC-3 | `tests/integration/test_doctor.py::test_e7_s02_ac3_import_error_at_doctor` |
| AC-4 | **shared:** `tests/unit/deploy/test_copy_rules.py::test_e7_s02_ac4_custom_tools_in_deploy` *(E5-S02)* |
| AC-2 | **optional:** ToolCorrectnessMetric in example harness `eval/` when DeepEval present |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/runtime/tools/test_custom_loader.py -v` passes

### Definition of done

- [ ] Deploy bundle includes referenced `tools/*.py` only
- [ ] Verification checklist complete; all ACs traced to tests

---
