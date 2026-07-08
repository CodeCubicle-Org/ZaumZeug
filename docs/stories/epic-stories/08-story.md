# E2-S07 — `workflow.yaml` schema (serial)

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/08-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-08 |
| **Story ID** | E2-S07 |
| **Status** | Done |
| **Epic** | [E2 — Configuration and Validation](../01-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 1 of 8 |
| **Story sequence** | 8 of 63 (global build order) |
| **Source** | Extracted from [`01-epic.md`](../01-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E2](../../prd.md#epic-e2--configuration-and-validation-phase-1) · [Architecture](../../architecture.md) |

---

## E2-S07 — `workflow.yaml` schema (serial)

| Field | Value |
|---|---|
| **Feature** | E2.7 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want `workflow.yaml` validated with my agent folders, so that serial multi-agent harnesses fail fast before run or compile.

### References

- [PRD E2.7](../../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §3.3](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- [Architecture §6.6](../../architecture/05-configuration.md#66-phase-1-config-schema)


### Implementation resources

**Config examples**

- [Architecture §6.6 — `workflow.yaml` example](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [User guide — multi-agent workflow](../../../install/templates/user-docs/guides/multi-agent-workflow.md)

**Code sketch — serial stage**

```yaml
# workflow.yaml (Phase 1)
entry: researcher
stages:
  - agent: researcher
```

**Code**

- `src/zaumzeug/config/schemas.py` — `WorkflowConfig`, `WorkflowStage`
- `src/zaumzeug/config/loader.py` — `load_workflow()`, agent cross-validation
- `src/zaumzeug/doctor/checks.py` — `check_workflow_config`
- `src/zaumzeug/serve/validate.py` — workflow validation on serve dry-run

### Acceptance criteria

- [x] **AC-1** `workflow.yaml` requires `entry` and non-empty `stages` list
- [x] **AC-2** Each stage is exactly one of `agent: <name>` or `pipeline: <id>` (serial order)
- [x] **AC-3** Every `agent` ref resolves to `agents/<name>/agent.yaml`
- [x] **AC-4** Agent names unique within harness; folder name matches `agent.yaml` `name`
- [x] **AC-5** `parallelism` field fails in Phase 1 with phase hint (deferred)
- [x] **AC-6** `example` harness `workflow.yaml` from §6.6 passes validation

### Implementation tasks (build)

- [x] Add `WorkflowConfig` schema in `src/zaumzeug/config/schemas.py`
- [x] Cross-validate workflow agent refs against `agents/` directory in loader
- [x] Wire into `zaumzeug doctor` and serve/run dry paths

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S07 / E2.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac1_requires_entry_and_stages` |
| AC-2 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac2_agent_or_pipeline_stage` |
| AC-3 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac3_unknown_agent_ref_fails` |
| AC-4 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac4_unique_agent_names` |
| AC-5 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac5_parallelism_phase_hint` |
| AC-6 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac6_example_workflow_valid` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/config/test_workflow_schema.py -v` passes

### Definition of done

- [x] Doctor validates workflow for named harness
- [x] Verification checklist complete; all ACs traced to tests
