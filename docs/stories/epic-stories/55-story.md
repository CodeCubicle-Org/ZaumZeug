# E7-S06 — MCP from deploy bundle

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/55-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E7-S06 |
| **Epic** | [E7 — Tools, MCP, and ACP](../07-epic.md) |
| **Phase** | 3 |
| **Epic build order** | 7 of 8 |
| **Story sequence** | 55 of 63 (global build order) |
| **Source** | Extracted from [`07-epic.md`](../07-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E7](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3) · [Architecture](../../architecture.md) |

---

## E7-S06 — MCP from deploy bundle

| Field | Value |
|---|---|
| **Feature** | E7.6 |
| **Persona** | Ops / platform |
| **Priority** | P1 |
| **Prerequisites** | [E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy) ✅ (2026-07-28) · [E7-S01](50-story.md#e7-s01-mcp-tool-configuration) |

### User story

As **ops**, I want `zaumzeug mcp <name> --deploy`, so that production bundles expose MCP without dev folders.

### References

- [PRD E7.6](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [E5-S03 — serve --deploy](../06-epic.md#e5-s03-zaumzeug-serve-deploy)
- [E5-S04 — HARNESS_ROOT](../06-epic.md#e5-s04-harness-rootdeploy-environment-override)


### Implementation resources

**Internal spec**

- [E5-S03 serve --deploy](43-story.md) — MCP from deploy bundle uses production paths
- [E7-S01 MCP config](50-story.md)

### Acceptance criteria

- [ ] **AC-1** `zaumzeug mcp <name> --deploy` loads from `deploy/<name>/`
- [ ] **AC-2** Same MCP surface as dev mode
- [ ] **AC-3** Respects `HARNESS_ROOT=deploy`

### Implementation tasks (build)

- [ ] Share root resolution with serve runner

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S06 / E7.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/mcp/test_mcp_deploy.py::test_e7_s06_ac1_loads_deploy_root` |
| AC-2 | `tests/integration/mcp/test_mcp_deploy.py::test_e7_s06_ac2_same_surface_as_dev` |
| AC-3 | `tests/integration/mcp/test_mcp_deploy.py::test_e7_s06_ac3_respects_harness_root_env` |
| AC-1–3 | **optional CI:** Linux deploy → mcp smoke (Phase 3) |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/mcp/test_mcp_deploy.py -v` passes

### Definition of done

- [ ] Documented in `README.deploy.md`
- [ ] Verification checklist complete; all ACs traced to tests

---
