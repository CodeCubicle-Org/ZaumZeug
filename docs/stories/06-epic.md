# Epic E5 — Deploy Packaging

| | |
|---|---|
| **Document** | Epic E5 user stories |
| **File** | `docs/stories/06-epic.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 (E5-S01 done) |
| **Status** | In progress (E5-S01 + E5-S06 Done; next E5-S02 copy rules) |
| **Build order** | **6 of 8** (after E4 compile + E6-S02 eval for eval gate) |
| **Related** | [PRD](../prd.md) · [Architecture](../architecture.md) · [Index](00-README.md) |

---
| Field | Value |
|---|---|
| **Phase** | 2 |
| **Epic** | E5 |
| **Outcome** | Production bundle separated from dev workspace |
| **Depends on** | [E4](04-epic.md) (artifacts to pin) · [E6-S02](05-epic.md#e6-s02-zaumzeug-eval-command) ✅ (for E5-S06 only) |
| **Blocks** | [E7-S06](07-epic.md#e7-s06-mcp-from-deploy-bundle) |
| **PRD** | [Epic E5](../prd.md#epic-e5--deploy-packaging-phase-2) |
| **Architecture** | [§10 Deploy packager](../architecture/07-deploy-packaging.md#10-deploy-packager) · [§11 #9, #13](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build) |
| **Journey** | [Journey B](../prd.md#72-journey-b--full-lifecycle-phase-23) |
| **Goal** | [G5 — Deploy path](../prd.md#3-goals) |

### Story implementation order (within this epic)

1. **E5-S02** — Copy rules *(can start with packager design)*
2. **E5-S01** — `zaumzeug deploy` ✅ (2026-07-28)
3. **E5-S09a** → **E5-S09b** → **E5-S09c** — Target install *(core, wrappers, verify)*
4. **E5-S03** → **E5-S04** — serve `--deploy` + `HARNESS_ROOT`
5. **E5-S05** → **E5-S08** — Ops docs and platform policy
6. **E5-S07** — Git policy
7. **E5-S06** — Deploy eval gate ✅ (2026-07-28; shipped early with [E6-S03](../05-epic.md#e6-s03-eval-gate-on-deploy); requires [E6-S02](../05-epic.md#e6-s02-zaumzeug-eval-command) ✅)

---

## E5-S01 — `zaumzeug deploy` command

| Field | Value |
|---|---|
| **Feature** | E5.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Status** | Done (2026-07-28) — canonical: [41-story.md](epic-stories/41-story.md) |

### User story

As a **harness developer**, I want `zaumzeug deploy <name>` to produce a production bundle, so that I can ship runtime-only files without my dev workspace.

### References

- [PRD E5.1](../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.2 — Packager steps](../architecture/07-deploy-packaging.md#102-packager-steps)
- [Architecture §10.3 — Deploy manifest.json](../architecture/07-deploy-packaging.md#103-deploy-manifestjson)

### Acceptance criteria

- [x] **AC-1** Writes `deploy/<name>/` with stripped yaml, `workflow.yaml`, per-agent runtime files, `docs/workflow-diagram.md`, pinned artifacts
- [x] **AC-2** Writes `manifest.json` per §10.3 schema
- [x] **AC-3** Writes `README.deploy.md` with ops instructions
- [x] **AC-4** Copies `target_install.py` plus `target-install.sh` / `target-install.ps1` into bundle
- [x] **AC-5** Idempotent — overwrites existing `deploy/<name>/`

### Implementation tasks (build)

- [x] Implement full `src/zaumzeug/deploy/packager.py` copy rules *(module + eval gate exist from E5-S06 / E6-S03)*
- [x] Run preflight doctor before pack
- [x] Apply eval gate (E5-S06) ✅ (2026-07-28)
- [x] Generate `README.deploy.md` from template

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E5-S01 / E5.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac1_writes_deploy_bundle` |
| AC-2 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac2_manifest_json_schema` |
| AC-3 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac3_readme_deploy_md_present` |
| AC-4 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac4_target_install_scripts_in_bundle` |
| AC-5 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac5_idempotent_overwrite` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/deploy/test_deploy.py -v -k e5_s01` passes (7 passed, 0 skipped; 1 deselected)
- [x] `pytest tests/integration/deploy/test_deploy.py -v` passes (8 passed, 0 skipped)

### Definition of done

- [x] Deploy after compile story seed passes
- [x] Bundle is self-describing when copied alone
- [x] Verification checklist complete; all ACs traced to tests

---

## E5-S02 — Dev vs deploy copy rules

| Field | Value |
|---|---|
| **Feature** | E5.2 |
| **Persona** | SDK maintainer |
| **Priority** | P0 |

### User story

As an **SDK maintainer**, I want explicit packager copy rules, so that dev-only files never leak into production bundles.

### References

- [PRD E5.2](../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.1](../architecture/07-deploy-packaging.md#101-dev-vs-deploy)

### Acceptance criteria

- [ ] **AC-1** Excludes `agents/<name>/modules/`, `data/`, `eval/`, `skills/` always
- [ ] **AC-2** Includes per-agent `prompts/`, `tools/`, `hooks.py`, `agents-models.yaml` per [Architecture §10.1](../architecture/07-deploy-packaging.md#101-dev-vs-deploy)
- [ ] **AC-3** Pins per-agent artifact runs under `deploy/<harness>/agents/<name>/artifacts/`
- [ ] **AC-4** Includes `workflow.yaml` and `docs/workflow-diagram.md`
- [ ] **AC-5** Stripped yaml removes `compile`, `eval`, `deploy` sections

### Implementation tasks (build)

- [ ] Implement reference resolver for copy matrix
- [ ] Fail deploy if required runtime path missing

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E5-S02 / E5.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac1_excludes_dev_only_dirs` |
| AC-1 (`eval/` slice) | **shared early:** `tests/unit/deploy/test_copy_rules.py::test_e5_s02_excludes_eval` *(policy landed with [E6-S04](epic-stories/37-story.md), 2026-07-28)* |
| AC-2 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac2_includes_referenced_runtime_assets` |
| AC-3 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac3_pins_per_agent_artifact_runs` |
| AC-4 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac4_includes_workflow_and_diagram` |
| AC-5 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac5_stripped_yaml_sections` |
| AC-1–5 | `tests/integration/deploy/test_deploy_golden.py::test_e5_s02_golden_example_bundle` *(golden snapshot)* |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/deploy/ tests/integration/deploy/test_deploy_golden.py -v -k e5_s02` passes

### Definition of done

- [ ] Golden test: example zaumzeug deploy contents match matrix
- [ ] Verification checklist complete; all ACs traced to tests

**Early slice (E6-S04, 2026-07-28):** `deploy/copy_rules.py` + `test_e5_s02_excludes_eval` assert `eval/` exclusion policy. **Early slice (E5-S01, 2026-07-28):** packager uses strip helpers + exclude policy when writing bundles; full include/pin golden matrix remains this story.
---

## E5-S03 — `zaumzeug serve --deploy`

| Field | Value |
|---|---|
| **Feature** | E5.3 |
| **Persona** | Ops / platform |
| **Priority** | P0 |

### User story

As **ops**, I want `zaumzeug serve <name> --deploy`, so that I run production bundles without the dev `usr-harnesses/` tree.

### References

- [PRD E5.3](../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §8.1 — Source roots](../architecture/06-runtime-and-protocols.md#81-source-roots)

### Acceptance criteria

- [ ] **AC-1** Loads only from `deploy/<name>/`
- [ ] **AC-2** Same OpenAI REST API as dev serve
- [ ] **AC-3** Fails if deploy folder missing or invalid manifest
- [ ] **AC-4** Works after target_install on clean venv without `usr-harnesses/`

### Implementation tasks (build)

- [ ] Add `--deploy` flag to serve command
- [ ] Resolve paths relative to `deploy/<name>/`

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E5-S03 / E5.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac1_loads_deploy_root_only` |
| AC-2 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac2_openai_rest_parity` |
| AC-3 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac3_fails_missing_manifest` |
| AC-4 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac4_after_target_install_clean_venv` |
| AC-1–4 | **shared:** E5-S08 Linux CI deploy → serve --deploy smoke |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/deploy/test_serve_deploy.py -v` passes

### Definition of done

- [ ] Documented in `README.deploy.md` and user-docs
- [ ] Verification checklist complete; all ACs traced to tests

---

## E5-S04 — `HARNESS_ROOT=deploy` environment override

| Field | Value |
|---|---|
| **Feature** | E5.4 |
| **Persona** | Ops / platform |
| **Priority** | P1 |

### User story

As **ops**, I want `HARNESS_ROOT=deploy`, so that serve/mcp/acp default to production roots in container or systemd environments.

### References

- [PRD E5.4](../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §2.5 — Env over convention](../architecture/01-overview-and-principles.md#25-cross-platform-portability)

### Acceptance criteria

- [ ] **AC-1** `HARNESS_ROOT=deploy` forces deploy root for serve, mcp, acp
- [ ] **AC-2** Default dev root remains `usr-harnesses/`
- [ ] **AC-3** Documented in deploy README and CLI reference

### Implementation tasks (build)

- [ ] Centralize root resolution in config loader

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E5-S04 / E5.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/deploy/test_harness_root.py::test_e5_s04_ac1_env_forces_deploy_root` |
| AC-2 | `tests/unit/deploy/test_harness_root.py::test_e5_s04_ac2_default_usr_harnesses` |
| AC-3 | **manual:** README.deploy.md and CLI reference document env var |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/deploy/test_harness_root.py -v` passes

### Definition of done

- [ ] No hardcoded `usr-harnesses` in serve runner when env set
- [ ] Verification checklist complete; all ACs traced to tests

---

## E5-S05 — Target ship workflow documentation

| Field | Value |
|---|---|
| **Feature** | E5.5 |
| **Persona** | Ops / platform · Harness developer |
| **Priority** | P0 |

### User story

As **ops**, I want a documented copy → install → serve workflow, so that I can deploy to a clean server without DSPy or GEPA on the target.

### References

- [PRD E5.5](../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.5 — Production dependencies](../architecture/07-deploy-packaging.md#105-production-server-dependencies)
- [Architecture §10.6 — Platform targets](../architecture/07-deploy-packaging.md#106-deploy-platform-targets)

### Acceptance criteria

- [ ] **AC-1** Documented path: copy `deploy/<name>/` → `target_install` → create `.env` → `zaumzeug serve --deploy`
- [ ] **AC-2** Target installs runtime deps only (`pip install zaumzeug`)
- [ ] **AC-3** No DSPy, GEPA, or DeepEval on production server by default
- [ ] **AC-4** Python 3.11+ must pre-exist on target
- [ ] **AC-5** `.env` never shipped inside bundle

### Implementation tasks (build)

- [ ] Author workflow in `README.deploy.md` and user-docs guide
- [ ] Include Win/macOS/Linux invocation table
- [ ] Link from root README production note (abbreviated)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). **Docs + integration** — manual checklist plus E5-S09/E5-S03 tests.

| AC | Verification |
|---|---|
| AC-1 | **manual:** README.deploy.md workflow steps; **integration:** E5-S03 AC-4 |
| AC-2 | **integration:** `tests/integration/deploy/test_target_install.py::test_e5_s05_ac2_runtime_only_install` |
| AC-3 | `tests/integration/deploy/test_target_install.py::test_e5_s05_ac3_no_dspy_gepa_deepeval` |
| AC-4 | **manual:** docs state Python 3.11+ prerequisite |
| AC-5 | `tests/integration/deploy/test_deploy.py::test_e5_s05_ac5_no_env_in_bundle` |

- [ ] Manual checklist completed; integration tests pass

### Definition of done

- [ ] Happy path validated on clean Linux target (Phase 2+ CI)
- [ ] Verification checklist complete

---

## E5-S06 — Deploy eval gate

| Field | Value |
|---|---|
| **Feature** | E5.6 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Done (2026-07-28) — shipped early with E6-S03; canonical: [46-story.md](epic-stories/46-story.md) |
| **Prerequisites** | [E5-S01](#e5-s01-zaumzeug-deploy-command) ✅ · [E6-S02](../05-epic.md#e6-s02-zaumzeug-eval-command) ✅ |

### User story

As a **harness developer**, I want configurable eval gates on deploy, so that I can optionally block shipping when regression tests fail.

### References

- [PRD E5.6](../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §6.4 — Deploy eval gate](../architecture/05-configuration.md#64-deploy-eval-gate)
- [E6-S02 — zaumzeug eval](../05-epic.md#e6-s02-zaumzeug-eval-command)

### Acceptance criteria

- [x] **AC-1** `deploy.eval_gate`: `skip` | `warn` | `block` behaves per §6.4
- [x] **AC-2** CLI override: `zaumzeug deploy <name> --eval-gate block`
- [x] **AC-3** If no `eval` section, `block` is no-op
- [x] **AC-4** `warn` continues deploy after printing failures

### Implementation tasks (build)

- [x] Add eval gate to deploy packager pre-step
- [x] Wire to `zaumzeug eval` when configured

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E5-S06 / E5.6` *(shared E6-S03)*.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/deploy/test_eval_gate.py::test_e5_s06_ac1_skip_warn_block_behaviors` |
| AC-2 | `tests/unit/deploy/test_eval_gate.py::test_e5_s06_ac2_cli_override_eval_gate` |
| AC-3 | `tests/unit/deploy/test_eval_gate.py::test_e5_s06_ac3_block_noop_without_eval_section` |
| AC-4 | `tests/unit/deploy/test_eval_gate.py::test_e5_s06_ac4_warn_continues_after_failures` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/deploy/test_eval_gate.py -v` passes

### Definition of done

- [x] Covered by E6-S03 cross-reference
- [x] Verification checklist complete; all ACs traced to tests

---

## E5-S07 — Deploy git policy

| Field | Value |
|---|---|
| **Feature** | E5.7 |
| **Persona** | SDK maintainer |
| **Priority** | P2 |

### User story

As an **SDK maintainer**, I want clear git policy for deploy artifacts, so that teams choose between local-only bundles and audited releases.

### References

- [PRD E5.7](../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.4](../architecture/07-deploy-packaging.md#104-git-and-gitignore)

### Acceptance criteria

- [ ] **AC-1** Default `.gitignore` includes `deploy/` and `usr-harnesses/*/artifacts/`
- [ ] **AC-2** Documented option to commit `deploy/<name>/` for release tags
- [ ] **AC-3** CI may build and upload bundle as workflow artifact

### Implementation tasks (build)

- [ ] Ensure install scaffolding sets `.gitignore` entries (E1-S03)
- [ ] Document release commit policy in maintainer docs

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E5-S07 / E5.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/install/test_scaffolding.py::test_e5_s07_ac1_gitignore_deploy_and_artifacts` *(extends E1-S03)* |
| AC-2 | **manual:** maintainer docs describe release commit option |
| AC-3 | **manual:** CI workflow documents artifact upload (when added) |

- [ ] Every AC row above has a passing test or documented manual exception

### Definition of done

- [ ] No accidental commit of `.env` in examples
- [ ] Verification checklist complete

---

## E5-S08 — Deploy platform policy

| Field | Value |
|---|---|
| **Feature** | E5.8 |
| **Persona** | Ops / platform |
| **Priority** | P1 |

### User story

As **ops**, I want a documented platform matrix, so that I know Linux is the primary production target while dev works everywhere.

### References

- [PRD E5.8](../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.6](../architecture/07-deploy-packaging.md#106-deploy-platform-targets)
- [PRD §14 — Cross-platform table](../prd.md#cross-platform-support)

### Acceptance criteria

- [ ] **AC-1** `README.deploy.md` states Linux-first production (VM, bare metal, Docker/K8s)
- [ ] **AC-2** Bundle is OS-neutral Python + pinned artifacts
- [ ] **AC-3** Windows/macOS production serve supported best-effort, not CI-gated in v1
- [ ] **AC-4** Optional container path referenced (E8-S05)

### Implementation tasks (build)

- [ ] Author platform matrix in `README.deploy.md`
- [ ] Phase 2+ Linux CI: deploy → serve --deploy smoke

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required).

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

## E5-S09 — Target runtime install *(split into sub-stories)*

> **Canonical story files:** [E5-S09a — core script](epic-stories/49.1-story.md) · [E5-S09b — wrappers](epic-stories/49.2-story.md) · [E5-S09c — verify](epic-stories/49.3-story.md)

See epic-stories for full AC → test mapping. `--verify` depends on [E2-S04c](../01-epic.md#e2-s04--zaumzeug-doctor-split-into-sub-stories) ✅ and [E2-S05](../01-epic.md#e2-s05-dry-run-on-serve) ✅ ([E5-S09c](epic-stories/49.3-story.md#e5-s09c-target-install-verify-integration) wires both in `target_install.py`). CI matrix dry-run ([E1-S07](../03-epic.md#e1-s07-cross-platform-ci-matrix) ✅, 2026-07-22) closed [E2-S05 DoD](epic-stories/06-story.md#definition-of-done) via AC-3.
