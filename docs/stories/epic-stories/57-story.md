# E7-S08 — Web client deployment layouts

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/57-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 |
| **Story ID** | E7-S08 |
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

Per [Story verification](../00-README.md#story-verification-required). **Docs-only** — manual checklist.

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

E7-S04 shipped the Chainlit co-location recipe and created `user-docs/guides/web-deployment.md` (mirrored in `install/templates/user-docs/guides/`). Open #2 stays open. Remaining work: Open WebUI two-container, SPA + Nginx, Next.js, and `baseURL` examples for those layouts.
