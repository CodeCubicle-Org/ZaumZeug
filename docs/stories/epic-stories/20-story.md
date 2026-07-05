# E1-S03 — Project scaffolding on install

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/20-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E1-S03 |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 20 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) |

---

## E1-S03 — Project scaffolding on install

| Field | Value |
|---|---|
| **Feature** | E1.3 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E1-S01](18-story.md#e1-s01-cross-platform-install-script) · [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent) |

### User story

As a **harness developer**, I want the install script to scaffold a working project layout, so that I can run `zaumzeug serve example` immediately after install.

### References

- [PRD E1.3](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.1](../../architecture/02-repository-and-layout.md#31-separation-rules)
- [Architecture §3.3 — Harness folder layout](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- [Architecture §6.6 — Phase 1 config schema](../../architecture/05-configuration.md#66-phase-1-config-schema)


### Implementation resources

**Scaffold sources**

- [Architecture §6.6 — Phase 1 harness layout](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [E3-S04 example templates](14-story.md) — copy from `usr-harnesses/example/`
- [Ideation — full tree reference](../../ideation-stage.md)

### Acceptance criteria

- [ ] **AC-1** Copies `usr-harnesses/example/` from install templates
- [ ] **AC-2** Copies `config/models.yaml`, `.env.example`, `.cursor/mcp.json.example`
- [ ] **AC-3** Updates `.gitignore` for `.venv`, `artifacts/`, `deploy/`, `.env`
- [ ] **AC-4** Never overwrites an existing `.env`
- [ ] **AC-5** `--no-example` skips example harness copy

### Implementation tasks (build)

- [ ] Create `install/templates/` from [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent) example harness
- [ ] Implement copy-if-missing / merge rules for `.gitignore`
- [ ] Ensure example harness uses `default_model_id: mock` per §6.6

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E1-S03 / E1.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac1_copies_example_harness` |
| AC-2 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac2_copies_config_and_env_example` |
| AC-3 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac3_gitignore_entries` |
| AC-4 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac4_preserves_existing_env` |
| AC-5 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac5_no_example_flag_skips_copy` |
| AC-1 | **integration:** `tests/integration/test_serve.py::test_e3_s04_ac3_serve_example_without_env` *(post-scaffold)* |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/install/test_scaffolding.py -v` passes

### Definition of done

- [ ] Fresh install yields runnable `zaumzeug serve example` (mock, no API keys)
- [ ] Re-install does not clobber user `.env`
- [ ] Verification checklist complete; all ACs traced to tests

---
