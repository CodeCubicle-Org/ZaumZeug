# E5-S08 — Deploy platform policy

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/48-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E5-S08 |
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
| **Prerequisites** | [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) |

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

### Acceptance criteria

- [ ] **AC-1** `README.deploy.md` states Linux-first production (VM, bare metal, Docker/K8s)
- [ ] **AC-2** Bundle is OS-neutral Python + pinned artifacts
- [ ] **AC-3** Windows/macOS production serve supported best-effort, not CI-gated in v1
- [ ] **AC-4** Optional container path referenced (E8-S05)

### Implementation tasks (build)

- [ ] Author platform matrix in `README.deploy.md`
- [ ] Phase 2+ Linux CI: deploy → serve --deploy smoke

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required).

| AC | Verification |
|---|---|
| AC-1 | **manual:** README.deploy.md platform section |
| AC-2 | `tests/integration/deploy/test_deploy_golden.py::test_e5_s08_ac2_os_neutral_bundle` |
| AC-3 | **manual:** docs state best-effort Win/macOS prod |
| AC-4 | **manual:** cross-link E8-S05 when present |
| AC-1–2 | **CI:** Linux job deploy → serve --deploy smoke |

- [ ] Manual checklist + CI smoke complete

### Definition of done

- [ ] Aligns with PRD §14 CI-gated column
- [ ] Verification checklist complete

---
