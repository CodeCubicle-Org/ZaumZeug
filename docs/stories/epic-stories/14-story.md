# E3-S04 — Example harness (general research agent)

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/14-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-20 |
| **Story ID** | E3-S04 |
| **Status** | Done |
| **Epic** | [E3 — Runtime and Local Serve](../02-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 2 of 8 |
| **Story sequence** | 14 of 63 (global build order) |
| **Source** | Extracted from [`02-epic.md`](../02-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1) · [Architecture](../../architecture.md) · **Closes open DoD from** [E3-S02](13-story.md#definition-of-done) |

---

## E3-S04 — Example harness (general research agent)

| Field | Value |
|---|---|
| **Feature** | E3.4 |
| **Persona** | Harness developer · SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E3-S03](11-story.md#e3-s03-builtin-tool-web_fetch) · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) ✅ |
| **Status** | Done (2026-07-20) |
| **Closes open from** | [E3-S02 DoD](13-story.md#definition-of-done): *`zaumzeug serve example` works with templates* (closed 2026-07-20) |

### User story

As a **new user**, I want a reference example harness, so that I can learn config-only agents and run CI without API keys.

### References

- [PRD E3.4](../../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §6.6](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [PRD Journey A](../../prd.md#71-journey-a--config-only-harness-phase-1)


### Implementation resources

**Config templates**

- [Architecture §6.6 — full `example` harness tree](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [Ideation — reference YAML](../../ideation-stage.md)
- Copy targets: `usr-harnesses/example/`, `install/templates/usr-harnesses/example/`

### Acceptance criteria

- [x] **AC-1** `example` uses `agents/researcher/` per Architecture §6.6
- [x] **AC-2** Includes `workflow.yaml` with one stage (`researcher`)
- [x] **AC-3** `agents/researcher/agents-models.yaml` with `default_model_id: mock`
- [x] **AC-4** `zaumzeug serve example` works without `.env`
- [x] **AC-5** No RAG until Epic E8
- [x] **AC-6** Templates under `install/templates/usr-harnesses/example/` for E1-S03

### Implementation tasks (build)

- [x] Author multi-agent template tree per Architecture §6.6 (`harness.yaml`, `workflow.yaml`, `agents/researcher/`)
- [x] Document in `user-docs/getting-started/first-harness.md`; link to [user-docs/guides/multi-agent-workflow.md](../../user-docs/guides/multi-agent-workflow.md) for workflow and pipelines (template copied by E1-S05)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S04 / E3.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/usr-harnesses/fixture/test_example_harness.py::test_e3_s04_ac1_researcher_agent_layout` |
| AC-2 | `tests/usr-harnesses/fixture/test_example_harness.py::test_e3_s04_ac2_workflow_yaml_single_stage` |
| AC-3 | `tests/usr-harnesses/fixture/test_example_harness.py::test_e3_s04_ac3_agents_models_mock_default` |
| AC-4 | `tests/integration/test_serve.py::test_e3_s04_ac4_serve_example_without_env` |
| AC-5 | `tests/usr-harnesses/fixture/test_example_harness.py::test_e3_s04_ac5_no_rag_sections` |
| AC-6 | **manual:** template files exist under `install/templates/usr-harnesses/example/` — also asserted by `test_e3_s04_ac6_install_template_mirrors_example` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/usr-harnesses/fixture/test_example_harness.py -v` passes

### Definition of done

- [x] `zaumzeug doctor example` passes (exit 0; Phase 1 warnings only) with committed `usr-harnesses/example/` — install scaffolding copy path remains [E1-S03](20-story.md)
- [x] Closes [E3-S02 DoD](13-story.md#definition-of-done): *`zaumzeug serve example` works with templates* (mock, no `.env`)
- [x] Verification checklist complete; all ACs traced to tests

---
