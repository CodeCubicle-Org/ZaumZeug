# E5-S02 — Dev vs deploy copy rules

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/42-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E5-S02 |
| **Status** | Done |
| **Epic** | [E5 — Deploy Packaging](../06-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 6 of 8 |
| **Story sequence** | 42 of 63 (global build order) |
| **Source** | Extracted from [`06-epic.md`](../06-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E5](../../prd.md#epic-e5--deploy-packaging-phase-2) · [Architecture](../../architecture.md) |

---

## E5-S02 — Dev vs deploy copy rules

| Field | Value |
|---|---|
| **Feature** | E5.2 |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) ✅ · [E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest) ✅ (2026-07-28) |

### User story

As an **SDK maintainer**, I want explicit packager copy rules, so that dev-only files never leak into production bundles.

### References

- [PRD E5.2](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.1](../../architecture/07-deploy-packaging.md#101-dev-vs-deploy)


### Implementation resources

**Internal spec**

- [Architecture §10.1 — dev vs deploy copy matrix](../../architecture/07-deploy-packaging.md#101-dev-vs-deploy)
- Golden tests: `tests/unit/deploy/test_copy_rules.py` (shared with E7-S02, E8-S01)

### Acceptance criteria

- [x] **AC-1** Excludes `agents/<name>/modules/`, `data/`, `eval/`, `skills/` always
- [x] **AC-2** Includes per-agent `prompts/`, `tools/`, `hooks.py`, `agents-models.yaml` per [Architecture §10.1](../../architecture/07-deploy-packaging.md#101-dev-vs-deploy)
- [x] **AC-3** Pins per-agent artifact runs under `deploy/<harness>/agents/<name>/artifacts/`
- [x] **AC-4** Includes `workflow.yaml` and `docs/workflow-diagram.md`
- [x] **AC-5** Stripped yaml removes `compile`, `eval`, `deploy` sections

### Implementation tasks (build)

- [x] Implement reference resolver for copy matrix
- [x] Fail deploy if required runtime path missing

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S02 / E5.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac1_excludes_dev_only_dirs` |
| AC-1 (`eval/` slice) | **shared early:** `tests/unit/deploy/test_copy_rules.py::test_e5_s02_excludes_eval` *(policy landed with [E6-S04](37-story.md), 2026-07-28)* |
| AC-2 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac2_includes_referenced_runtime_assets` |
| AC-3 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac3_pins_per_agent_artifact_runs` |
| AC-4 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac4_includes_workflow_and_diagram` |
| AC-5 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac5_stripped_yaml_sections` |
| AC-1–5 | `tests/integration/deploy/test_deploy_golden.py::test_e5_s02_golden_example_bundle` *(golden snapshot)* |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/deploy/ tests/integration/deploy/test_deploy_golden.py -v -k e5_s02` passes (13 passed, 0 skipped; 9 deselected)

### Definition of done

- [x] Golden test: example zaumzeug deploy contents match matrix
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- `deploy/copy_rules.py`: `resolve_deploy_copy_plan` / `assert_required_paths` encode Architecture §10.1 include matrix; exclude + strip helpers retained from E6-S04 / E5-S01.
- `deploy/packager.py`: validates the copy plan before writing `deploy/<name>/`; raises `DeployError` when required runtime paths are missing.
- Shared rows: `test_e7_s02_ac4_custom_tools_in_deploy`, `test_e8_s01_ac3_exposed_pipelines_in_deploy`.
- Golden: `tests/integration/deploy/golden/example_bundle_paths.json`.

### Early slice (E6-S04, 2026-07-28)

`deploy/copy_rules.py` + `test_e5_s02_excludes_eval` assert `eval/` (and other §10.1 dev-only paths) are marked excluded.

### Early slice (E5-S01, 2026-07-28)

Packager body uses `strip_harness_yaml` / `strip_agent_yaml` and the exclude policy when writing `deploy/<name>/`. Full include/pin golden matrix + `test_deploy_golden.py` completed in this story.
---
