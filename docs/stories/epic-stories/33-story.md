# E4-S08 — Workflow diagram at compile

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/33-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E4-S08 |
| **Status** | Done |
| **Epic** | [E4 — Compile and GEPA Pipeline](../04-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 4 of 8 |
| **Story sequence** | 33 of 63 (global build order) |
| **Source** | Extracted from [`04-epic.md`](../04-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2) · [Architecture](../../architecture.md) |

---

## E4-S08 — Workflow diagram at compile

| Field | Value |
|---|---|
| **Feature** | E4.7 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Done (2026-07-28) |
| **Prerequisites** | [E2-S07](08-story.md#e2-s07-workflowyaml-schema-serial) ✅ · [E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts) ✅ |

### User story

As a **harness developer**, I want a workflow diagram generated at compile time, so that my harness documentation stays in sync with `workflow.yaml` and agent LLM config.

### References

- [PRD E4.7](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §5.4](../../architecture/04-data-flows.md#54-workflow-diagram-compile)


### Implementation resources

**Internal spec**

- [Architecture §5.4 — workflow diagram at compile](../../architecture/04-data-flows.md#54-workflow-diagram-compile)
- [Mermaid flowchart syntax](https://mermaid.js.org/syntax/flowchart.html) (if diagram is Mermaid)

### Acceptance criteria

- [x] **AC-1** Every `zaumzeug compile <harness>` writes `docs/workflow-diagram.md` (Mermaid flowchart)
- [x] **AC-2** Diagram nodes label agent/pipeline id and resolved `default_model_id` per agent
- [x] **AC-3** `--workflow-diagram-only` refreshes diagram without GEPA or LLM calls
- [x] **AC-4** File header states auto-generated; hand-edit discouraged
- [x] **AC-5** `zaumzeug doctor` warns when `workflow.yaml` newer than diagram
- [x] **AC-6** Golden snapshot test for example harness diagram structure

### Implementation tasks (build)

- [x] Implement `src/zaumzeug/compile/workflow_diagram.py`
- [x] Invoke from compile runner before/after GEPA per agent
- [x] Add `--workflow-diagram-only` flag to compile CLI

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S08 / E4.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/compile/test_workflow_diagram.py::test_e4_s08_ac1_compile_writes_diagram` |
| AC-2 | `tests/unit/compile/test_workflow_diagram.py::test_e4_s08_ac2_nodes_include_model_ids` |
| AC-3 | `tests/unit/compile/test_workflow_diagram.py::test_e4_s08_ac3_diagram_only_no_gepa` |
| AC-4 | `tests/unit/compile/test_workflow_diagram.py::test_e4_s08_ac4_auto_generated_header` |
| AC-5 | `tests/integration/test_doctor.py::test_e4_s08_ac5_stale_diagram_warning` |
| AC-6 | `tests/unit/compile/test_workflow_diagram.py::test_e4_s08_ac6_example_diagram_snapshot` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/compile/test_workflow_diagram.py -v` passes (7 passed, 0 skipped)
- Verification: **8 passed, 0 skipped** (`test_workflow_diagram.py` + `test_e4_s08_ac5_*`).

### Definition of done

- [x] Deploy copies diagram per E5-S02 *(contract documented; packager copy lands in E5-S02)*
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- `compile/workflow_diagram.py` renders Mermaid `flowchart LR` from `workflow.yaml` stages; agent nodes include `default_model_id (provider)`; pipeline stages use the pipeline id.
- Full `zaumzeug compile` (not `--dry-run`) and `--workflow-diagram-only` write `docs/workflow-diagram.md` with an auto-generated header.
- Doctor stale/missing diagram warn already existed (`check_workflow_diagram_staleness`, E2-S04b); AC-5 re-asserts under the E4-S08 test name.
- Docs: [CLI reference — compile](../../user-docs/reference/cli.md#zaumzeug-compile), [guides/compile.md](../../user-docs/guides/compile.md), [multi-agent-workflow.md](../../user-docs/guides/multi-agent-workflow.md).

---
