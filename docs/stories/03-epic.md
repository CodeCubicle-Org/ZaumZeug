# Epic E1 — Onboarding and Project Setup

| | |
|---|---|
| **Document** | Epic E1 user stories |
| **File** | `docs/stories/03-epic.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-22 (E1-S07 done) |
| **Status** | Phase 1 complete (E1-S01–S07); E1-S08 blocked |
| **Build order** | **3 of 8** (after E2 + E3 — install/CI need working SDK) |
| **Related** | [PRD](../prd.md) · [Architecture](../architecture.md) · [Index](00-README.md) |

---
| Field | Value |
|---|---|
| **Phase** | 1 |
| **Epic** | E1 |
| **Outcome** | Developer clones repo and runs a harness in one session |
| **Depends on** | [E2](01-epic.md) · [E3](02-epic.md) (doctor, serve, example templates must exist) |
| **Blocks** | — (completes Phase 1 milestone) |
| **PRD** | [Epic E1](../prd.md#epic-e1--onboarding-and-project-setup-phase-1) |
| **Architecture** | [§3 Repository structure](../architecture/02-repository-and-layout.md#3-repository-structure) · [§3.4 Install scripts](../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target) · [§4.4 pyproject.toml](../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub) · [§11 #13 install](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build) |
| **Journey** | [Journey A — Config-only harness](../prd.md#71-journey-a--config-only-harness-phase-1) |
| **Success metrics** | [§11 — Time to first serve < 15 min](../prd.md#11-success-metrics) |

### Story implementation order (within this epic)

1. **E1-S01** → **E1-S02** — Install script + wrappers ✅
2. **E1-S03** — Scaffolding *(copies E3-S04 templates)* ✅
3. **E1-S04** — `zaumzeug init` ✅
4. **E1-S05** ✅ → **E1-S06** ✅ — User docs + CONTRIBUTING.md
5. **E1-S07** — CI matrix **last** (validates full Phase 1 stack) ✅
6. **E1-S08** — Future: `zaumzeug install-project` *(blocked)*

---

## E1-S01 — Cross-platform install script

| Field | Value |
|---|---|
| **Feature** | E1.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |

### User story

As a **harness developer**, I want a single Python install script that works on Windows, macOS, and Linux, so that I can onboard in one command without manual dependency juggling.

### References

- [PRD E1.1](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.4](../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)
- [Architecture §4.4](../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)
- [PRD §7.4 — Install commands](../prd.md#74-user-installation-guide-content-for-readme--phase-1)

### Acceptance criteria

- [x] **AC-1** `install/client_install.py` runs on Windows, macOS, and Linux with Python 3.11+
- [x] **AC-2** Creates project `.venv` when not present (unless `--skip-venv`)
- [x] **AC-3** Runs `pip install -e ".[dev]"` successfully per Architecture §4.4
- [x] **AC-4** Re-running the script is idempotent (no duplicate scaffolding or broken state)
- [x] **AC-5** Supports flags: `--verify`, `--no-example`, `--skip-venv`, `--cursor-mcp`
- [x] **AC-6** `--verify` runs `zaumzeug doctor` after install ([E2-S04a](epic-stories/05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks))
- [x] **AC-7** Uses `pathlib` only — no hardcoded OS path separators ([Architecture §2.5](../architecture/01-overview-and-principles.md#25-cross-platform-portability))

### Implementation tasks (build)

- [x] Create `install/client_install.py` with OS detection via `platform.system()`
- [x] Implement venv creation and activation path hints (`Scripts` vs `bin`)
- [x] Wire editable install: `pip install -e ".[dev]"`
- [x] Parse and forward CLI flags (`--verify`, `--no-example`, `--skip-venv`, `--cursor-mcp`)
- [x] Add non-blocking Git missing warning
- [x] Return non-zero exit code on failure with actionable stderr

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E1-S01 / E1.1`.

| AC | Test |
|---|---|
| AC-1 | **shared:** [E1-S07](#e1-s07-cross-platform-ci-matrix) matrix runs script on three OS |
| AC-2 | `tests/unit/install/test_client_install.py::test_e1_s01_ac2_creates_venv_when_missing` |
| AC-3 | `tests/unit/install/test_client_install.py::test_e1_s01_ac3_editable_dev_install` |
| AC-4 | `tests/unit/install/test_client_install.py::test_e1_s01_ac4_idempotent_rerun` |
| AC-5 | `tests/unit/install/test_client_install.py::test_e1_s01_ac5_cli_flags_parsed` |
| AC-6 | `tests/unit/install/test_client_install.py::test_e1_s01_ac6_verify_invokes_doctor` |
| AC-7 | `tests/unit/install/test_client_install.py::test_e1_s01_ac7_pathlib_no_hardcoded_separators` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/install/test_client_install.py -v` passes

### Definition of done

- [x] Idempotent re-run verified
- [x] No secrets written to disk
- [x] Verification checklist complete; all ACs traced to tests

---

## E1-S02 — Install shell wrappers

| Field | Value |
|---|---|
| **Feature** | E1.2 |
| **Persona** | Harness developer |
| **Priority** | P0 |

### User story

As a **harness developer**, I want OS-specific install wrappers that delegate to the Python script, so that I can run familiar one-liners on my platform.

### References

- [PRD E1.2](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [PRD §7.4 — Install command table](../prd.md#74-user-installation-guide-content-for-readme--phase-1)

### Acceptance criteria

- [x] **AC-1** `install/client-install.sh` delegates to `client_install.py` with forwarded args
- [x] **AC-2** `install/client-install.ps1` delegates to `client_install.py` with forwarded args
- [x] **AC-3** All flags from E1-S01 pass through unchanged
- [x] **AC-4** Wrappers contain no duplicated install logic

### Implementation tasks (build)

- [x] Add `install/client-install.sh` (bash)
- [x] Add `install/client-install.ps1` (PowerShell)
- [x] Document commands in user-docs (see E1-S05) — command table + full §7.4 guide in `user-docs/getting-started/installation.md` (**Done** E1-S05)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E1-S02 / E1.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac1_sh_delegates_to_python` |
| AC-2 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac2_ps1_delegates_to_python` |
| AC-3 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac3_flags_forwarded` |
| AC-4 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac4_no_duplicated_install_logic` |
| AC-1–4 | **shared:** [E1-S07](#e1-s07-cross-platform-ci-matrix) CI matrix invokes wrappers per OS |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/install/test_wrappers.py -v` passes

### Definition of done

- [x] Wrappers tested on respective OS in CI matrix *(closed by [E1-S07](#e1-s07-cross-platform-ci-matrix) — Done 2026-07-22)*
- [x] Verification checklist complete; all ACs traced to tests

---

## E1-S03 — Project scaffolding on install

| Field | Value |
|---|---|
| **Feature** | E1.3 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Status** | Done (2026-07-22) |

### User story

As a **harness developer**, I want the install script to scaffold a working project layout, so that I can run `zaumzeug serve example` immediately after install.

### References

- [PRD E1.3](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.1](../architecture/02-repository-and-layout.md#31-separation-rules)
- [Architecture §3.3 — Harness folder layout](../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- [Architecture §6.6 — Phase 1 config schema](../architecture/05-configuration.md#66-phase-1-config-schema)

### Acceptance criteria

- [x] **AC-1** Copies `usr-harnesses/example/` from install templates
- [x] **AC-2** Copies `config/models.yaml`, `.env.example`, `.cursor/mcp.json.example`
- [x] **AC-3** Updates `.gitignore` for `.venv`, `artifacts/`, `deploy/`, `.env`
- [x] **AC-4** Never overwrites an existing `.env`
- [x] **AC-5** `--no-example` skips example harness copy

### Implementation tasks (build)

- [x] Create `install/templates/` from [E3-S04](../02-epic.md#e3-s04-example-harness-general-research-agent) example harness
- [x] Implement copy-if-missing / merge rules for `.gitignore`
- [x] Ensure example harness uses `default_model_id: mock` per §6.6

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E1-S03 / E1.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac1_copies_example_harness` |
| AC-2 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac2_copies_config_and_env_example` |
| AC-3 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac3_gitignore_entries` |
| AC-4 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac4_preserves_existing_env` |
| AC-5 | `tests/unit/install/test_scaffolding.py::test_e1_s03_ac5_no_example_flag_skips_copy` |
| AC-1 | **integration:** `tests/integration/test_serve.py::test_e3_s04_ac4_serve_example_without_env` *(post-scaffold)* |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/install/test_scaffolding.py -v` passes

### Definition of done

- [x] Fresh install yields runnable `zaumzeug serve example` (mock, no API keys)
- [x] Re-install does not clobber user `.env`
- [x] Verification checklist complete; all ACs traced to tests

---

## E1-S04 — `zaumzeug init` command

| Field | Value |
|---|---|
| **Feature** | E1.4 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Done (2026-07-22) |

### User story

As a **harness developer**, I want `zaumzeug init <name>` to scaffold a new harness folder, so that I can add agents beyond the example without copying files by hand.

### References

- [PRD E1.4](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.4](../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)
- [Architecture §8 — CLI](../architecture/06-runtime-and-protocols.md#8-cli-and-runtime-layering)
- [Ideation — YAML examples](../ideation-stage.md) (until `user-docs/reference/` exists)

### Acceptance criteria

- [x] **AC-1** `zaumzeug init <name>` creates `usr-harnesses/<name>/`
- [x] **AC-2** Generated `harness.yaml` passes Phase 1 Pydantic validation (E2-S01)
- [x] **AC-3** Template includes minimal valid `runtime`, `serve`, and optional `models` reference
- [x] **AC-4** Fails fast if harness name already exists (unless `--force` documented)

### Implementation tasks (build)

- [x] Add `init` subcommand in `src/zaumzeug/cli.py`
- [x] Create harness template under `install/templates/harness/`
- [x] Validate name (safe path segment, no traversal)
- [x] Print next-step hints (`zaumzeug doctor`, `zaumzeug serve`)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E1-S04 / E1.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/cli/test_init.py::test_e1_s04_ac1_creates_harness_folder` |
| AC-2 | `tests/unit/cli/test_init.py::test_e1_s04_ac2_generated_yaml_validates` |
| AC-3 | `tests/unit/cli/test_init.py::test_e1_s04_ac3_template_has_runtime_serve_models` |
| AC-4 | `tests/unit/cli/test_init.py::test_e1_s04_ac4_fails_if_exists_without_force` |
| AC-2 | **integration:** `tests/integration/test_doctor.py::test_e1_s04_init_then_doctor_passes` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/cli/test_init.py -v` passes

### Definition of done

- [x] Documented in `user-docs/getting-started/project-setup.md`
- [x] Verification checklist complete; all ACs traced to tests

---

## E1-S05 — User documentation skeleton

| Field | Value |
|---|---|
| **Feature** | E1.5 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Done (2026-07-22) |

### User story

As a **harness developer**, I want a structured `user-docs/` tree after install, so that I can follow guides without reading internal design docs.

### References

- [PRD E1.5](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.5](../architecture/02-repository-and-layout.md#35-user-documentation)
- [PRD §7.4 — Full install guide content](../prd.md#74-user-installation-guide-content-for-readme--phase-1)

### Acceptance criteria

- [x] **AC-1** After install: `user-docs/README.md`, `getting-started/` (installation, project-setup, first-harness), `reference/cli.md`, `guides/multi-agent-workflow.md`, `guides/testing.md`
- [x] **AC-2** `getting-started/installation.md` covers prerequisites, effort, disk ranges, optional extras, updating dependencies, troubleshooting
- [x] **AC-3** Content aligns with PRD §7.4 (not duplicated SDK internals)

### Implementation tasks (build)

- [x] Add / complete template files under `install/templates/user-docs/` (include `guides/testing.md` per [Architecture §13.6](../architecture/10-operations-and-reference.md#136-testing-playbook); ensure `getting-started/project-setup.md` exists for AC-1)
- [x] Copy skeleton during `client_install.py` — **done in [E1-S03](#e1-s03-project-scaffolding-on-install)** (`scaffold_project` copy-if-missing of `install/templates/user-docs/`)
- [x] Expand `installation.md` to full PRD §7.4 topics (prerequisites, effort, disk, extras, updates, troubleshooting)
- [x] Link to Architecture only for “technical behavior” footnotes

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E1-S05 / E1.5`.

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

## E1-S06 — Root README

| Field | Value |
|---|---|
| **Feature** | E1.6 |
| **Persona** | Harness developer · SDK maintainer |
| **Priority** | P1 |
| **Status** | Done (2026-07-22) — delivered as [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |

### User story

As a **new contributor**, I want a short root README, so that I understand vision, install, and first commands without reading the full PRD.

### References

- [PRD E1.6](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [PRD §7.4](../prd.md#74-user-installation-guide-content-for-readme--phase-1)
- [PRD §15 — Documentation map](../prd.md#15-documentation-map)

### Acceptance criteria

- [x] **AC-1** Short new-contributor guide created in Phase 1 alongside install path — [`CONTRIBUTING.md`](../../CONTRIBUTING.md) (product `README.md` unchanged)
- [x] **AC-2** Includes vision one-liner, install command table, mock-first quick start
- [x] **AC-3** States < 15 min target and ~1–2.5 GB dev venv planning range
- [x] **AC-4** Includes updating-dependencies summary with post-`git pull` commands
- [x] **AC-5** Links to `user-docs/getting-started/installation.md` for depth — not a duplicate

### Implementation tasks (build)

- [x] Author root `CONTRIBUTING.md` from PRD §7.4 checklist
- [x] Add abbreviated project layout (`usr-harnesses/`, `deploy/`, `config/`)
- [x] Cross-link `docs/prd.md` and `docs/architecture.md` for maintainers only

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E1-S06 / E1.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac1_contributing_exists` |
| AC-2 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac2_vision_install_mock_quick_start` |
| AC-3 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac3_time_and_disk_ranges` |
| AC-4 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac4_updating_dependencies_after_pull` |
| AC-5 | `tests/unit/docs/test_contributing_guide.py::test_e1_s06_ac5_links_installation_not_full_duplicate` |

- [x] Every AC row above has a passing test
- [x] `pytest tests/unit/docs/test_contributing_guide.py -v` passes

### Definition of done

- [x] Guide review: no contradiction with PRD §11 success metrics
- [x] Verification checklist complete

---

## E1-S07 — Cross-platform CI matrix

| Field | Value |
|---|---|
| **Feature** | E1.7 |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E1-S01](#e1-s01-cross-platform-install-script) through [E1-S03](#e1-s03-project-scaffolding-on-install) · [E2](../01-epic.md) · [E2-S05](epic-stories/06-story.md#e2-s05-dry-run-on-serve) ✅ · [E3](../02-epic.md) complete |
| **Status** | Done (2026-07-22) — see [24-story.md](epic-stories/24-story.md) |
| **Closes open from** | [E1-S02 DoD](epic-stories/19-story.md#definition-of-done) *Wrappers tested on respective OS in CI matrix* · [E3-S02 AC-6 · AC-7](epic-stories/13-story.md#acceptance-criteria) · [E3-S07 DoD](epic-stories/16-story.md#definition-of-done) *Green on all three OS in CI matrix* |

### User story

As an **SDK maintainer**, I want CI to verify install and mock-model serve on Windows, macOS, and Linux, so that cross-platform regressions fail fast.

### References

- [PRD E1.7](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [PRD §11 — Success metrics](../prd.md#11-success-metrics)
- [Architecture §2.5](../architecture/01-overview-and-principles.md#25-cross-platform-portability)
- [E3-S07 — OpenAI REST contract](epic-stories/16-story.md#e3-s07-openai-rest-contract-tests) — **Done** (2026-07-21); matrix runs `pytest tests/integration/test_openai_contract.py`
- [E1-S02 — Install shell wrappers](epic-stories/19-story.md#e1-s02-install-shell-wrappers) — **Done** (2026-07-22); closes [E1-S02 DoD](epic-stories/19-story.md#definition-of-done) via per-OS wrappers in matrix

### Acceptance criteria

- [x] **AC-1** Workflow runs on `windows-latest`, `ubuntu-latest`, `macos-latest`
- [x] **AC-2** Each job: OS install wrappers with `--skip-venv --verify` (delegates to `client_install.py`)
- [x] **AC-3** Each job: `zaumzeug doctor`, `zaumzeug serve example --dry-run`
- [x] **AC-4** Each job: smoke `zaumzeug serve example` on ephemeral port with **mock model only** (no live API keys)
- [x] **AC-5** Workflow wired for default-branch green (matrix + fail-fast)
- [x] **AC-6** Workflow lives in `.github/workflows/`

### Implementation tasks (build)

- [x] Add GitHub Actions workflow (`.github/workflows/ci-matrix.yml`)
- [x] Use ephemeral port binding for serve smoke test (`install/ci_serve_smoke.py`)
- [x] Run `pytest tests/integration/test_openai_contract.py` on each matrix OS (closes [E3-S07 DoD](epic-stories/16-story.md#definition-of-done))
- [x] Set timeout and fail-fast on first step failure
- [x] Cache pip where practical

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). **CI orchestration** — workflow steps trace to ACs. Full detail: [24-story.md](epic-stories/24-story.md#verification-after-build).

| AC | Verification |
|---|---|
| AC-1 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac1_three_os_matrix` |
| AC-2 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac2_install_via_wrappers_or_client_install` |
| AC-3 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac3_doctor_and_serve_dry_run` |
| AC-4 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac4_serve_smoke_ephemeral` |
| AC-5 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac5_no_live_llm_in_default_ci` · **CI:** matrix on push/PR |
| AC-6 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac6_workflow_exists` |

- [x] Workflow defined for all three OS; AC table satisfied

### Definition of done

- [x] Install + verify path wired on CI matrix ([PRD §11](../prd.md#11-success-metrics))
- [x] Runtime smoke wired on all three OS jobs
- [x] Verification checklist complete
- [x] [E2-S05](epic-stories/06-story.md#definition-of-done) DoD *Called by E1-S07 CI matrix* checked off
- [x] [E3-S02 AC-6 · AC-7](epic-stories/13-story.md#acceptance-criteria) checked off
- [x] [E3-S07 DoD](epic-stories/16-story.md#definition-of-done) *Green on all three OS in CI matrix* checked off
- [x] [E1-S02 DoD](epic-stories/19-story.md#definition-of-done) *Wrappers tested on respective OS in CI matrix* checked off

---

## E1-S08 — Future: `zaumzeug install-project` (blocked)

| Field | Value |
|---|---|
| **Feature** | E1 future (open #3) |
| **Persona** | PyPI consumer |
| **Priority** | Deferred |

### User story

As a **PyPI consumer**, I want to scaffold harness folders in an arbitrary project cwd, so that I do not need a full SDK repo clone.

### References

- [PRD open decision #4](../prd.md#12-open-decisions-blockers-for-some-stories)
- [PRD §9 — Future commands](../prd.md#9-cli-surface-epic-mapping)

### Blocker

- [ ] Resolve `install/` vs `zaumzeug install-project` for PyPI consumers before implementation

### Implementation tasks (when unblocked)

- [ ] Reuse `client_install.py` logic without editable repo install
- [ ] Scaffold `usr-harnesses/`, `user-docs/`, `.env` in consumer cwd

### Verification (when unblocked)

Apply [Story verification](00-README.md#story-verification-required) with AC labels and `tests/unit/install/test_install_project.py` mapping when story is split from blocker.

---
