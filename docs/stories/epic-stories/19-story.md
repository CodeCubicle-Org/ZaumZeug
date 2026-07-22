# E1-S02 — Install shell wrappers

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/19-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-22 |
| **Story ID** | E1-S02 |
| **Status** | Done |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 19 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) · **DoD closed by** [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) |

---

## E1-S02 — Install shell wrappers

| Field | Value |
|---|---|
| **Feature** | E1.2 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E1-S01](18-story.md#e1-s01-cross-platform-install-script) |
| **Status** | Done (2026-07-22) |
| **Open — carried forward** | — |
| **Closed by E1-S07** | [DoD *Wrappers tested on respective OS in CI matrix*](#definition-of-done) → [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) (2026-07-22) |

### User story

As a **harness developer**, I want OS-specific install wrappers that delegate to the Python script, so that I can run familiar one-liners on my platform.

### References

- [PRD E1.2](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [PRD §7.4 — Install command table](../../prd.md#74-user-installation-guide-content-for-readme--phase-1)


### Implementation resources

**Internal spec**

- [Architecture §3.4 — install wrappers](../../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)
- Mirror pattern from `install/client_install.py` → `install.sh` / `install.ps1` forwarding args

### Acceptance criteria

- [x] **AC-1** `install/client-install.sh` delegates to `client_install.py` with forwarded args
- [x] **AC-2** `install/client-install.ps1` delegates to `client_install.py` with forwarded args
- [x] **AC-3** All flags from E1-S01 pass through unchanged
- [x] **AC-4** Wrappers contain no duplicated install logic

### Implementation tasks (build)

- [x] Add `install/client-install.sh` (bash)
- [x] Add `install/client-install.ps1` (PowerShell)
- [x] Document commands in user-docs (see E1-S05) — command table in `user-docs/getting-started/installation.md` (+ install template); full §7.4 guide **Done** in [E1-S05](22-story.md)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E1-S02 / E1.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac1_sh_delegates_to_python` |
| AC-2 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac2_ps1_delegates_to_python` |
| AC-3 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac3_flags_forwarded` |
| AC-4 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac4_no_duplicated_install_logic` |
| AC-1–4 | **shared:** [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) CI matrix invokes wrappers per OS |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/install/test_wrappers.py -v` passes

### Definition of done

- [x] Wrappers tested on respective OS in CI matrix *(closed by [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) — `.github/workflows/ci-matrix.yml` invokes `client-install.sh` / `client-install.ps1` — Done 2026-07-22)*
- [x] Verification checklist complete; all ACs traced to tests

---
