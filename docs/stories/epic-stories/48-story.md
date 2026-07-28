# E5-S08 — Deploy platform policy

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/48-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-29 |
| **Story ID** | E5-S08 |
| **Status** | Done |
| **Epic** | [E5 — Deploy Packaging](../06-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 6 of 8 |
| **Story sequence** | 48 of 63 (global build order) |
| **Source** | Extracted from [`06-epic.md`](../06-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E5](../../prd.md#epic-e5--deploy-packaging-phase-2) · [Architecture](../../architecture.md) |

---

## E5-S08 — Deploy platform policy

| Field | Value |
|---|---|
| **Feature** | E5.8 |
| **Persona** | Ops / platform |
| **Priority** | P1 |
| **Prerequisites** | [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) ✅ · [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) ✅ |

### User story

As **ops**, I want a documented platform matrix, so that I know Linux is the primary production target while dev works everywhere.

### References

- [PRD E5.8](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.6](../../architecture/07-deploy-packaging.md#106-deploy-platform-targets)
- [PRD §14 — Cross-platform table](../../prd.md#cross-platform-support)


### Implementation resources

**Internal spec**

- [Architecture §10.6 — platform targets matrix](../../architecture/07-deploy-packaging.md#106-deploy-platform-targets)
- [GitHub Actions runners](https://docs.github.com/en/actions/using-github-hosted-runners)

**Docs / code**

- `install/templates/deploy/README.deploy.md` — platform matrix (rendered into every bundle)
- [user-docs/guides/deploy.md](../../../user-docs/guides/deploy.md#platforms) (+ install template mirror)
- [`install/ci_serve_smoke.py --deploy`](../../../install/ci_serve_smoke.py) — production-bundle smoke
- [`.github/workflows/ci-matrix.yml`](../../../.github/workflows/ci-matrix.yml) — Linux `deploy` → `serve --deploy` step

### Acceptance criteria

- [x] **AC-1** `README.deploy.md` states Linux-first production (VM, bare metal, Docker/K8s)
- [x] **AC-2** Bundle is OS-neutral Python + pinned artifacts
- [x] **AC-3** Windows/macOS production serve supported best-effort, not CI-gated in v1
- [x] **AC-4** Optional container path referenced (E8-S05)

### Implementation tasks (build)

- [x] Author platform matrix in `README.deploy.md`
- [x] Phase 2+ Linux CI: deploy → serve --deploy smoke

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S02 / E5.2 · E5-S08 / E5.8`.

| AC | Verification |
|---|---|
| AC-1 | **manual + docs test:** README.deploy.md platform section; `test_e5_s08_platform_docs_matrix` |
| AC-2 | `tests/integration/deploy/test_deploy_golden.py::test_e5_s08_ac2_os_neutral_bundle` |
| AC-3 | **manual + docs test:** docs state best-effort Win/macOS prod (`test_e5_s08_platform_docs_matrix`) |
| AC-4 | **manual + docs test:** cross-link E8-S05 (`test_e5_s08_platform_docs_matrix`) |
| AC-1–2 | **CI:** Linux job deploy → serve --deploy smoke ([ci-matrix.yml](../../../.github/workflows/ci-matrix.yml) + `ci_serve_smoke.py --deploy`) |

- [x] Manual checklist + CI smoke wired; local deploy → serve --deploy smoke green
- [x] `pytest tests/integration/deploy/test_deploy_golden.py -v` passes (3 passed, 0 skipped)

### Definition of done

- [x] Aligns with PRD §14 CI-gated column
- [x] Verification checklist complete

### Implementation notes (2026-07-29)

- Platform matrix authored in bundle `README.deploy.md` and [user-docs/guides/deploy.md](../../../user-docs/guides/deploy.md#platforms): Linux-first production (VM / bare metal / Docker/K8s), OS-neutral bundle, Win/macOS best-effort not CI-gated, E8-S05 Dockerfile forward reference.
- OS-neutral + pinned-artifact assertions in `test_e5_s08_ac2_os_neutral_bundle`; docs matrix in `test_e5_s08_platform_docs_matrix`.
- Linux CI step: `zaumzeug deploy example` → `ci_serve_smoke.py example --deploy` (gated with `runner.os == 'Linux'`).
---
