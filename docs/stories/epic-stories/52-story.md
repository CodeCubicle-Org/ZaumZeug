# E7-S03 — Cursor MCP setup

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/52-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 |
| **Story ID** | E7-S03 |
| **Status** | Done (2026-08-21) |
| **Epic** | [E7 — Tools, MCP, and ACP](../07-epic.md) |
| **Phase** | 3 |
| **Epic build order** | 7 of 8 |
| **Story sequence** | 52 of 63 (global build order) |
| **Source** | Extracted from [`07-epic.md`](../07-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E7](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3) · [Architecture](../../architecture.md) |

---

## E7-S03 — Cursor MCP setup

| Field | Value |
|---|---|
| **Feature** | E7.3 |
| **Persona** | Client integrator |
| **Priority** | P1 |
| **Prerequisites** | [E1-S03](20-story.md#e1-s03-project-scaffolding-on-install) · [E7-S01](50-story.md#e7-s01-mcp-tool-configuration) · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) |

### User story

As a **Cursor user**, I want documented MCP setup, so that Cursor can invoke my harness as tools.

### References

- [PRD E7.3](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9.2 — MCP when to use](../../architecture/06-runtime-and-protocols.md#92-mcp-when-to-use)
- [E1-S03 — `.cursor/mcp.json.example`](../03-epic.md#e1-s03-project-scaffolding-on-install)


### Implementation resources

**Libraries & docs**

- [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol)
- [MCP JSON config](https://modelcontextprotocol.io/quickstart/user) (`.cursor/mcp.json`)
- Scaffold template from [E1-S03](20-story.md)

### Acceptance criteria

- [x] **AC-1** Documented `mcp.json` → `http://localhost:{mcp_port}/mcp`
- [x] **AC-2** Install scaffolds `.cursor/mcp.json.example`
- [x] **AC-3** `--cursor-mcp` install flag may write live `.cursor/mcp.json` (opt-in)
- [x] **AC-4** Requires `uv` when harness uses MCP tool servers — documented

### Implementation tasks (build)

- [x] Author Cursor setup guide in `user-docs/guides/cursor-mcp.md`
- [x] Template `mcp.json.example` with placeholder port
- [x] Wire `--cursor-mcp` in client_install (E1-S01)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **Docs + scaffold** — manual E2E checklist. Test file header: `# Story: E7-S03 / E7.3`.

| AC | Verification |
|---|---|
| AC-1 | **manual:** guide shows correct URL pattern — [cursor-mcp.md](../../../user-docs/guides/cursor-mcp.md) documents `http://localhost:{mcp_port}/mcp` (default **1417**) |
| AC-2 | `tests/unit/install/test_scaffolding.py::test_e7_s03_ac2_mcp_json_example_scaffolded` |
| AC-3 | `tests/unit/install/test_client_install.py::test_e7_s03_ac3_cursor_mcp_flag_writes_json` |
| AC-4 | **manual:** guide documents `uv` requirement for stdio `tools.mcp` (HTTP Cursor → `zaumzeug mcp` does not need `uv`) |
| AC-1–4 | **manual:** end-to-end checklist in `cursor-mcp.md` completed once |

- [x] Manual E2E checklist completed; automated ACs pass
- [x] `pytest tests/unit/install/test_scaffolding.py::test_e7_s03_ac2_mcp_json_example_scaffolded tests/unit/install/test_client_install.py::test_e7_s03_ac3_cursor_mcp_flag_writes_json -v` passes
- [x] Full suite `pytest tests -q` (2026-08-21): 322 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate)

### Definition of done

- [x] End-to-end manual test checklist in guide
- [x] Verification checklist complete

### Implementation notes (2026-08-21)

- Guide: [cursor-mcp.md](../../../user-docs/guides/cursor-mcp.md) (mirrored in `install/templates/user-docs/guides/`). URL is `http://localhost:{mcp_port}/mcp`; template placeholder port **1417**.
- `scaffold_project(..., cursor_mcp=True)` copy-if-missing writes live `.cursor/mcp.json` from the example (never overwrite). Flag off still scaffolds `.cursor/mcp.json.example` only.
- `uv` is required only for stdio `tools.mcp` servers (`zaumzeug doctor` `mcp_uv` warn). Cursor talking to `zaumzeug mcp` over HTTP does not need `uv`.

---
