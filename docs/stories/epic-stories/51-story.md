# E7-S02 — Custom tool loader

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/51-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-14 |
| **Story ID** | E7-S02 |
| **Status** | Done (2026-08-14) |
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

- [x] **AC-1** `tools.custom` imports modules from harness folder
- [x] **AC-2** Tools registered as Haystack `ComponentTool` (or equivalent)
- [x] **AC-3** Import errors fail at doctor/ serve with module path
- [x] **AC-4** Custom tools copied to deploy when listed in yaml *(packager row **Done** early with [E5-S02](42-story.md), 2026-07-28; loader remains this story)*

### Implementation tasks (build)

- [x] Implement loader in `src/zaumzeug/runtime/tools/custom.py`
- [x] Validate tool registration at startup
- [x] Example custom tool in user-docs guide

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S02 / E7.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/tools/test_custom_loader.py::test_e7_s02_ac1_imports_custom_modules` |
| AC-2 | `tests/unit/runtime/tools/test_custom_loader.py::test_e7_s02_ac2_registers_component_tool` |
| AC-3 | `tests/integration/test_doctor.py::test_e7_s02_ac3_import_error_at_doctor` |
| AC-4 | **shared early:** `tests/unit/deploy/test_copy_rules.py::test_e7_s02_ac4_custom_tools_in_deploy` *(packager copy landed with [E5-S02](42-story.md), 2026-07-28)* |
| AC-2 | **optional:** ToolCorrectnessMetric in example harness `eval/` when DeepEval present — **not added** (example eval stays the E6-S04 substring metric; guide covers registration) |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/runtime/tools/test_custom_loader.py -v` passes
- [x] Full suite `pytest tests -q` (2026-08-14): 320 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate)

### Definition of done

- [x] Deploy bundle includes referenced `tools/*.py` only
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-14)

- `AgentToolsConfig.custom` unblocked (non-empty string list). `CURRENT_SDK_PHASE` stays **1**. Doctor `phase_gated_tools` is a no-op pass; `custom_tools` imports listed modules in default and `--deploy` modes.
- Loader `runtime/tools/custom.py`: path (`tools/search_docs.py`), dotted (`tools.search_docs`), or `module:attr`. Prepends `agents/<name>/`, drops stale `sys.modules` chain, rejects traversal. Registers Haystack `Tool` / `ComponentTool` / `@component` (class instantiated then wrapped) / typed functions via `create_tool_from_function`.
- Factory `build_agent_tools(..., agent_dir=)` appends custom tools after builtins and MCP. Import errors raise `RuntimeFactoryError` with the module path (same text as doctor).
- Packager/copy-rules resolve dotted names to `tools/<name>.py` so deploy still copies only listed files (AC-4 unchanged).
- User guide: [custom-tools.md](../../user-docs/guides/custom-tools.md).

---
