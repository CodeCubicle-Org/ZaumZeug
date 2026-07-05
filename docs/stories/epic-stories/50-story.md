# E7-S01 — MCP tool configuration

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/50-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E7-S01 |
| **Epic** | [E7 — Tools, MCP, and ACP](../07-epic.md) |
| **Phase** | 3 |
| **Epic build order** | 7 of 8 |
| **Story sequence** | 50 of 63 (global build order) |
| **Source** | Extracted from [`07-epic.md`](../07-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E7](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3) · [Architecture](../../architecture.md) |

---

## E7-S01 — MCP tool configuration

| Field | Value |
|---|---|
| **Feature** | E7.1 |
| **Persona** | Harness developer · Client integrator |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E2-S04b](05.2-story.md#e2-s04b-zaumzeug-doctor-phase-aware-warnings) |

### User story

As a **harness developer**, I want MCP tools declared in yaml, so that my agent can call external MCP servers without custom wiring code.

### References

- [PRD E7.1](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9](../../architecture/06-runtime-and-protocols.md#9-client-access-and-protocols)
- [Architecture §6.2 — `tools.mcp`](../../architecture/05-configuration.md#62-config-sections)


### Implementation resources

**Libraries & docs**

- [Model Context Protocol](https://modelcontextprotocol.io/introduction)
- [Haystack MCPToolset](https://docs.haystack.deepset.ai/docs/mcp)
- [uv — MCP server launcher](https://docs.astral.sh/uv/)
- [Architecture §9.2 — MCP when to use](../../architecture/06-runtime-and-protocols.md#92-mcp-when-to-use)

**Config sketch**

```yaml
tools:
  mcp:
    - name: filesystem
      command: uv
      args: ["run", "mcp-server-filesystem", "/workspace"]
```

### Acceptance criteria

- [ ] **AC-1** `tools.mcp` in yaml wires Haystack `MCPToolset`
- [ ] **AC-2** `zaumzeug mcp <name>` serves MCP at `{host}:{mcp_port}/mcp`
- [ ] **AC-3** Doctor warns when MCP configured but `uv` missing (non-blocking where applicable)
- [ ] **AC-4** MCP errors return consistent shape per Architecture MCP boundary patterns

### Implementation tasks (build)

- [ ] Extend config schema for `tools.mcp` entries
- [ ] Implement MCP server boot in `src/zaumzeug/serve/mcp.py`
- [ ] Add `mcp` subcommand to `src/zaumzeug/cli.py`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S01 / E7.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/mcp/test_mcp_config.py::test_e7_s01_ac1_yaml_wires_mcp_toolset` |
| AC-2 | `tests/integration/mcp/test_mcp_server.py::test_e7_s01_ac2_mcp_endpoint_serves` |
| AC-3 | `tests/unit/cli/test_doctor.py::test_e7_s01_ac3_mcp_without_uv_warns` *(extends E2-S04b)* |
| AC-4 | `tests/integration/mcp/test_mcp_server.py::test_e7_s01_ac4_error_shape_consistent` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/mcp/ -v -k e7_s01` passes

### Definition of done

- [ ] Documented endpoint in CLI reference and user-docs
- [ ] Verification checklist complete; all ACs traced to tests

---
