# E7-S01 — MCP tool configuration

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/50-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 |
| **Story ID** | E7-S01 |
| **Status** | Done (2026-08-14) |
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
- Follow-up: [E7-S06 — MCP from deploy](55-story.md)


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

- [x] **AC-1** `tools.mcp` in yaml wires Haystack `MCPToolset`
- [x] **AC-2** `zaumzeug mcp <name>` serves MCP at `{host}:{mcp_port}/mcp`
- [x] **AC-3** Doctor warns when MCP configured but `uv` missing (non-blocking where applicable)
- [x] **AC-4** MCP errors return consistent shape per Architecture MCP boundary patterns

### Implementation tasks (build)

- [x] Extend config schema for `tools.mcp` entries
- [x] Implement MCP server boot in `src/zaumzeug/serve/mcp.py`
- [x] Add `mcp` subcommand to `src/zaumzeug/cli.py`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S01 / E7.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/mcp/test_mcp_config.py::test_e7_s01_ac1_yaml_wires_mcp_toolset` |
| AC-1 (schema) | `tests/unit/config/test_schemas.py::test_e7_s01_mcp_schema_and_mcp_port` |
| AC-2 | `tests/integration/mcp/test_mcp_server.py::test_e7_s01_ac2_mcp_endpoint_serves` |
| AC-3 | `tests/unit/cli/test_doctor.py::test_e7_s01_ac3_mcp_without_uv_warns` *(extends E2-S04b)* |
| AC-4 | `tests/integration/mcp/test_mcp_server.py::test_e7_s01_ac4_error_shape_consistent` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/mcp/ -v -k e7_s01` passes
- [x] Full suite `pytest tests -q` (2026-08-14): 314 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate)

### Definition of done

- [x] Documented endpoint in CLI reference and user-docs
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-14)

- `McpServerConfig`: `name` + exactly one of `command` (stdio) or `url` (HTTP); optional `args`, `timeout_s` (default 30), `tool_names`, `env`. `HayhooksConfig.mcp_port` default **1417** (removed from `PHASE_GATED_FIELDS`). `tools.mcp` unblocked; `tools.custom` stayed gated until [E7-S02](51-story.md) (**Done** 2026-08-14). `CURRENT_SDK_PHASE` stays **1**.
- Runtime: `runtime/tools/mcp.py` builds Haystack `MCPToolset` (`eager_connect=False`, 30s timeouts) from `tools.mcp`; factory appends toolsets to builtins.
- Serve: `serve/mcp.py` (`prepare_mcp` / `run_mcp`) registers the entry pipeline with `skip_mcp=False`; Hayhooks `create_mcp_server` + `create_starlette_app`; bind `127.0.0.1` only. `zaumzeug serve` keeps `skip_mcp=True`. Malformed `POST /mcp` returns JSON-RPC 2.0 `{jsonrpc, error: {code, message, data}}` with `data.ok: false`.
- CLI: `zaumzeug mcp <harness> [--deploy] [--verbose] [--port N]`. Doctor `mcp_uv` warns (non-blocking) when stdio MCP is configured and `uv` is missing; HTTP-only MCP does not require `uv`.
- Production `--deploy` / `HARNESS_ROOT=deploy` closed by [E7-S06](55-story.md) (2026-08-21) — same MCP surface from `deploy/<name>/`.
- Compile follow-up (same session): DSPy loader drops stale `sys.modules` before import — [E4-S01](26-story.md).

---
