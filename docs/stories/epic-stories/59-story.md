# E8-S02 — Production auth

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/59-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E8-S02 |
| **Epic** | [E8 — RAG and Production Hardening](../08-epic.md) |
| **Phase** | 4 |
| **Epic build order** | 8 of 8 |
| **Story sequence** | 59 of 63 (global build order) |
| **Source** | Extracted from [`08-epic.md`](../08-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E8](../../prd.md#epic-e8--rag-and-production-hardening-phase-4) · [Architecture](../../architecture.md) |

---

## E8-S02 — Production auth

| Field | Value |
|---|---|
| **Feature** | E8.2 |
| **Persona** | Ops / platform |
| **Priority** | P1 |
| **Prerequisites** | [E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy) ✅ (2026-07-28) |

### User story

As **ops**, I want an auth story for production serve, so that harness endpoints are not wide open on the public internet.

### References

- [PRD E8.2](../../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §14 — Security](../../architecture/10-operations-and-reference.md#14-security-phase-1-stance)
- [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/) · [Traefik Headers middleware](https://doc.traefik.io/traefik/middlewares/http/headers/)


### Implementation resources

**Libraries & docs**

- [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)
- [Traefik Headers middleware](https://doc.traefik.io/traefik/middlewares/http/headers/)
- [Architecture §14 — proxy-only auth Phase 4](../../architecture/10-operations-and-reference.md#14-security-phase-1-stance)

### Decision (resolved)

**Proxy-only via Traefik** — production auth lives at the edge, not in ZaumZeug/Hayhooks. Traefik terminates TLS and applies bearer/API-key or ForwardAuth middleware; harness process binds behind the proxy (e.g. `127.0.0.1` or Docker internal network). **No `serve.auth` in SDK v1.**

### Acceptance criteria

- [ ] **AC-1** `user-docs/guides/production-auth.md` documents Traefik as the **reference** production pattern
- [ ] **AC-2** Cover REST (`/v1/chat/completions`), MCP (`/mcp`), and Chainlit (`/chat`) path routing
- [ ] **AC-3** Example Traefik static/dynamic config: TLS, Headers middleware (bearer validation) or ForwardAuth
- [ ] **AC-4** `README.deploy.md` links to guide; notes Hayhooks has no built-in auth in v1
- [ ] **AC-5** Document Nginx/Caddy as optional alternatives (same proxy-only principle)
- [ ] **AC-6** No secrets in yaml or deploy bundle; auth credentials only in Traefik/env on target host

### Implementation tasks (build)

- [ ] Author `user-docs/guides/production-auth.md` with Traefik examples
- [ ] Add `deploy/<name>/` optional `traefik/` snippet or comment block in `README.deploy.md`
- [ ] Cross-link from [E7-S08](../07-epic.md) web-deployment guide
- [ ] **Do not** add in-process auth to serve layer in v1

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **Docs-only** — manual checklist; confirm no SDK auth code added.

| AC | Verification |
|---|---|
| AC-1 | **manual:** production-auth.md exists with Traefik as reference |
| AC-2 | **manual:** REST, MCP, Chainlit paths documented |
| AC-3 | **manual:** example Traefik config blocks present and valid YAML |
| AC-4 | **manual:** README.deploy.md links to guide |
| AC-5 | **manual:** Nginx/Caddy alternatives noted |
| AC-6 | `tests/integration/deploy/test_deploy.py::test_e8_s02_ac6_no_secrets_in_bundle` *(extends deploy tests)* |

- [ ] Manual checklist completed; no in-process auth in codebase

### Definition of done

- [ ] Ops can deploy harness behind Traefik with TLS + bearer auth using docs only
- [ ] Verification checklist complete

---
