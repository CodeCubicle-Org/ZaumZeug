# E7-S07 — Extended builtin tools catalog

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/56-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 |
| **Story ID** | E7-S07 |
| **Status** | Done (2026-08-21) |
| **Epic** | [E7 — Tools, MCP, and ACP](../07-epic.md) |
| **Phase** | 3 |
| **Epic build order** | 7 of 8 |
| **Story sequence** | 56 of 63 (global build order) |
| **Source** | Extracted from [`07-epic.md`](../07-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E7](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3) · [Architecture](../../architecture.md) |

---

## E7-S07 — Extended builtin tools catalog

| Field | Value |
|---|---|
| **Feature** | E7.7 |
| **Persona** | Harness developer |
| **Priority** | P2 |
| **Prerequisites** | [E3-S03](11-story.md#e3-s03-builtin-tool-web_fetch) · [E7-S01](50-story.md#e7-s01-mcp-tool-configuration) |
| **Status** | Done (2026-08-21) |

### User story

As a **harness developer**, I want additional builtin tools beyond `web_fetch`, so that common agent tasks need no custom Python.

### References

- [PRD E7.7](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §6.5](../../architecture/05-configuration.md#65-builtin-tools-catalog)


### Implementation resources

**Internal spec**

- [Architecture §6.5 — extended builtins catalog](../../architecture/05-configuration.md#65-builtin-tools-catalog)
- Extend [E3-S03 web_fetch](11-story.md) catalog registration pattern

### Acceptance criteria

- [x] **AC-1** Phase 3 ships `calculator`, `read_file` per catalog
- [x] **AC-2** `read_file` sandboxed to harness workspace paths
- [x] **AC-3** Unknown builtin ID fails with phase-appropriate available list
- [x] **AC-4** `search_docs` remains Phase 4 (E8)

### Implementation tasks (build)

- [x] Implement `calculator` and `read_file` in runtime tools package
- [x] Extend phase gate in config validation

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S07 / E7.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/tools/test_extended_builtins.py::test_e7_s07_ac1_calculator_and_read_file_in_catalog` |
| AC-2 | `tests/unit/runtime/tools/test_read_file.py::test_e7_s07_ac2_sandbox_blocks_outside_workspace` |
| AC-3 | `tests/unit/config/test_schemas.py::test_e7_s07_ac3_unknown_builtin_phase3_list` |
| AC-4 | `tests/unit/runtime/tools/test_extended_builtins.py::test_e7_s07_ac4_search_docs_not_phase3` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/runtime/tools/test_extended_builtins.py tests/unit/runtime/tools/test_read_file.py -v` passes
- [x] Full suite `pytest tests -q` (2026-08-21): 339 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate)

### Definition of done

- [x] Catalog table in Architecture §6.5 matches implementation
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-21)

- `calculator` (`runtime/tools/calculator.py`) evaluates arithmetic with a restricted AST (`+ - * / // % **` and parentheses; no names or calls). Haystack `@component` + `ComponentTool`.
- `read_file` (`runtime/tools/read_file.py`) reads UTF-8 text under the harness folder. Paths `resolve()` then `relative_to(workspace)`; traversal and absolute paths outside the workspace are blocked. Factory passes `workspace=harness_dir`.
- Catalog factories in `runtime/tools/catalog.py`. `BUILTIN_CATALOG_PHASE` was **3** at E7-S07 ship so Phase 3 ids landed without bumping `CURRENT_SDK_PHASE` (stays **1**). Follow-up: [E8-S01](58-story.md) shipped `search_docs` and raised the catalog phase to **4**.
- Unknown builtin ids fail with `available for Phase 3: ['calculator', 'read_file', 'web_fetch']`.
- Tests: `tests/unit/runtime/tools/test_extended_builtins.py`, `tests/unit/runtime/tools/test_read_file.py`, `tests/unit/config/test_schemas.py::test_e7_s07_ac3_unknown_builtin_phase3_list`.

---
