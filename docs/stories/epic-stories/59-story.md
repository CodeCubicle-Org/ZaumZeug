# E8-S02 — Production auth

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/59-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 |
| **Story ID** | E8-S02 |
| **Status** | Done (2026-08-21) |
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
| **Status** | Done (2026-08-21) |

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

- [x] **AC-1** `user-docs/guides/production-auth.md` documents Traefik as the **reference** production pattern
- [x] **AC-2** Cover REST (`/v1/chat/completions`), MCP (`/mcp`), and Chainlit (`/chat`) path routing
- [x] **AC-3** Example Traefik static/dynamic config: TLS, Headers middleware (bearer validation) or ForwardAuth
- [x] **AC-4** `README.deploy.md` links to guide; notes Hayhooks has no built-in auth in v1
- [x] **AC-5** Document Nginx/Caddy as optional alternatives (same proxy-only principle)
- [x] **AC-6** No secrets in yaml or deploy bundle; auth credentials only in Traefik/env on target host

### Implementation tasks (build)

- [x] Author `user-docs/guides/production-auth.md` with Traefik examples
- [x] Add `deploy/<name>/` optional `traefik/` snippet or comment block in `README.deploy.md`
- [x] Cross-link from [E7-S08](../07-epic.md) web-deployment guide
- [x] **Do not** add in-process auth to serve layer in v1

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **Docs-only** with content-assertion tests plus AC-6 bundle scan. Test file header: `# Story: E8-S02 / E8.2`. Confirm no SDK auth code added.

| AC | Verification |
|---|---|
| AC-1 | `tests/unit/docs/test_production_auth.py::test_e8_s02_ac1_traefik_is_reference_pattern` |
| AC-2 | `tests/unit/docs/test_production_auth.py::test_e8_s02_ac2_rest_mcp_chainlit_paths` |
| AC-3 | `tests/unit/docs/test_production_auth.py::test_e8_s02_ac3_traefik_static_dynamic_yaml` |
| AC-4 | `tests/unit/docs/test_production_auth.py::test_e8_s02_ac4_readme_deploy_links_guide` |
| AC-5 | `tests/unit/docs/test_production_auth.py::test_e8_s02_ac5_nginx_caddy_alternatives` |
| AC-6 | `tests/integration/deploy/test_deploy.py::test_e8_s02_ac6_no_secrets_in_bundle` |
| Schema | `tests/unit/config/test_schemas.py::test_e8_s02_no_serve_auth_in_schema` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/docs/test_production_auth.py tests/integration/deploy/test_deploy.py::test_e8_s02_ac6_no_secrets_in_bundle -v` passes
- [x] Manual checklist: no in-process auth in serve layer (`ServeConfig` extra-forbid rejects `serve.auth`)

### Definition of done

- [x] Ops can deploy harness behind Traefik with TLS + bearer auth using docs only
- [x] Verification checklist complete; ACs traced to tests

### Implementation notes (2026-08-21)

- Guide: [production-auth.md](../../../user-docs/guides/production-auth.md) (mirrored in `install/templates/user-docs/guides/`).
- Bundle `README.deploy.md` notes Hayhooks has no built-in auth; optional secret-free `traefik/traefik.yml` + `dynamic.yml` copied by the packager.
- No `serve.auth` schema field; Hayhooks stays unauthenticated behind the proxy.
- Tests: `tests/unit/docs/test_production_auth.py`, `test_e8_s02_ac6_no_secrets_in_bundle`, `test_e8_s02_no_serve_auth_in_schema`. Full suite 2026-08-21: **360 passed, 1 skipped**.

---
