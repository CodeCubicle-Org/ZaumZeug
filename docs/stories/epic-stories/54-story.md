# E7-S05 — ACP adapter

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/54-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E7-S05 |
| **Epic** | [E7 — Tools, MCP, and ACP](../07-epic.md) |
| **Phase** | 3 |
| **Epic build order** | 7 of 8 |
| **Story sequence** | 54 of 63 (global build order) |
| **Source** | Extracted from [`07-epic.md`](../07-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E7](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3) · [Architecture](../../architecture.md) |

---

## E7-S05 — ACP adapter

| Field | Value |
|---|---|
| **Feature** | E7.5 |
| **Persona** | Client integrator |
| **Priority** | P1 |
| **Prerequisites** | [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) |

### User story

As a **Zed/JetBrains user**, I want `zaumzeug acp`, so that my IDE can drive the harness as the primary agent via stdio.

### References

- [PRD E7.5](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9.1 — ACP row](../../architecture/06-runtime-and-protocols.md#91-protocol-selection)
- [Architecture §9.3 — ACP when to use](../../architecture/06-runtime-and-protocols.md#93-acp-when-to-use)


### Implementation resources

**Libraries & docs**

- [Agent Client Protocol](https://agentclientprotocol.com/)
- [Architecture §9.3 — ACP when to use](../../architecture/06-runtime-and-protocols.md#93-acp-when-to-use)

### Acceptance criteria

- [ ] **AC-1** `zaumzeug acp <name>` starts stdio JSON-RPC process
- [ ] **AC-2** Zed/JetBrains can register command in agent settings
- [ ] **AC-3** ACP naming clarified: Agent Client Protocol ≠ IBM ACP/A2A
- [ ] **AC-4** Harness may still use MCP internally for its own tools

### Implementation tasks (build)

- [ ] Implement ACP adapter in `src/zaumzeug/serve/acp.py`
- [ ] Document registration snippets for Zed and JetBrains

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S05 / E7.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/acp/test_acp_stdio.py::test_e7_s05_ac1_starts_stdio_jsonrpc` |
| AC-2 | **manual:** docs include Zed/JetBrains registration snippets |
| AC-3 | **manual:** docs disambiguate ACP vs A2A |
| AC-4 | `tests/integration/acp/test_acp_stdio.py::test_e7_s05_ac4_internal_mcp_still_works` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/acp/test_acp_stdio.py -v` passes

### Definition of done

- [ ] Document Cursor limitation (MCP primary, not generic ACP client)
- [ ] Verification checklist complete; all ACs traced to tests

---
