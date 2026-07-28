# E5-S05 — Target ship workflow documentation

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/45-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E5-S05 |
| **Status** | Done |
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
| **Prerequisites** | [E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy) ✅ (2026-07-28) · [E5-S09c](49.3-story.md#e5-s09c-target-install-verify-integration) *(full `--verify` automation later; stub + docs ship now)* |

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

**Docs / code**

- `install/templates/deploy/README.deploy.md` — ship workflow + OS table (rendered into every bundle)
- `user-docs/guides/deploy.md` (+ install template mirror)
- Root `README.md` production note (abbreviated)
- `install/target_install.py` — next-steps print runtime-only contract (full install → E5-S09)

### Acceptance criteria

- [x] **AC-1** Documented path: copy `deploy/<name>/` → `target_install` → create `.env` → `zaumzeug serve --deploy`
- [x] **AC-2** Target installs runtime deps only (`pip install zaumzeug`)
- [x] **AC-3** No DSPy, GEPA, or DeepEval on production server by default
- [x] **AC-4** Python 3.11+ must pre-exist on target
- [x] **AC-5** `.env` never shipped inside bundle

### Implementation tasks (build)

- [x] Author workflow in `README.deploy.md` and user-docs guide
- [x] Include Win/macOS/Linux invocation table
- [x] Link from root README production note (abbreviated)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **Docs + integration** — manual checklist plus E5-S09/E5-S03 tests. Test file header: `# Story: E5-S05 / E5.5`.

| AC | Verification |
|---|---|
| AC-1 | **manual:** README.deploy.md + `user-docs/guides/deploy.md` workflow steps; **integration:** E5-S03 AC-4 + `test_e5_s05_docs_ship_workflow_steps` / `test_e5_s05_bundled_readme_renders_ship_workflow` |
| AC-2 | **integration:** `tests/integration/deploy/test_target_install.py::test_e5_s05_ac2_runtime_only_install` |
| AC-3 | `tests/integration/deploy/test_target_install.py::test_e5_s05_ac3_no_dspy_gepa_deepeval` |
| AC-4 | **manual + docs test:** docs state Python 3.11+ prerequisite (`test_e5_s05_docs_ship_workflow_steps`) |
| AC-5 | `tests/integration/deploy/test_deploy.py::test_e5_s05_ac5_no_env_in_bundle` |

- [x] Manual checklist completed; integration tests pass
- [x] `pytest tests/integration/deploy/test_target_install.py tests/integration/deploy/test_deploy.py::test_e5_s05_ac5_no_env_in_bundle -v` passes (5 passed, 0 skipped)

### Definition of done

- [x] Happy path documented; clean-bundle serve covered by E5-S03 AC-4; Linux CI smoke remains [E5-S08](48-story.md)
- [x] Verification checklist complete; all ACs traced to tests or documented manual exceptions

### Implementation notes (2026-07-28)

- Ship path authored in bundle `README.deploy.md` template and [user-docs/guides/deploy.md](../../../user-docs/guides/deploy.md); root README production note links the guide.
- Runtime-only contract asserted via pyproject core deps + `target_install` / docs wording; `.env` exclusion covered by packager integration test (explicit plant of secrets under project + harness).
- Full automated `pip install` / venv / `--verify` remains [E5-S09](49.1-story.md); stub already prints the documented next steps.
---
