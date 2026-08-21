# E7-S08 — Web client deployment layouts

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/57-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 |
| **Story ID** | E7-S08 |
| **Status** | Done (2026-08-21) |
| **Epic** | [E7 — Tools, MCP, and ACP](../07-epic.md) |
| **Phase** | 3 |
| **Epic build order** | 7 of 8 |
| **Story sequence** | 57 of 63 (global build order) |
| **Source** | Extracted from [`07-epic.md`](../07-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E7](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3) · [Architecture](../../architecture.md) |

---

## E7-S08 — Web client deployment layouts

| Field | Value |
|---|---|
| **Feature** | E7.8 |
| **Persona** | Client integrator · Ops |
| **Priority** | P2 |
| **Prerequisites** | [E7-S04](53-story.md#e7-s04-chainlit-embedded-ui) · [E7-S05](54-story.md#e7-s05-acp-adapter) |
| **Status** | Done (2026-08-21) |

### User story

As a **web integrator**, I want documented deployment layouts, so that I can choose Chainlit, Open WebUI, or SPA + proxy patterns.

### References

- [PRD E7.8](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9.4](../../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)
- [PRD open #2](../../prd.md#12-open-decisions-blockers-for-some-stories)


### Implementation resources

**Internal spec**

- [Architecture §9.4 — web deployment layouts](../../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)
- Cross-link Chainlit ([E7-S04](53-story.md)) and ACP ([E7-S05](54-story.md)) setup guides

### Acceptance criteria

- [x] **AC-1** Document Chainlit embedded co-location — **shipped in E7-S04** ([web-deployment.md](../../../user-docs/guides/web-deployment.md))
- [x] **AC-2** Document Open WebUI + Hayhooks two-container pattern
- [x] **AC-3** Document custom SPA + Nginx proxy pattern
- [x] **AC-4** Document Next.js co-located pattern
- [x] **AC-5** Clarify OpenAI `baseURL` points at harness server, not OpenAI API

### Implementation tasks (build)

- [x] Author `user-docs/guides/web-deployment.md` — Chainlit (E7-S04) plus Open WebUI / SPA / Next.js recipes
- [x] Expand Open WebUI / SPA / Next.js recipes
- [x] Include example `baseURL` and env vars for remaining layouts
- [x] Cross-link Hayhooks `/v1/models`, `/docs` endpoints for remaining layouts

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **Docs-only** with content-assertion tests. Test file header: `# Story: E7-S08 / E7.8`.

| AC | Verification |
|---|---|
| AC-1 | **manual:** web-deployment.md Chainlit section — **done** (E7-S04, 2026-08-21); `tests/integration/serve/test_chainlit.py::test_e7_s04_ac2_user_docs_list_chainlit_extra` |
| AC-2 | `tests/unit/docs/test_web_deployment.py::test_e7_s08_ac2_open_webui_two_container_section` |
| AC-3 | `tests/unit/docs/test_web_deployment.py::test_e7_s08_ac3_spa_nginx_proxy_section` |
| AC-4 | `tests/unit/docs/test_web_deployment.py::test_e7_s08_ac4_nextjs_colocated_section` |
| AC-5 | `tests/unit/docs/test_web_deployment.py::test_e7_s08_ac5_baseurl_points_at_harness_not_openai` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/docs/test_web_deployment.py tests/integration/serve/test_chainlit.py -v` passes
- [x] Full suite `pytest tests -q` (2026-08-21): 344 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate)

### Definition of done

- [x] No implementation required beyond docs unless Chainlit flag (E7-S04) — **flag shipped 2026-08-21**; remaining layouts are docs only
- [x] Verification checklist complete; ACs 2–5 traced to content tests
- [x] Open #2 (primary web UI) remains open — layouts are peers, not a product default

### Implementation notes (2026-08-21)

- Guide: [web-deployment.md](../../../user-docs/guides/web-deployment.md) (mirrored in `install/templates/user-docs/guides/`).
- Open WebUI two-container compose uses `OPENAI_API_BASE_URL=http://hayhooks:1416/v1`. Serve still binds **127.0.0.1**; the guide documents host-network / `host.docker.internal` reachability until a wide-open bind / [E8-S05](62-story.md) Dockerfile.
- SPA + Nginx: `/api/v1/` → `127.0.0.1:1416/v1/`; Next.js `:3000` server-side `OPENAI_BASE_URL=http://127.0.0.1:1416/v1`.
- Every recipe sets OpenAI `baseURL` at the harness, not `api.openai.com`; probes include `GET /v1/models` and `GET /docs`.
- Tests: `tests/unit/docs/test_web_deployment.py`.
- Full suite 2026-08-21: 344 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate).
- Open #2 stays open.

---
