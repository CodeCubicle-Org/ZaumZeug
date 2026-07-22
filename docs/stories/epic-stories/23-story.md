# E1-S06 — Root README

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/23-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-22 |
| **Story ID** | E1-S06 |
| **Status** | Done |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 23 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) |

---

## E1-S06 — Root README

| Field | Value |
|---|---|
| **Feature** | E1.6 |
| **Persona** | Harness developer · SDK maintainer |
| **Priority** | P1 |
| **Prerequisites** | [E1-S05](22-story.md#e1-s05-user-documentation-skeleton) |
| **Status** | Done (2026-07-22) |

### User story

As a **new contributor**, I want a short root README, so that I understand vision, install, and first commands without reading the full PRD.

### References

- [PRD E1.6](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [PRD §7.4](../../prd.md#74-user-installation-guide-content-for-readme--phase-1)
- [PRD §15 — Documentation map](../../prd.md#15-documentation-map)


### Implementation resources

**Internal spec**

- [PRD §7.4 — user installation guide content](../../prd.md#74-user-installation-guide-content-for-readme--phase-1)
- Link to [Architecture hub](../../architecture.md) and [stories index](../00-README.md)

### Acceptance criteria

- [x] **AC-1** Short new-contributor guide created in Phase 1 alongside install path — delivered as root [`CONTRIBUTING.md`](../../../CONTRIBUTING.md) (existing product [`README.md`](../../../README.md) left as overview)
- [x] **AC-2** Includes vision one-liner, install command table, mock-first quick start
- [x] **AC-3** States < 15 min target and ~1–2.5 GB dev venv planning range
- [x] **AC-4** Includes updating-dependencies summary with post-`git pull` commands
- [x] **AC-5** Links to `user-docs/getting-started/installation.md` for depth — not a duplicate

### Implementation tasks (build)

- [x] Author root `CONTRIBUTING.md` from PRD §7.4 checklist (new-contributor entry; do not overwrite product README)
- [x] Add abbreviated project layout (`usr-harnesses/`, `deploy/`, `config/`)
- [x] Cross-link `docs/prd.md` and `docs/architecture.md` for maintainers only

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E1-S06 / E1.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac1_contributing_exists` |
| AC-2 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac2_vision_install_mock_quick_start` |
| AC-3 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac3_time_and_disk_ranges` |
| AC-4 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac4_updating_dependencies_after_pull` |
| AC-5 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac5_links_installation_not_full_duplicate` |

- [x] Every AC row above has a passing test
- [x] `pytest tests/unit/docs/test_contributing_guide.py -v` passes
- [x] Manual review: no contradiction with PRD §11 success metrics (`< 15 minutes` target; ~30 min slow networks)

### Definition of done

- [x] Guide review: no contradiction with PRD §11 success metrics
- [x] Verification checklist complete; all ACs traced to tests

---
