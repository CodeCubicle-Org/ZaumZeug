# E8-S05 — Dockerfile template

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/62-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 |
| **Story ID** | E8-S05 |
| **Epic** | [E8 — RAG and Production Hardening](../08-epic.md) |
| **Phase** | 4 |
| **Epic build order** | 8 of 8 |
| **Story sequence** | 62 of 63 (global build order) |
| **Source** | Extracted from [`08-epic.md`](../08-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E8](../../prd.md#epic-e8--rag-and-production-hardening-phase-4) · [Architecture](../../architecture.md) |

---

## E8-S05 — Dockerfile template

| Field | Value |
|---|---|
| **Feature** | E8.5 |
| **Persona** | Ops / platform |
| **Priority** | P2 |
| **Prerequisites** | [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) ✅ · [E5-S08](48-story.md#e5-s08-deploy-platform-policy) ✅ (2026-07-29) · [E8-S02](59-story.md#e8-s02-production-auth) ✅ (2026-08-21) |

### User story

As **ops**, I want an optional generated Dockerfile in the deploy bundle, so that I can containerize production serve quickly.

### References

- [PRD E8.5](../../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [E5-S08 — Platform policy](../06-epic.md#e5-s08-deploy-platform-policy)
- [Architecture §10.6](../../architecture/07-deploy-packaging.md#106-deploy-platform-targets)


### Implementation resources

**Libraries & docs**

- [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
- [Architecture §10.6 — container targets](../../architecture/07-deploy-packaging.md#106-deploy-platform-targets)
- [E8-S02 Traefik auth](59-story.md) ✅ (2026-08-21) for production compose examples

### Acceptance criteria

- [ ] **AC-1** Optional generated `deploy/<name>/Dockerfile` (config flag or deploy flag)
- [ ] **AC-2** Base image Python 3.11+; runs `target_install` pattern or pre-baked venv
- [ ] **AC-3** Document `zaumzeug serve <name> --deploy` as container CMD
- [ ] **AC-4** `.env` injected at runtime, not baked into image

### Implementation tasks (build)

- [ ] Add Dockerfile template to deploy packager
- [ ] Document build/run in `README.deploy.md`
- [ ] Example docker-compose for Open WebUI + harness (optional)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E8-S05 / E8.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_dockerfile.py::test_e8_s05_ac1_dockerfile_generated_when_flagged` |
| AC-2 | `tests/integration/deploy/test_dockerfile.py::test_e8_s05_ac2_python311_base_and_target_install` |
| AC-3 | **manual:** README.deploy.md documents CMD |
| AC-4 | `tests/integration/deploy/test_dockerfile.py::test_e8_s05_ac4_no_env_baked_in_image` |
| AC-1–4 | **optional CI:** Linux container smoke test |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/deploy/test_dockerfile.py -v` passes

### Definition of done

- [ ] Linux container smoke test on CI (optional)
- [ ] Verification checklist complete; all ACs traced to tests

---
