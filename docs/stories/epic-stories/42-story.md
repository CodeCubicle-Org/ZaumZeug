# E5-S02 — Dev vs deploy copy rules

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/42-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E5-S02 |
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
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest) |

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

- [ ] **AC-1** Excludes `agents/<name>/modules/`, `data/`, `eval/`, `skills/` always
- [ ] **AC-2** Includes per-agent `prompts/`, `tools/`, `hooks.py`, `agents-models.yaml` per [Architecture §10.1](../../architecture/07-deploy-packaging.md#101-dev-vs-deploy)
- [ ] **AC-3** Pins per-agent artifact runs under `deploy/<harness>/agents/<name>/artifacts/`
- [ ] **AC-4** Includes `workflow.yaml` and `docs/workflow-diagram.md`
- [ ] **AC-5** Stripped yaml removes `compile`, `eval`, `deploy` sections

### Implementation tasks (build)

- [ ] Implement reference resolver for copy matrix
- [ ] Fail deploy if required runtime path missing

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S02 / E5.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/deploy/test_copy_rules.py::test_e5_s02_ac1_excludes_dev_only_dirs` |
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

---
