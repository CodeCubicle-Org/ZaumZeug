# E1-S05 — User documentation skeleton

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/22-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-22 |
| **Story ID** | E1-S05 |
| **Status** | Done |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 22 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) |

---

## E1-S05 — User documentation skeleton

| Field | Value |
|---|---|
| **Feature** | E1.5 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E1-S03](20-story.md#e1-s03-project-scaffolding-on-install) |
| **Status** | Done (2026-07-22) |

### User story

As a **harness developer**, I want a structured `user-docs/` tree after install, so that I can follow guides without reading internal design docs.

### References

- [PRD E1.5](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.5](../../architecture/02-repository-and-layout.md#35-user-documentation)
- [PRD §7.4 — Full install guide content](../../prd.md#74-user-installation-guide-content-for-readme--phase-1)


### Implementation resources

**Templates**

- [Architecture §3.5 — user-docs layout](../../architecture/02-repository-and-layout.md#35-user-documentation)
- [Architecture §13.6 — testing guide template](../../architecture/10-operations-and-reference.md#136-testing-playbook)
- Seed from `install/templates/user-docs/`

### Acceptance criteria

- [x] **AC-1** After install: `user-docs/README.md`, `getting-started/` (installation, project-setup, first-harness), `reference/cli.md`, `guides/multi-agent-workflow.md`, `guides/testing.md`
- [x] **AC-2** `getting-started/installation.md` covers prerequisites, effort, disk ranges, optional extras, updating dependencies, troubleshooting
- [x] **AC-3** Content aligns with PRD §7.4 (not duplicated SDK internals)

### Implementation tasks (build)

- [x] Add / complete template files under `install/templates/user-docs/` (include `guides/testing.md` per [Architecture §13.6](../../architecture/10-operations-and-reference.md#136-testing-playbook); ensure `getting-started/project-setup.md` exists for AC-1)
- [x] Copy skeleton during `client_install.py` — **done in [E1-S03](20-story.md)** (`scaffold_project` copy-if-missing of `install/templates/user-docs/`)
- [x] Expand `installation.md` to full PRD §7.4 topics (prerequisites, effort, disk, extras, updates, troubleshooting)
- [x] Link to Architecture only for “technical behavior” footnotes

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E1-S05 / E1.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/docs/test_user_docs_skeleton.py::test_e1_s05_ac1_template_tree_has_required_paths` |
| AC-1 | `tests/unit/docs/test_user_docs_skeleton.py::test_e1_s05_ac1_live_tree_has_required_paths` |
| AC-2 | `tests/unit/docs/test_user_docs_skeleton.py::test_e1_s05_ac2_installation_covers_prd_74_topics` |
| AC-3 | `tests/unit/docs/test_user_docs_skeleton.py::test_e1_s05_ac3_installation_links_architecture_not_sdk_internals` |

- [x] Every AC row above has a passing test
- [x] `pytest tests/unit/docs/test_user_docs_skeleton.py -v` passes

### Definition of done

- [x] All install table commands from PRD §7.4 appear in installation.md
- [x] Dependency update scenarios documented (post-`git pull`, manual refresh, production redeploy)
- [x] Verification checklist complete; all ACs traced to tests

---
