# E1-S06 — Root README

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/23-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E1-S06 |
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

- [ ] **AC-1** Root `README.md` created in Phase 1 alongside install path
- [ ] **AC-2** Includes vision one-liner, install command table, mock-first quick start
- [ ] **AC-3** States < 15 min target and ~1–2.5 GB dev venv planning range
- [ ] **AC-4** Includes updating-dependencies summary with post-`git pull` commands
- [ ] **AC-5** Links to `user-docs/getting-started/installation.md` for depth — not a duplicate

### Implementation tasks (build)

- [ ] Author root `README.md` from PRD §7.4 checklist
- [ ] Add abbreviated project layout (`usr-harnesses/`, `deploy/`, `config/`)
- [ ] Cross-link `docs/prd.md` and `docs/architecture.md` for maintainers only

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **Docs-only** — manual checklist.

| AC | Verification |
|---|---|
| AC-1 | **manual:** `README.md` exists at repo root |
| AC-2 | **manual:** vision, install table, mock quick start present |
| AC-3 | **manual:** time and disk range stated |
| AC-4 | **manual:** dependency update commands present |
| AC-5 | **manual:** link to installation.md; no full duplicate of user-docs |

- [ ] Manual checklist completed; no contradiction with PRD §11 success metrics

### Definition of done

- [ ] README review: no contradiction with PRD §11 success metrics
- [ ] Verification checklist complete

---
