# E5-S07 — Deploy git policy

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/47-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-29 |
| **Story ID** | E5-S07 |
| **Status** | Done |
| **Epic** | [E5 — Deploy Packaging](../06-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 6 of 8 |
| **Story sequence** | 47 of 63 (global build order) |
| **Source** | Extracted from [`06-epic.md`](../06-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E5](../../prd.md#epic-e5--deploy-packaging-phase-2) · [Architecture](../../architecture.md) |

---

## E5-S07 — Deploy git policy

| Field | Value |
|---|---|
| **Feature** | E5.7 |
| **Persona** | SDK maintainer |
| **Priority** | P2 |
| **Prerequisites** | [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) ✅ (2026-07-28) |

### User story

As an **SDK maintainer**, I want clear git policy for deploy artifacts, so that teams choose between local-only bundles and audited releases.

### References

- [PRD E5.7](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.4](../../architecture/07-deploy-packaging.md#104-git-and-gitignore)


### Implementation resources

**Internal spec**

- [Architecture §10.4 — deploy git policy](../../architecture/07-deploy-packaging.md#104-git-and-gitignore)
- `.gitignore` patterns for `deploy/` generated bundles

**Docs / code**

- `install/client_install.py` — `GITIGNORE_ENTRIES` / `ensure_gitignore_entries`
- [user-docs/guides/deploy.md](../../../user-docs/guides/deploy.md#git-policy-for-deploy-bundles) (+ install template mirror)
- [CONTRIBUTING.md](../../../CONTRIBUTING.md#deploy-git-policy-maintainers) — maintainer release / CI options
- [`.github/workflows/ci-matrix.yml`](../../../.github/workflows/ci-matrix.yml) — commented upload-artifact example

### Acceptance criteria

- [x] **AC-1** Default `.gitignore` includes `deploy/` and `usr-harnesses/*/artifacts/`
- [x] **AC-2** Documented option to commit `deploy/<name>/` for release tags
- [x] **AC-3** CI may build and upload bundle as workflow artifact

### Implementation tasks (build)

- [x] Ensure install scaffolding sets `.gitignore` entries (E1-S03)
- [x] Document release commit policy in maintainer docs

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S07 / E5.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/install/test_scaffolding.py::test_e5_s07_ac1_gitignore_deploy_and_artifacts` *(extends E1-S03)* |
| AC-2 | **manual:** maintainer docs describe release commit option ([deploy.md](../../../user-docs/guides/deploy.md#git-policy-for-deploy-bundles), [CONTRIBUTING.md](../../../CONTRIBUTING.md#deploy-git-policy-maintainers)) |
| AC-3 | **manual:** CI workflow documents artifact upload (commented example in [ci-matrix.yml](../../../.github/workflows/ci-matrix.yml)) |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/install/test_scaffolding.py -v` passes (6 passed, 0 skipped)

### Definition of done

- [x] No accidental commit of `.env` in examples (`.env` remains gitignored via scaffolding)
- [x] Verification checklist complete

### Implementation notes (2026-07-28)

- Scaffolding `GITIGNORE_ENTRIES` adds `usr-harnesses/*/artifacts/` alongside existing `/deploy/`, `artifacts/`, `.venv`, `.env`.
- Release force-add path and CI `upload-artifact` option documented for maintainers; default remains local-only bundles.
---
