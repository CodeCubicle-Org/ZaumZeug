# E5-S01 — `zaumzeug deploy` command

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/41-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E5-S01 |
| **Epic** | [E5 — Deploy Packaging](../06-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 6 of 8 |
| **Story sequence** | 41 of 63 (global build order) |
| **Source** | Extracted from [`06-epic.md`](../06-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E5](../../prd.md#epic-e5--deploy-packaging-phase-2) · [Architecture](../../architecture.md) |

---

## E5-S01 — `zaumzeug deploy` command

| Field | Value |
|---|---|
| **Feature** | E5.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts) · [E5-S02](42-story.md#e5-s02-dev-vs-deploy-copy-rules) · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command) |

### User story

As a **harness developer**, I want `zaumzeug deploy <name>` to produce a production bundle, so that I can ship runtime-only files without my dev workspace.

### References

- [PRD E5.1](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.2 — Packager steps](../../architecture/07-deploy-packaging.md#102-packager-steps)
- [Architecture §10.3 — Deploy manifest.json](../../architecture/07-deploy-packaging.md#103-deploy-manifestjson)


### Implementation resources

**Internal spec**

- [Architecture §10.2 — packager steps](../../architecture/07-deploy-packaging.md#102-packager-steps)
- [Architecture §10.3 — `manifest.json` schema](../../architecture/07-deploy-packaging.md#103-deploy-manifestjson)
- [E5-S02 copy rules](42-story.md)

### Acceptance criteria

- [ ] **AC-1** Writes `deploy/<name>/` with stripped yaml, `workflow.yaml`, per-agent runtime files, `docs/workflow-diagram.md`, pinned artifacts
- [ ] **AC-2** Writes `manifest.json` per §10.3 schema
- [ ] **AC-3** Writes `README.deploy.md` with ops instructions
- [ ] **AC-4** Copies `target_install.py` plus `target-install.sh` / `target-install.ps1` into bundle
- [ ] **AC-5** Idempotent — overwrites existing `deploy/<name>/`

### Implementation tasks (build)

- [ ] Implement `src/zaumzeug/deploy/packager.py`
- [ ] Run preflight doctor before pack
- [ ] Apply eval gate (E5-S06)
- [ ] Generate `README.deploy.md` from template

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S01 / E5.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac1_writes_deploy_bundle` |
| AC-2 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac2_manifest_json_schema` |
| AC-3 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac3_readme_deploy_md_present` |
| AC-4 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac4_target_install_scripts_in_bundle` |
| AC-5 | `tests/integration/deploy/test_deploy.py::test_e5_s01_ac5_idempotent_overwrite` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/deploy/test_deploy.py -v -k e5_s01` passes

### Definition of done

- [ ] Deploy after compile story seed passes
- [ ] Bundle is self-describing when copied alone
- [ ] Verification checklist complete; all ACs traced to tests

---
