# E7-S05 — ACP adapter

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/54-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 |
| **Story ID** | E7-S05 |
| **Status** | Done (2026-08-21) |
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

- [x] **AC-1** `zaumzeug acp <name>` starts stdio JSON-RPC process
- [x] **AC-2** Zed/JetBrains can register command in agent settings
- [x] **AC-3** ACP naming clarified: Agent Client Protocol ≠ IBM ACP/A2A
- [x] **AC-4** Harness may still use MCP internally for its own tools

### Implementation tasks (build)

- [x] Implement ACP adapter in `src/zaumzeug/serve/acp.py`
- [x] Document registration snippets for Zed and JetBrains

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S05 / E7.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/acp/test_acp_stdio.py::test_e7_s05_ac1_starts_stdio_jsonrpc` |
| AC-2 | **manual + automated:** Zed/JetBrains registration snippets — [acp.md](../../../user-docs/guides/acp.md) and [cli.md](../../../user-docs/reference/cli.md); `test_e7_s05_ac2_docs_include_zed_jetbrains_snippets` |
| AC-3 | **manual + automated:** docs disambiguate ACP vs A2A — `test_e7_s05_ac3_docs_disambiguate_acp_vs_a2a` |
| AC-4 | `tests/integration/acp/test_acp_stdio.py::test_e7_s05_ac4_internal_mcp_still_works` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/acp/test_acp_stdio.py -v` passes
- [x] Full suite `pytest tests -q` (2026-08-21): 332 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate)

### Definition of done

- [x] Document Cursor limitation (MCP primary, not generic ACP client)
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-21)

- `AcpConfig` (`serve.acp.enabled`) unblocked from `PHASE_GATED_FIELDS`. `CURRENT_SDK_PHASE` stays **1**.
- `serve/acp.py` (`prepare_acp` / `serve_stdio` / `run_acp`) builds the entry agent via the factory and serves Agent Client Protocol v1 JSON-RPC on newline-delimited stdio (`initialize`, `session/new`, `session/prompt`). Logs and banners go to stderr.
- Internal `tools.mcp` still becomes Haystack `MCPToolset` (deferred connect) on the ACP path.
- Guide: [acp.md](../../../user-docs/guides/acp.md) (Zed `agent_servers`, JetBrains `~/.jetbrains/acp.json`, ACP ≠ IBM A2A, Cursor uses MCP).
- CLI: `zaumzeug acp <harness> [--deploy] [--verbose]`.
- Full suite 2026-08-21: 332 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate).

---
