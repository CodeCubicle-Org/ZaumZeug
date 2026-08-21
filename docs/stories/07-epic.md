# Epic E7 — Tools, MCP, and ACP

| | |
|---|---|
| **Document** | Epic E7 user stories |
| **File** | `docs/stories/07-epic.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 (E7-S06 Done) |
| **Status** | In progress (E7-S06 Done 2026-08-21) |
| **Build order** | **7 of 8** |
| **Related** | [PRD](../prd.md) · [Architecture](../architecture.md) · [Index](00-README.md) |

---
| Field | Value |
|---|---|
| **Phase** | 3 |
| **Epic** | E7 |
| **Outcome** | Full tool surface and IDE integrations |
| **Depends on** | [E5](06-epic.md) deploy serve path · Phase 1–2 complete |
| **Blocks** | — |
| **PRD** | [Epic E7](../prd.md#epic-e7--tools-mcp-and-acp-phase-3) |
| **Architecture** | [§9 Client access](../architecture/06-runtime-and-protocols.md#9-client-access-and-protocols) · [§11 #5, #11, #13](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build) |
| **Open decisions** | [#2 Web UI](../prd.md#12-open-decisions-blockers-for-some-stories) · [#5 MCP granularity](../prd.md#12-open-decisions-blockers-for-some-stories) |

### Story implementation order (within this epic)

1. **E7-S02** — Custom tools ✅
2. **E7-S07** — Extended builtins
3. **E7-S01** — MCP config + `zaumzeug mcp` ✅
4. **E7-S03** — Cursor setup ✅
5. **E7-S05** — ACP adapter ✅
6. **E7-S06** — MCP from deploy ✅
7. **E7-S04** → **E7-S08** — Chainlit ✅; remaining Open WebUI / SPA / Next.js recipes

---

## E7-S01 — MCP tool configuration

| Field | Value |
|---|---|
| **Feature** | E7.1 |
| **Persona** | Harness developer · Client integrator |
| **Priority** | P0 |

### User story

As a **harness developer**, I want MCP tools declared in yaml, so that my agent can call external MCP servers without custom wiring code.

### References

- [PRD E7.1](../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9](../architecture/06-runtime-and-protocols.md#9-client-access-and-protocols)
- [Architecture §6.2 — `tools.mcp`](../architecture/05-configuration.md#62-config-sections)

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

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E7-S01 / E7.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/mcp/test_mcp_config.py::test_e7_s01_ac1_yaml_wires_mcp_toolset` |
| AC-1 (schema) | `tests/unit/config/test_schemas.py::test_e7_s01_mcp_schema_and_mcp_port` |
| AC-2 | `tests/integration/mcp/test_mcp_server.py::test_e7_s01_ac2_mcp_endpoint_serves` |
| AC-3 | `tests/unit/cli/test_doctor.py::test_e7_s01_ac3_mcp_without_uv_warns` *(extends E2-S04)* |
| AC-4 | `tests/integration/mcp/test_mcp_server.py::test_e7_s01_ac4_error_shape_consistent` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/mcp/ -v -k e7_s01` passes
- [x] Full suite `pytest tests -q` (2026-08-14): 314 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate)

### Definition of done

- [x] Documented endpoint in CLI reference and user-docs
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-14)

Canonical detail: [50-story.md](epic-stories/50-story.md). `tools.mcp` → `MCPToolset`; `zaumzeug mcp` at `{mcp_port}/mcp` (default 1417); doctor `mcp_uv` warn for stdio without `uv`; JSON-RPC error envelope with `data.ok: false`.

---

## E7-S02 — Custom tool loader

| Field | Value |
|---|---|
| **Feature** | E7.2 |
| **Persona** | Harness developer |
| **Priority** | P0 |

### User story

As a **harness developer**, I want Python tools under `tools/` loaded from config, so that I can extend agents beyond builtins.

### References

- [PRD E7.2](../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §3.3 — `tools/`](../architecture/02-repository-and-layout.md#33-harness-folder-layout)

### Acceptance criteria

- [x] **AC-1** `tools.custom` imports modules from harness folder
- [x] **AC-2** Tools registered as Haystack `ComponentTool` (or equivalent)
- [x] **AC-3** Import errors fail at doctor/ serve with module path
- [x] **AC-4** Custom tools copied to deploy when listed in yaml *(packager row **Done** early with [E5-S02](epic-stories/42-story.md), 2026-07-28; loader remains this story)*

### Implementation tasks (build)

- [x] Implement loader in `src/zaumzeug/runtime/tools/custom.py`
- [x] Validate tool registration at startup
- [x] Example custom tool in user-docs guide

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E7-S02 / E7.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/tools/test_custom_loader.py::test_e7_s02_ac1_imports_custom_modules` |
| AC-2 | `tests/unit/runtime/tools/test_custom_loader.py::test_e7_s02_ac2_registers_component_tool` |
| AC-3 | `tests/integration/test_doctor.py::test_e7_s02_ac3_import_error_at_doctor` |
| AC-4 | **shared early:** `tests/unit/deploy/test_copy_rules.py::test_e7_s02_ac4_custom_tools_in_deploy` *(packager copy landed with [E5-S02](epic-stories/42-story.md), 2026-07-28)* |
| AC-2 | **optional:** ToolCorrectnessMetric in example harness `eval/` when DeepEval present — **not added** (example eval stays the E6-S04 substring metric; guide covers registration) |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/runtime/tools/test_custom_loader.py -v` passes

### Definition of done

- [x] Deploy bundle includes referenced `tools/*.py` only
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-14)

Canonical detail: [51-story.md](epic-stories/51-story.md). `tools.custom` → Haystack `ComponentTool` / `Tool`; doctor `custom_tools` fails with module path; packager copies listed `tools/*.py` only.

---

## E7-S03 — Cursor MCP setup

| Field | Value |
|---|---|
| **Feature** | E7.3 |
| **Persona** | Client integrator |
| **Priority** | P1 |

### User story

As a **Cursor user**, I want documented MCP setup, so that Cursor can invoke my harness as tools.

### References

- [PRD E7.3](../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9.2 — MCP when to use](../architecture/06-runtime-and-protocols.md#92-mcp-when-to-use)
- [E1-S03 — `.cursor/mcp.json.example`](../03-epic.md#e1-s03-project-scaffolding-on-install)

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

Per [Story verification](00-README.md#story-verification-required). **Docs + scaffold** — manual E2E checklist.

| AC | Verification |
|---|---|
| AC-1 | **manual:** guide shows correct URL pattern — [cursor-mcp.md](../../user-docs/guides/cursor-mcp.md) documents `http://localhost:{mcp_port}/mcp` (default **1417**) |
| AC-2 | `tests/unit/install/test_scaffolding.py::test_e7_s03_ac2_mcp_json_example_scaffolded` |
| AC-3 | `tests/unit/install/test_client_install.py::test_e7_s03_ac3_cursor_mcp_flag_writes_json` |
| AC-4 | **manual:** guide documents `uv` requirement for stdio `tools.mcp` |
| AC-1–4 | **manual:** end-to-end checklist in `cursor-mcp.md` completed once |

- [x] Manual E2E checklist completed; automated ACs pass
- [x] `pytest tests/unit/install/test_scaffolding.py::test_e7_s03_ac2_mcp_json_example_scaffolded tests/unit/install/test_client_install.py::test_e7_s03_ac3_cursor_mcp_flag_writes_json -v` passes

### Definition of done

- [x] End-to-end manual test checklist in guide
- [x] Verification checklist complete

### Implementation notes (2026-08-21)

Canonical detail: [52-story.md](epic-stories/52-story.md). Cursor `mcp.json` → `http://localhost:{mcp_port}/mcp` (default 1417); install `--cursor-mcp` writes live `.cursor/mcp.json`; `uv` only for stdio `tools.mcp`.

---

## E7-S04 — Chainlit embedded UI

| Field | Value |
|---|---|
| **Feature** | E7.4 |
| **Persona** | Client integrator |
| **Priority** | P2 |

### User story

As a **web integrator**, I want optional Chainlit at `/chat`, so that I get a quick GUI on the same port as the API.

### References

- [PRD E7.4](../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9.4 — Chainlit embedded](../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)
- [PRD open #2](../prd.md#12-open-decisions-blockers-for-some-stories)

### Acceptance criteria

- [x] **AC-1** `serve.hayhooks.chainlit: true` serves `/chat` on same port as REST
- [x] **AC-2** Document `pip install "hayhooks[chainlit]"` as optional extra
- [x] **AC-3** OpenAI REST remains available alongside Chainlit

### Implementation tasks (build)

- [x] Wire Chainlit flag in serve runner
- [x] Document in web deployment guide (E7-S08)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E7-S04 / E7.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/serve/test_chainlit.py::test_e7_s04_ac1_chat_route_loads` |
| AC-2 | **manual + automated:** user-docs list hayhooks chainlit extra — [web-deployment.md](../user-docs/guides/web-deployment.md) |
| AC-3 | `tests/integration/serve/test_chainlit.py::test_e7_s04_ac3_openai_rest_still_available` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/serve/test_chainlit.py -v` passes

### Definition of done

- [x] Align docs with open #2 primary web UI decision when resolved — **open #2 remains open**; Chainlit is an optional layout, not a product default
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-21)

Canonical detail: [53-story.md](epic-stories/53-story.md). `serve.hayhooks.chainlit: true` mounts `/chat` on the REST port; extra `pip install "hayhooks[chainlit]"`; OpenAI REST stays available.

---

## E7-S05 — ACP adapter

| Field | Value |
|---|---|
| **Feature** | E7.5 |
| **Persona** | Client integrator |
| **Priority** | P1 |

### User story

As a **Zed/JetBrains user**, I want `zaumzeug acp`, so that my IDE can drive the harness as the primary agent via stdio.

### References

- [PRD E7.5](../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9.1 — ACP row](../architecture/06-runtime-and-protocols.md#91-protocol-selection)
- [Architecture §9.3 — ACP when to use](../architecture/06-runtime-and-protocols.md#93-acp-when-to-use)

### Acceptance criteria

- [x] **AC-1** `zaumzeug acp <name>` starts stdio JSON-RPC process
- [x] **AC-2** Zed/JetBrains can register command in agent settings
- [x] **AC-3** ACP naming clarified: Agent Client Protocol ≠ IBM ACP/A2A
- [x] **AC-4** Harness may still use MCP internally for its own tools

### Implementation tasks (build)

- [x] Implement ACP adapter in `src/zaumzeug/serve/acp.py`
- [x] Document registration snippets for Zed and JetBrains

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E7-S05 / E7.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/acp/test_acp_stdio.py::test_e7_s05_ac1_starts_stdio_jsonrpc` |
| AC-2 | **manual + automated:** docs include Zed/JetBrains registration snippets |
| AC-3 | **manual + automated:** docs disambiguate ACP vs A2A |
| AC-4 | `tests/integration/acp/test_acp_stdio.py::test_e7_s05_ac4_internal_mcp_still_works` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/acp/test_acp_stdio.py -v` passes

### Definition of done

- [x] Document Cursor limitation (MCP primary, not generic ACP client)
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-21)

Canonical detail: [54-story.md](epic-stories/54-story.md). `zaumzeug acp <name>` serves Agent Client Protocol JSON-RPC on stdio; Zed/JetBrains snippets in [acp.md](../../user-docs/guides/acp.md); Cursor uses MCP.

---

## E7-S06 — MCP from deploy bundle

| Field | Value |
|---|---|
| **Feature** | E7.6 |
| **Persona** | Ops / platform |
| **Priority** | P1 |

### User story

As **ops**, I want `zaumzeug mcp <name> --deploy`, so that production bundles expose MCP without dev folders.

### References

- [PRD E7.6](../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [E5-S03 — serve --deploy](../06-epic.md#e5-s03-zaumzeug-serve-deploy)
- [E5-S04 — HARNESS_ROOT](../06-epic.md#e5-s04-harness-rootdeploy-environment-override)

### Acceptance criteria

- [x] **AC-1** `zaumzeug mcp <name> --deploy` loads from `deploy/<name>/`
- [x] **AC-2** Same MCP surface as dev mode
- [x] **AC-3** Respects `HARNESS_ROOT=deploy`

### Implementation tasks (build)

- [x] Share root resolution with serve runner

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E7-S06 / E7.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/mcp/test_mcp_deploy.py::test_e7_s06_ac1_loads_deploy_root` |
| AC-2 | `tests/integration/mcp/test_mcp_deploy.py::test_e7_s06_ac2_same_surface_as_dev` |
| AC-3 | `tests/integration/mcp/test_mcp_deploy.py::test_e7_s06_ac3_respects_harness_root_env` |
| AC-1–3 | **optional CI (deferred):** Linux deploy → mcp smoke — pytest covers ACs; not required to close this story |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/mcp/test_mcp_deploy.py -v` passes

### Definition of done

- [x] Documented in `README.deploy.md`
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-21)

Canonical detail: [55-story.md](epic-stories/55-story.md). `zaumzeug mcp <name> --deploy` (and `HARNESS_ROOT=deploy`) uses the same `validate_serve` root as serve; MCP surface matches dev (`POST /mcp`, `GET /status`). Docs: `README.deploy.md`, [deploy.md](../../user-docs/guides/deploy.md).

---

## E7-S07 — Extended builtin tools catalog

| Field | Value |
|---|---|
| **Feature** | E7.7 |
| **Persona** | Harness developer |
| **Priority** | P2 |

### User story

As a **harness developer**, I want additional builtin tools beyond `web_fetch`, so that common agent tasks need no custom Python.

### References

- [PRD E7.7](../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §6.5](../architecture/05-configuration.md#65-builtin-tools-catalog)

### Acceptance criteria

- [ ] **AC-1** Phase 3 ships `calculator`, `read_file` per catalog
- [ ] **AC-2** `read_file` sandboxed to harness workspace paths
- [ ] **AC-3** Unknown builtin ID fails with phase-appropriate available list
- [ ] **AC-4** `search_docs` remains Phase 4 (E8)

### Implementation tasks (build)

- [ ] Implement `calculator` and `read_file` in runtime tools package
- [ ] Extend phase gate in config validation

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E7-S07 / E7.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/tools/test_extended_builtins.py::test_e7_s07_ac1_calculator_and_read_file_in_catalog` |
| AC-2 | `tests/unit/runtime/tools/test_read_file.py::test_e7_s07_ac2_sandbox_blocks_outside_workspace` |
| AC-3 | `tests/unit/config/test_schemas.py::test_e7_s07_ac3_unknown_builtin_phase3_list` |
| AC-4 | `tests/unit/runtime/tools/test_extended_builtins.py::test_e7_s07_ac4_search_docs_not_phase3` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/runtime/tools/test_extended_builtins.py tests/unit/runtime/tools/test_read_file.py -v` passes

### Definition of done

- [ ] Catalog table in Architecture §6.5 matches implementation
- [ ] Verification checklist complete; all ACs traced to tests

---

## E7-S08 — Web client deployment layouts

| Field | Value |
|---|---|
| **Feature** | E7.8 |
| **Persona** | Client integrator · Ops |
| **Priority** | P2 |

### User story

As a **web integrator**, I want documented deployment layouts, so that I can choose Chainlit, Open WebUI, or SPA + proxy patterns.

### References

- [PRD E7.8](../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9.4](../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)
- [PRD open #2](../prd.md#12-open-decisions-blockers-for-some-stories)

### Acceptance criteria

- [x] **AC-1** Document Chainlit embedded co-location — **shipped in E7-S04** ([web-deployment.md](../../user-docs/guides/web-deployment.md))
- [ ] **AC-2** Document Open WebUI + Hayhooks two-container pattern
- [ ] **AC-3** Document custom SPA + Nginx proxy pattern
- [ ] **AC-4** Document Next.js co-located pattern
- [ ] **AC-5** Clarify OpenAI `baseURL` points at harness server, not OpenAI API

### Implementation tasks (build)

- [x] Author `user-docs/guides/web-deployment.md` — **file exists** (E7-S04 Chainlit recipe + preview of other layouts)
- [ ] Expand Open WebUI / SPA / Next.js recipes (preview only today)
- [ ] Include example `baseURL` and env vars for remaining layouts
- [ ] Cross-link Hayhooks `/v1/models`, `/docs` endpoints for remaining layouts

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). **Docs-only** — manual checklist.

| AC | Verification |
|---|---|
| AC-1 | **manual:** web-deployment.md Chainlit section — **done** (E7-S04, 2026-08-21) |
| AC-2 | **manual:** Open WebUI two-container section |
| AC-3 | **manual:** SPA + Nginx section |
| AC-4 | **manual:** Next.js co-located section |
| AC-5 | **manual:** baseURL examples point at harness host |

- [ ] Manual checklist completed for all five ACs

### Definition of done

- [ ] No implementation required beyond docs unless Chainlit flag (E7-S04) — **flag shipped 2026-08-21**; this story remains docs for the other layouts
- [ ] Verification checklist complete

### Implementation notes (2026-08-21)

E7-S04 shipped the Chainlit recipe and created `user-docs/guides/web-deployment.md`. Remaining layouts stay on this story.
