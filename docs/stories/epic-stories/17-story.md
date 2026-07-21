# E3-S08 — `zaumzeug run` (serial workflow)

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/17-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-21 |
| **Story ID** | E3-S08 |
| **Status** | Done |
| **Epic** | [E3 — Runtime and Local Serve](../02-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 2 of 8 |
| **Story sequence** | 17 of 63 (global build order) |
| **Source** | Extracted from [`02-epic.md`](../02-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1) · [Architecture](../../architecture.md) |

---

## E3-S08 — `zaumzeug run` (serial workflow)

| Field | Value |
|---|---|
| **Feature** | E3.6 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S07](08-story.md#e2-s07-workflowyaml-schema-serial) · [E3-S00](12-story.md#e3-s00-runtime-factory-haystack-agent-builder) · [E3-S01](10-story.md#e3-s01-modelrouter) |
| **Status** | Done (2026-07-21) |

### User story

As a **harness developer**, I want `zaumzeug run` to execute my harness workflow serially, so that multiple agents cooperate without manual orchestration.

### References

- [PRD E3.6](../../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §5.2](../../architecture/04-data-flows.md#52-runtime-agent-resolution)
- [Architecture §8.2](../../architecture/06-runtime-and-protocols.md#82-harness-vs-raw-hayhooks)


### Implementation resources

**Internal spec**

- [Architecture §8.2 — `zaumzeug run`](../../architecture/06-runtime-and-protocols.md#82-harness-vs-raw-hayhooks)
- [User guide — multi-agent workflow](../../../install/templates/user-docs/guides/multi-agent-workflow.md)
- [Haystack Agent messages](https://docs.haystack.deepset.ai/docs/agents) (list of `{"role", "content"}` dicts)

**Inter-stage context (AC-3)**

```python
messages = [{"role": "user", "content": user_input}]
if prior_output:
    messages.insert(0, {"role": "user", "content": prior_output})
```

### Acceptance criteria

- [x] **AC-1** Executes `workflow.yaml` stages in order (serial only Phase 1)
- [x] **AC-2** Each agent stage loads `agents/<name>/` config and merged `agents-models.yaml`
- [x] **AC-3** Prior stage output passed as context to next agent stage — append prior agent's final assistant message as a new `user` message: `{"role": "user", "content": "<prior_stage_output>"}` prepended before the workflow input; full message list forwarded to the next agent's Haystack Agent.run
- [x] **AC-4** Pipeline stages invoke exposed pipeline when `serve.expose` lists id (Phase 4+; stub OK in Phase 1)
- [x] **AC-5** `--from <stage>` runs partial workflow for debugging
- [x] **AC-6** Fails fast with harness + agent name on resolution errors
- [x] **AC-7** Integration test: two-agent serial workflow with mock models

### Implementation tasks (build)

- [x] Implement `src/zaumzeug/runtime/workflow.py` serial executor
- [x] Add `run` subcommand in `src/zaumzeug/cli.py`
- [x] Reuse runtime factory per stage with stage-scoped ModelRouter

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S08 / E3.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_workflow_run.py::test_e3_s08_ac1_serial_stage_order` |
| AC-2 | `tests/integration/test_workflow_run.py::test_e3_s08_ac2_per_agent_models_registry` |
| AC-3 | `tests/integration/test_workflow_run.py::test_e3_s08_ac3_stage_output_forwarded` |
| AC-4 | **manual:** pipeline stage deferred Phase 4 (Phase 1 raises actionable `WorkflowError` stub) |
| AC-5 | `tests/integration/test_workflow_run.py::test_e3_s08_ac5_from_stage_partial_run` |
| AC-6 | `tests/integration/test_workflow_run.py::test_e3_s08_ac6_actionable_agent_error` |
| AC-7 | `tests/integration/test_workflow_run.py::test_e3_s08_ac7_two_agent_mock_workflow` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/test_workflow_run.py -v` passes

### Definition of done

- [x] `zaumzeug run example` works with single-stage workflow
- [x] Verification checklist complete; all ACs traced to tests
