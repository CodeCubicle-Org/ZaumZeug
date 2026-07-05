# E1-S04 — `zaumzeug init` command

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/21-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E1-S04 |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 21 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) |

---

## E1-S04 — `zaumzeug init` command

| Field | Value |
|---|---|
| **Feature** | E1.4 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E1-S03](20-story.md#e1-s03-project-scaffolding-on-install) · [E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation) |

### User story

As a **harness developer**, I want `zaumzeug init <name>` to scaffold a new harness folder, so that I can add agents beyond the example without copying files by hand.

### References

- [PRD E1.4](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.4](../../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)
- [Architecture §8 — CLI](../../architecture/06-runtime-and-protocols.md#8-cli-and-runtime-layering)
- [Ideation — YAML examples](../../ideation-stage.md) (until `user-docs/reference/` exists)


### Implementation resources

**Internal spec**

- [Architecture §3.3 — harness folder layout](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- Reuse scaffolding logic from [E1-S03](20-story.md) / `client_install.py`

### Acceptance criteria

- [ ] **AC-1** `zaumzeug init <name>` creates `usr-harnesses/<name>/`
- [ ] **AC-2** Generated `harness.yaml` passes Phase 1 Pydantic validation (E2-S01)
- [ ] **AC-3** Template includes minimal valid `runtime`, `serve`, and optional `models` reference
- [ ] **AC-4** Fails fast if harness name already exists (unless `--force` documented)

### Implementation tasks (build)

- [ ] Add `init` subcommand in `src/zaumzeug/cli.py`
- [ ] Create harness template under `install/templates/harness/`
- [ ] Validate name (safe path segment, no traversal)
- [ ] Print next-step hints (`zaumzeug doctor`, `zaumzeug serve`)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E1-S04 / E1.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/cli/test_init.py::test_e1_s04_ac1_creates_harness_folder` |
| AC-2 | `tests/unit/cli/test_init.py::test_e1_s04_ac2_generated_yaml_validates` |
| AC-3 | `tests/unit/cli/test_init.py::test_e1_s04_ac3_template_has_runtime_serve_models` |
| AC-4 | `tests/unit/cli/test_init.py::test_e1_s04_ac4_fails_if_exists_without_force` |
| AC-2 | **integration:** `tests/integration/test_doctor.py::test_e1_s04_init_then_doctor_passes` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/cli/test_init.py -v` passes

### Definition of done

- [ ] Documented in `user-docs/getting-started/project-setup.md`
- [ ] Verification checklist complete; all ACs traced to tests

---
