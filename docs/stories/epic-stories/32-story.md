# E4-S07 — Rollback to pinned artifact run

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/32-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E4-S07 |
| **Epic** | [E4 — Compile and GEPA Pipeline](../04-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 4 of 8 |
| **Story sequence** | 32 of 63 (global build order) |
| **Source** | Extracted from [`04-epic.md`](../04-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2) · [Architecture](../../architecture.md) |

---

## E4-S07 — Rollback to pinned artifact run

| Field | Value |
|---|---|
| **Feature** | PRD E4 story seed |
| **Persona** | Harness developer |
| **Priority** | P2 |
| **Prerequisites** | [E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts) · [E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest) |

### User story

As a **harness developer**, I want to pin or rollback to a specific `artifacts/<run_id>/`, so that I can recover from a bad compile without re-running GEPA.

### References

- [PRD E4 story seeds](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §5.3 — Artifact layout](../../architecture/04-data-flows.md#53-artifact-layout)


### Implementation resources

**Internal spec**

- [Architecture §5.3 — pinned `run_id` folders](../../architecture/04-data-flows.md#53-artifact-layout)
- Update `agent.yaml` / harness config to point `artifact:` at chosen run directory

### Acceptance criteria

- [ ] **AC-1** Document/manual path: set `agents/<name>/agent.yaml` `runtime.artifact` to `artifacts/<run_id>/` or update `artifacts/current` pointer
- [ ] **AC-2** `zaumzeug doctor` validates pinned run has valid `artifact-manifest.json`
- [ ] **AC-3** Deploy can pin a specific `artifact_run_id` in deploy `manifest.json` ([E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command))
- [ ] **AC-4** Immutable `<run_id>/` directories are never overwritten by new compile

### Implementation tasks (build)

- [ ] Ensure compile writes immutable `artifacts/<run_id>/` and updates `artifacts/current` separately
- [ ] Add doctor check comparing `current` vs explicitly pinned path
- [ ] Document rollback steps in user-docs compile guide

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S07`.

| AC | Test |
|---|---|
| AC-1 | **manual:** user-docs rollback steps; config pin path documented |
| AC-2 | `tests/integration/test_doctor.py::test_e4_s07_ac2_doctor_validates_pinned_manifest` |
| AC-3 | `tests/integration/deploy/test_deploy_pin.py::test_e4_s07_ac3_deploy_manifest_artifact_run_id` *(shared E5-S01)* |
| AC-4 | `tests/integration/compile/test_rollback.py::test_e4_s07_ac4_compile_twice_pin_first_serve_first` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/compile/test_rollback.py -v` passes

### Definition of done

- [ ] Rollback procedure documented; no hand-editing of exported prompt files ([Architecture §15](../../architecture/10-operations-and-reference.md#15-anti-patterns))
- [ ] Verification checklist complete; all ACs traced to tests

---
