# Epic E1 — Onboarding and Project Setup

| | |
|---|---|
| **Document** | Epic E1 user stories |
| **File** | `docs/stories/03-epic.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Status** | Backlog |
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

1. **E1-S01** → **E1-S02** — Install script + wrappers
2. **E1-S03** — Scaffolding *(copies E3-S04 templates)*
3. **E1-S04** — `zaumzeug init`
4. **E1-S05** → **E1-S06** — User docs + root README
5. **E1-S07** — CI matrix **last** (validates full Phase 1 stack)

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

- [ ] **AC-1** `install/client_install.py` runs on Windows, macOS, and Linux with Python 3.11+
- [ ] **AC-2** Creates project `.venv` when not present (unless `--skip-venv`)
- [ ] **AC-3** Runs `pip install -e ".[dev]"` successfully per Architecture §4.4
- [ ] **AC-4** Re-running the script is idempotent (no duplicate scaffolding or broken state)
- [ ] **AC-5** Supports flags: `--verify`, `--no-example`, `--skip-venv`, `--cursor-mcp`
- [ ] **AC-6** `--verify` runs `zaumzeug doctor` after install ([E2-S04a](epic-stories/05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks))
- [ ] **AC-7** Uses `pathlib` only — no hardcoded OS path separators ([Architecture §2.5](../architecture/01-overview-and-principles.md#25-cross-platform-portability))

### Implementation tasks (build)

- [ ] Create `install/client_install.py` with OS detection via `platform.system()`
- [ ] Implement venv creation and activation path hints (`Scripts` vs `bin`)
- [ ] Wire editable install: `pip install -e ".[dev]"`
- [ ] Parse and forward CLI flags (`--verify`, `--no-example`, `--skip-venv`, `--cursor-mcp`)
- [ ] Add non-blocking Git missing warning
- [ ] Return non-zero exit code on failure with actionable stderr

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

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/install/test_client_install.py -v` passes

### Definition of done

- [ ] Idempotent re-run verified
- [ ] No secrets written to disk
- [ ] Verification checklist complete; all ACs traced to tests

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

- [ ] **AC-1** `install/client-install.sh` delegates to `client_install.py` with forwarded args
- [ ] **AC-2** `install/client-install.ps1` delegates to `client_install.py` with forwarded args
- [ ] **AC-3** All flags from E1-S01 pass through unchanged
- [ ] **AC-4** Wrappers contain no duplicated install logic

### Implementation tasks (build)

- [ ] Add `install/client-install.sh` (bash)
- [ ] Add `install/client-install.ps1` (PowerShell)
- [ ] Document commands in user-docs (see E1-S05)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E1-S02 / E1.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac1_sh_delegates_to_python` |
| AC-2 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac2_ps1_delegates_to_python` |
| AC-3 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac3_flags_forwarded` |
| AC-4 | `tests/unit/install/test_wrappers.py::test_e1_s02_ac4_no_duplicated_install_logic` |
| AC-1–4 | **shared:** E1-S07 CI matrix invokes wrappers per OS |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/install/test_wrappers.py -v` passes

### Definition of done

- [ ] Wrappers tested on respective OS in CI matrix (E1-S07)
- [ ] Verification checklist complete; all ACs traced to tests

---

## E1-S03 — Project scaffolding on install

| Field | Value |
|---|---|
| **Feature** | E1.3 |
| **Persona** | Harness developer |
| **Priority** | P0 |

### User story

As a **harness developer**, I want the install script to scaffold a working project layout, so that I can run `zaumzeug serve example` immediately after install.

### References

- [PRD E1.3](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.1](../architecture/02-repository-and-layout.md#31-separation-rules)
- [Architecture §3.3 — Harness folder layout](../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- [Architecture §6.6 — Phase 1 config schema](../architecture/05-configuration.md#66-phase-1-config-schema)

### Acceptance criteria

- [ ] **AC-1** Copies `usr-harnesses/example/` from install templates
- [ ] **AC-2** Copies `config/models.yaml`, `.env.example`, `.cursor/mcp.json.example`
- [ ] **AC-3** Updates `.gitignore` for `.venv`, `artifacts/`, `deploy/`, `.env`
- [ ] **AC-4** Never overwrites an existing `.env`
- [ ] **AC-5** `--no-example` skips example harness copy

### Implementation tasks (build)

- [ ] Create `install/templates/` from [E3-S04](../02-epic.md#e3-s04-example-harness-general-research-agent) example harness
- [ ] Implement copy-if-missing / merge rules for `.gitignore`
- [ ] Ensure example harness uses `default_model_id: mock` per §6.6

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E1-S03 / E1.3`.

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

## E1-S04 — `zaumzeug init` command

| Field | Value |
|---|---|
| **Feature** | E1.4 |
| **Persona** | Harness developer |
| **Priority** | P1 |

### User story

As a **harness developer**, I want `zaumzeug init <name>` to scaffold a new harness folder, so that I can add agents beyond the example without copying files by hand.

### References

- [PRD E1.4](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.4](../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)
- [Architecture §8 — CLI](../architecture/06-runtime-and-protocols.md#8-cli-and-runtime-layering)
- [Ideation — YAML examples](../ideation-stage.md) (until `user-docs/reference/` exists)

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

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E1-S04 / E1.4`.

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

## E1-S05 — User documentation skeleton

| Field | Value |
|---|---|
| **Feature** | E1.5 |
| **Persona** | Harness developer |
| **Priority** | P1 |

### User story

As a **harness developer**, I want a structured `user-docs/` tree after install, so that I can follow guides without reading internal design docs.

### References

- [PRD E1.5](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.5](../architecture/02-repository-and-layout.md#35-user-documentation)
- [PRD §7.4 — Full install guide content](../prd.md#74-user-installation-guide-content-for-readme--phase-1)

### Acceptance criteria

- [ ] **AC-1** After install: `user-docs/README.md`, `getting-started/` (installation, project-setup, first-harness), `reference/cli.md`, `guides/multi-agent-workflow.md`, `guides/testing.md`
- [ ] **AC-2** `getting-started/installation.md` covers prerequisites, effort, disk ranges, optional extras, updating dependencies, troubleshooting
- [ ] **AC-3** Content aligns with PRD §7.4 (not duplicated SDK internals)

### Implementation tasks (build)

- [ ] Add template files under `install/templates/user-docs/` (include `guides/testing.md` per [Architecture §13.6](../architecture/10-operations-and-reference.md#136-testing-playbook))
- [ ] Copy skeleton during `client_install.py`
- [ ] Link to Architecture only for “technical behavior” footnotes

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). **Docs-only** — manual checklist mapped to ACs.

| AC | Verification |
|---|---|
| AC-1 | **manual:** post-install tree contains listed paths |
| AC-2 | **manual:** installation.md includes all §7.4 topics (checklist in PRD) |
| AC-3 | **manual:** no SDK internals duplicated; links to Architecture where needed |

- [ ] Manual checklist completed and recorded in PR or story notes
- [ ] Optional future: `tests/unit/docs/test_user_docs_skeleton.py` for path presence

### Definition of done

- [ ] All install table commands from PRD §7.4 appear in installation.md
- [ ] Dependency update scenarios documented (post-`git pull`, manual refresh, production redeploy)
- [ ] Verification checklist complete

---

## E1-S06 — Root README

| Field | Value |
|---|---|
| **Feature** | E1.6 |
| **Persona** | Harness developer · SDK maintainer |
| **Priority** | P1 |

### User story

As a **new contributor**, I want a short root README, so that I understand vision, install, and first commands without reading the full PRD.

### References

- [PRD E1.6](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [PRD §7.4](../prd.md#74-user-installation-guide-content-for-readme--phase-1)
- [PRD §15 — Documentation map](../prd.md#15-documentation-map)

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

Per [Story verification](00-README.md#story-verification-required). **Docs-only** — manual checklist.

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

## E1-S07 — Cross-platform CI matrix

| Field | Value |
|---|---|
| **Feature** | E1.7 |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E1-S01](#e1-s01-cross-platform-install-script) through [E1-S03](#e1-s03-project-scaffolding-on-install) · [E2](../01-epic.md) · [E3](../02-epic.md) complete |

### User story

As an **SDK maintainer**, I want CI to verify install and mock-model serve on Windows, macOS, and Linux, so that cross-platform regressions fail fast.

### References

- [PRD E1.7](../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [PRD §11 — Success metrics](../prd.md#11-success-metrics)
- [Architecture §2.5](../architecture/01-overview-and-principles.md#25-cross-platform-portability)

### Acceptance criteria

- [ ] **AC-1** Workflow runs on `windows-latest`, `ubuntu-latest`, `macos-latest`
- [ ] **AC-2** Each job: `python install/client_install.py --skip-venv --verify` (or full venv + editable install)
- [ ] **AC-3** Each job: `zaumzeug doctor`, `zaumzeug serve example --dry-run`
- [ ] **AC-4** Each job: smoke `zaumzeug serve example` on ephemeral port with **mock model only** (no live API keys)
- [ ] **AC-5** All jobs green on default branch
- [ ] **AC-6** Workflow lives in `.github/workflows/`

### Implementation tasks (build)

- [ ] Add GitHub Actions workflow (e.g. `ci-matrix.yml`)
- [ ] Use ephemeral port binding for serve smoke test
- [ ] Set timeout and fail-fast on first step failure
- [ ] Cache pip where practical

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). **CI orchestration** — workflow steps trace to ACs.

| AC | Verification |
|---|---|
| AC-1 | **CI:** workflow `strategy.matrix.os` includes three runners |
| AC-2 | **CI:** job step runs `client_install.py --skip-venv --verify` |
| AC-3 | **CI:** job steps run `doctor` and `serve example --dry-run` |
| AC-4 | **CI:** job step smoke-tests serve on ephemeral port (mock only) |
| AC-5 | **CI:** all matrix jobs green on default branch |
| AC-6 | **manual:** `.github/workflows/ci-matrix.yml` (or equivalent) exists |

- [ ] Workflow green on all three OS; AC table satisfied

### Definition of done

- [ ] 100% install success rate on CI matrix ([PRD §11](../prd.md#11-success-metrics))
- [ ] Runtime smoke 100% on all three OS jobs
- [ ] Verification checklist complete

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
