# E5-S05 — Target ship workflow documentation

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/45-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E5-S05 |
| **Epic** | [E5 — Deploy Packaging](../06-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 6 of 8 |
| **Story sequence** | 45 of 63 (global build order) |
| **Source** | Extracted from [`06-epic.md`](../06-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E5](../../prd.md#epic-e5--deploy-packaging-phase-2) · [Architecture](../../architecture.md) |

---

## E5-S05 — Target ship workflow documentation

| Field | Value |
|---|---|
| **Feature** | E5.5 |
| **Persona** | Ops / platform · Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy) · [E5-S09c](49.3-story.md#e5-s09c-target-install-verify-integration) |

### User story

As **ops**, I want a documented copy → install → serve workflow, so that I can deploy to a clean server without DSPy or GEPA on the target.

### References

- [PRD E5.5](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.5 — Production dependencies](../../architecture/07-deploy-packaging.md#105-production-server-dependencies)
- [Architecture §10.6 — Platform targets](../../architecture/07-deploy-packaging.md#106-deploy-platform-targets)


### Implementation resources

**Internal spec**

- [Architecture §10.5 — production dependencies](../../architecture/07-deploy-packaging.md#105-production-server-dependencies)
- [E5-S09c target install verify](49.3-story.md)

### Acceptance criteria

- [ ] **AC-1** Documented path: copy `deploy/<name>/` → `target_install` → create `.env` → `zaumzeug serve --deploy`
- [ ] **AC-2** Target installs runtime deps only (`pip install zaumzeug`)
- [ ] **AC-3** No DSPy, GEPA, or DeepEval on production server by default
- [ ] **AC-4** Python 3.11+ must pre-exist on target
- [ ] **AC-5** `.env` never shipped inside bundle

### Implementation tasks (build)

- [ ] Author workflow in `README.deploy.md` and user-docs guide
- [ ] Include Win/macOS/Linux invocation table
- [ ] Link from root README production note (abbreviated)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **Docs + integration** — manual checklist plus E5-S09/E5-S03 tests.

| AC | Verification |
|---|---|
| AC-1 | **manual:** README.deploy.md workflow steps; **integration:** E5-S03 AC-4 |
| AC-2 | **integration:** `tests/integration/deploy/test_target_install.py::test_e5_s05_ac2_runtime_only_install` |
| AC-3 | `tests/integration/deploy/test_target_install.py::test_e5_s05_ac3_no_dspy_gepa_deepeval` |
| AC-4 | **manual:** docs state Python 3.11+ prerequisite |
| AC-5 | `tests/integration/deploy/test_deploy.py::test_e5_s05_ac5_no_env_in_bundle` |

- [ ] Manual checklist completed; integration tests pass

### Definition of done

- [ ] Happy path validated on clean Linux target (Phase 2+ CI)
- [ ] Verification checklist complete

---
