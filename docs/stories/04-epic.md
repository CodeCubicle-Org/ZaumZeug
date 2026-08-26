# Epic E4 — Compile and GEPA Pipeline

| | |
|---|---|
| **Document** | Epic E4 user stories |
| **File** | `docs/stories/04-epic.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-26 (E4-S09 Ready — workflow path Mermaid docs) |
| **Status** | Done (E4-S01–S08, 2026-07-28) · **E4-S09 Ready** (post–Phase 4 backlog) |
| **Build order** | **4 of 8** |
| **Related** | [PRD](../prd.md) · [Architecture](../architecture.md) · [Index](00-README.md) |

---
| Field | Value |
|---|---|
| **Phase** | 2 |
| **Epic** | E4 |
| **Outcome** | Offline GEPA per agent; harness `docs/workflow-diagram.md` regenerated at every compile; **E4-S09 Ready** — `docs/workflow-paths.md` |
| **Depends on** | [E2](01-epic.md) · [E3](02-epic.md) Phase 1 complete |
| **Blocks** | [E6](05-epic.md) · [E5](06-epic.md) (deploy pins compile artifacts) |
| **PRD** | [Epic E4](../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2) |
| **Architecture** | [§5.1–5.3](../architecture/04-data-flows.md#51-default-pattern-compile-deploy-serve) · [§12 Pattern A](../architecture/08-compile-and-optimization.md#pattern-a-default-phase-2-v1) · [§11 #6–7](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build) |
| **Journey** | [Journey B](../prd.md#72-journey-b--full-lifecycle-phase-23) · [Journey C](../prd.md#73-journey-c--improve-after-failure-phase-2) |
| **External** | [DSPy GEPA](https://dspy.ai/api/optimizers/GEPA/overview) |
| **Scope (resolved)** | **Phase 2 v1 CLI:** `dspy.GEPA` (Pattern A). **Optional:** compile-time input rewrite/clarify templates (E4-S03). **`optimize_anything` / Pattern B** shipped as adapter + schema ([E4-S04](#e4-s04-haystack-gepa-evaluator-wrapper), 2026-07-28) |

### Story implementation order (within this epic)

1. **E4-S01** — DSPy module loader ✅ (2026-07-28)
2. **E4-S02a** → **E4-S02b** — Compile schema + GEPA runner ✅ (2026-07-28)
3. **E4-S03a** ✅ → **E4-S03b** ✅ — Export contract + runtime preprocess
4. **E4-S04** — Haystack GEPA evaluator / Pattern B ✅ (2026-07-28)
5. **E4-S05** — Post-compile serve uses artifact ✅ (2026-07-28)
6. **E4-S06** — Compile `--dry-run` ✅ (2026-07-28)
7. **E4-S07** — Artifact rollback to pinned run ✅ (2026-07-28)
8. **E4-S08** — Workflow diagram at compile ✅ (2026-07-28)
9. **E4-S09** — Workflow path Mermaid docs (all paths) *(post–Phase 4; Ready)*

---

## E4-S01 — DSPy module loader

| Field | Value |
|---|---|
| **Feature** | E4.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Status** | Done (2026-07-28) |

### User story

As a **harness developer**, I want the compile path to load my DSPy module from the harness folder, so that GEPA can optimize offline without touching the runtime request path.

### References

- [PRD E4.1](../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §2.1 — Compile vs runtime](../architecture/01-overview-and-principles.md#21-golden-rules)
- [Architecture §3.3 — `modules/`](../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- Canonical story file: [26-story.md](epic-stories/26-story.md)

### Acceptance criteria

- [x] **AC-1** Loads `compile.module` from `agents/<name>/agent.yaml`
- [x] **AC-2** Runs only on `zaumzeug compile` — never during serve/MCP/ACP
- [x] **AC-3** Import errors surface with module path and file hint
- [x] **AC-4** Validates module is a DSPy `Module` subclass

### Implementation tasks (build)

- [x] Implement loader in `src/zaumzeug/compile/module_loader.py`
- [x] Add harness folder to `sys.path` safely (no traversal)

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E4-S01 / E4.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/compile/test_module_loader.py::test_e4_s01_ac1_valid_module_loads` |
| AC-1 (isolation) | `tests/unit/compile/test_module_loader.py::test_e4_s01_reloads_same_module_name_from_other_agent_dir` |
| AC-2 | `tests/unit/compile/test_module_loader.py::test_e4_s01_ac2_not_imported_on_serve_path` |
| AC-3 | `tests/unit/compile/test_module_loader.py::test_e4_s01_ac3_invalid_path_actionable_error` |
| AC-4 | `tests/unit/compile/test_module_loader.py::test_e4_s01_ac4_requires_dspy_module_subclass` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/compile/test_module_loader.py -v` passes (6 passed, 0 skipped)

### Definition of done

- [x] Serve path has zero DSPy imports ([PRD G2](../prd.md#3-goals))
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- `zaumzeug.compile.module_loader.load_dspy_module()` resolves `compile.module` via `resolve_agent_compile`, prepends `agents/<name>/` to `sys.path`, imports `module.path:ClassName`, and requires a `dspy.Module` subclass.
- Path segments reject traversal; post-import `__file__` must stay under the agent directory.
- DSPy imported lazily in the loader only; AST check keeps `serve/` / `runtime/` free of `dspy` / `gepa` / `zaumzeug.compile`. CLI `compile` wired in E4-S02a (2026-07-28).
- **2026-08-14:** Loader drops a stale `sys.modules` chain before import so the same `compile.module` name from another agent folder is not reused (`test_e4_s01_reloads_same_module_name_from_other_agent_dir`).

---

## E4-S02 — GEPA compile *(split into sub-stories)*

> **Canonical story files:** [E4-S02a — schema/CLI](epic-stories/27.1-story.md) ✅ (2026-07-28) · [E4-S02b — GEPA runner](epic-stories/27.2-story.md) ✅ (2026-07-28). Diagram generation: [E4-S08](#e4-s08-workflow-diagram-at-compile) ✅ (2026-07-28).

See [epic-stories/27.1-story.md](epic-stories/27.1-story.md) and [27.2-story.md](epic-stories/27.2-story.md) for full AC → test mapping.

**E4-S02a Done (2026-07-28):** Phase 2 `CompileConfig`; `zaumzeug compile <harness> [--agent]` validates config, loads DSPy modules, preflights task/reflection LM registry + `.env` (GEPA invoke was out of scope for S02a). Tests: `pytest … -k e4_s02a` (4 passed, 0 skipped).

**E4-S02b Done (2026-07-28):** `invoke_gepa()` runs `dspy.GEPA` (stub for mock/CI), LiteLLM strings from registry, budget kwargs, writes `artifacts/<run_id>/` + `current`. Tests: `pytest … -k e4_s02` (8 passed). Export: [E4-S03a](epic-stories/28.1-story.md) ✅.

---

## E4-S03 — Export contract *(split into sub-stories)*

> **Canonical story files:** [E4-S03a — export/manifest](epic-stories/28.1-story.md) ✅ (2026-07-28) · [E4-S03b — runtime preprocess](epic-stories/28.2-story.md) ✅ (2026-07-28)

See epic-stories for full AC → test mapping. Runtime `input_rewrite` preprocess is **E4-S03b** ✅, consumed by [E4-S05](#e4-s05-post-compile-serve-uses-artifact).

**E4-S03a Done (2026-07-28):** `compile/export.py` maps `dump_state()` → Haystack prompts / `agent.json` / `artifact-manifest.json`; optional `input_rewrite`; legacy `manifest.json` accepted. Tests: `pytest … -k e4_s03` (7 passed).

**E4-S03b Done (2026-07-28):** `runtime/preprocess.py` + `build_agent_bundle()` apply fixed `input_rewrite` before `Agent.run` on serve/run (no DSPy). Tests: `pytest … -k e4_s03b` (7 passed). **E4-S04 Done (2026-07-28):** Pattern B `compile/gepa_adapter.py` + `CompileConfig` mode/seed_artifact. Tests: `pytest tests/unit/compile/test_gepa_adapter.py -v` (5 passed, 0 skipped). **E4-S05 Done (2026-07-28):** Post-compile serve prefers artifact; doctor stale `source_hash` warn. Tests: **12 passed, 0 skipped** (`test_compile_serve.py` + `test_e4_s05_ac5_stale_artifact_warn`). **E4-S06 Done (2026-07-28):** `compile --dry-run`. Tests: **5 passed, 0 skipped** (`test_compile_dry_run.py`). **E4-S07 Done (2026-07-28):** Immutable `<run_id>/` + doctor `pinned_artifact` + rollback docs; deploy `artifact_run_id` contract shared with E5-S01. Tests: `test_rollback.py`, `test_e4_s07_ac2_*`, `test_deploy_pin.py`. **E4-S08 Done (2026-07-28):** Mermaid `docs/workflow-diagram.md` + `--workflow-diagram-only`. Tests: **8 passed, 0 skipped** (`test_workflow_diagram.py` + `test_e4_s08_ac5_*`). Epic E4 complete.

---

## E4-S04 — Haystack GEPA evaluator wrapper

| Field | Value |
|---|---|
| **Feature** | E4.4 |
| **Persona** | SDK maintainer |
| **Priority** | P1 (shipped early; was Deferred Phase 4+) |
| **Status** | Done (2026-07-28) — see [29-story.md](epic-stories/29-story.md) |

### User story

As an **SDK maintainer**, I want a Haystack adapter for GEPA `optimize_anything`, so that we can optimize pipeline YAML and other native artifacts without a DSPy module path.

### References

- [PRD E4.4](../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §12 Pattern B](../architecture/08-compile-and-optimization.md#pattern-b-optimize-anything-deferred-phase-4)
- [GEPA optimize_anything](https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/)
- [Story file](epic-stories/29-story.md)

### Acceptance criteria

- [x] **AC-1** Evaluator wrapper supports `optimize_anything` pattern
- [x] **AC-2** Modes: `single-task`, `multi-task`, `generalization`
- [x] **AC-3** Integrates with Haystack agent execution for trace collection

### Implementation tasks (build)

- [x] Implement in `src/zaumzeug/compile/gepa_adapter.py` ([Architecture §11 #8](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build))
- [x] Document mode selection in compile config schema

### Verification (after build)

| AC | Test |
|---|---|
| AC-1 | `tests/unit/compile/test_gepa_adapter.py::test_e4_s04_ac1_optimize_anything_pattern` |
| AC-2 | `tests/unit/compile/test_gepa_adapter.py::test_e4_s04_ac2_modes_single_multi_generalization` |
| AC-3 | `tests/unit/compile/test_gepa_adapter.py::test_e4_s04_ac3_haystack_agent_trace_collection` |

- [x] `pytest tests/unit/compile/test_gepa_adapter.py -v` passes (5 passed, 0 skipped)

### Definition of done

- [x] Documented as Pattern B alongside Pattern A in user-docs compile guide

---

## E4-S05 — Post-compile serve uses artifact

| Field | Value |
|---|---|
| **Feature** | E4.5 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Status** | Done (2026-07-28) — see [30-story.md](epic-stories/30-story.md) |

### User story

As a **harness developer**, I want serve to prefer compiled artifacts over hand-edited prompts, so that what I ship matches what GEPA optimized.

### References

- [PRD E4.5](../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §5.2](../architecture/04-data-flows.md#52-runtime-agent-resolution)

### Acceptance criteria

- [x] **AC-1** After compile, `zaumzeug serve` uses artifact path
- [x] **AC-2** Ignores `compile.module` at serve/run time
- [x] **AC-3** Ignores hand-edited `system_prompt` when valid artifact present
- [x] **AC-4** When artifact includes optional `input_rewrite`, applies preprocess before agent loop (E4-S03) — no GEPA at runtime
- [x] **AC-5** Doctor warns if artifact stale vs module hash (optional warn)

### Implementation tasks (build)

- [x] Ensure runtime factory honors resolver priority
- [x] If `artifact-manifest.json` lists `input_rewrite`, run preprocess step then pass result to agent

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E4-S05 / E4.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/compile/test_compile_serve.py::test_e4_s05_ac1_serve_uses_artifact_after_compile` |
| AC-2 | `tests/integration/compile/test_compile_serve.py::test_e4_s05_ac2_no_module_import_at_serve` |
| AC-3 | `tests/integration/compile/test_compile_serve.py::test_e4_s05_ac3_artifact_over_hand_edited_prompt` |
| AC-4 | `tests/integration/compile/test_compile_serve.py::test_e4_s05_ac4_input_rewrite_preprocess_no_dspy` |
| AC-5 | `tests/integration/test_doctor.py::test_e4_s05_ac5_stale_artifact_warn` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/compile/test_compile_serve.py -v` passes (11 passed, 0 skipped)
- [x] `pytest tests/integration/test_doctor.py::test_e4_s05_ac5_stale_artifact_warn -v` passes (1 passed, 0 skipped)
- [x] Combined E4-S05 verification: **12 passed, 0 skipped** (2026-07-28)

### Definition of done

- [x] Compile → serve happy path documented in user-docs
- [x] Verification checklist complete; all ACs traced to tests

---

## E4-S06 — `--dry-run` on compile

| Field | Value |
|---|---|
| **Feature** | E4.6 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Done (2026-07-28) |

### User story

As a **harness developer**, I want `zaumzeug compile --dry-run`, so that I can validate module imports and model registry without running GEPA or LLM calls.

### References

- [PRD E4.6](../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- Canonical: [31-story.md](epic-stories/31-story.md)

### Acceptance criteria

- [x] **AC-1** Validates compile config and Phase 2 schema
- [x] **AC-2** Resolves module imports successfully
- [x] **AC-3** Prints resolved model registry (task/reflection LM)
- [x] **AC-4** No GEPA run; no LLM API calls
- [x] **AC-5** Exit 0 on success

### Implementation tasks (build)

- [x] Add `--dry-run` to compile CLI
- [x] Reuse module loader + config validation
- [x] Human-readable summary output

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E4-S06 / E4.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac1_validates_phase2_schema` |
| AC-2 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac2_resolves_module_import` |
| AC-3 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac3_prints_model_registry` |
| AC-4 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac4_no_gepa_no_llm_calls` |
| AC-5 | `tests/integration/compile/test_compile_dry_run.py::test_e4_s06_ac5_exit_zero_on_success` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/compile/test_compile_dry_run.py -v` passes (5 passed, 0 skipped)

### Definition of done

- [x] Documented alongside serve dry-run in CLI reference
- [x] Verification checklist complete; all ACs traced to tests

---

## E4-S07 — Rollback to pinned artifact run

| Field | Value |
|---|---|
| **Feature** | PRD E4 story seed |
| **Persona** | Harness developer |
| **Priority** | P2 |
| **Status** | Done (2026-07-28) |
| **Prerequisites** | [E4-S02](#e4-s02-gepa-compile-command) · [E4-S03](#e4-s03-export-contract-haystack-artifacts) |

### User story

As a **harness developer**, I want to pin or rollback to a specific `artifacts/<run_id>/`, so that I can recover from a bad compile without re-running GEPA.

### References

- [PRD E4 story seeds](../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §5.3 — Artifact layout](../architecture/04-data-flows.md#53-artifact-layout)

### Acceptance criteria

- [x] **AC-1** Document/manual path: set `agents/<name>/agent.yaml` `runtime.artifact` to `artifacts/<run_id>/` or update `artifacts/current` pointer
- [x] **AC-2** `zaumzeug doctor` validates pinned run has valid `artifact-manifest.json`
- [x] **AC-3** Deploy can pin a specific `artifact_run_id` in deploy `manifest.json` ([E5-S01](../06-epic.md#e5-s01-zaumzeug-deploy-command))
- [x] **AC-4** Immutable `<run_id>/` directories are never overwritten by new compile

### Implementation tasks (build)

- [x] Ensure compile writes immutable `artifacts/<run_id>/` and updates `artifacts/current` separately
- [x] Add doctor check comparing `current` vs explicitly pinned path
- [x] Document rollback steps in user-docs compile guide

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E4-S07`.

| AC | Test |
|---|---|
| AC-1 | **manual:** user-docs rollback steps; config pin path documented |
| AC-2 | `tests/integration/test_doctor.py::test_e4_s07_ac2_doctor_validates_pinned_manifest` |
| AC-3 | `tests/integration/deploy/test_deploy_pin.py::test_e4_s07_ac3_deploy_manifest_artifact_run_id` *(shared E5-S01)* |
| AC-4 | `tests/integration/compile/test_rollback.py::test_e4_s07_ac4_compile_twice_pin_first_serve_first` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/compile/test_rollback.py -v` passes (1 passed, 0 skipped)

### Definition of done

- [x] Rollback procedure documented; no hand-editing of exported prompt files ([Architecture §15](../architecture/10-operations-and-reference.md#15-anti-patterns))
- [x] Verification checklist complete; all ACs traced to tests

---

## E4-S08 — Workflow diagram at compile

| Field | Value |
|---|---|
| **Feature** | E4.7 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Done (2026-07-28) |
| **Prerequisites** | [E2-S07](../01-epic.md#e2-s07-workflowyaml-schema-serial) · [E4-S02](#e4-s02-gepa-compile-command) *(diagram runs even without GEPA)* |

### User story

As a **harness developer**, I want a workflow diagram generated at compile time, so that my harness documentation stays in sync with `workflow.yaml` and agent LLM config.

### References

- [PRD E4.7](../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §5.4](../architecture/04-data-flows.md#54-workflow-diagram-compile)

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

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E4-S08 / E4.7`.

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

### Definition of done

- [x] Deploy copies diagram per E5-S02 *(packager copy ✅ E5-S01; golden matrix ✅ E5-S02, 2026-07-28)*
- [x] Verification checklist complete; all ACs traced to tests

---

## E4-S09 — Workflow path Mermaid docs (all paths)

| Field | Value |
|---|---|
| **Feature** | E4.8 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Ready |
| **Prerequisites** | [E4-S08](#e4-s08-workflow-diagram-at-compile) ✅ · [E2-S07](01-epic.md#e2-s07-workflowyaml-schema-serial) ✅ |
| **Canonical** | [66-story.md](epic-stories/66-story.md) |

### User story

As a **harness developer**, I want an auto-generated Markdown file under my harness `docs/` that shows every possible path through that harness's workflow as Mermaid diagrams, so that I can review and share how a run can flow through stages (and per-agent tool branches) without reading YAML by hand.

### References

- [PRD E4.8](../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §5.4](../architecture/04-data-flows.md#54-workflow-diagram-compile)
- Canonical story: [66-story.md](epic-stories/66-story.md)

### Acceptance criteria

- [ ] **AC-1** Every non–dry-run `zaumzeug compile` (incl. `--agent`) writes `docs/workflow-paths.md`; diagram unchanged
- [ ] **AC-2** Index + serial stage-path Mermaid (`P1`); agent nodes include model ids; pipeline stages use pipeline id; serial `P1` may mirror overview
- [ ] **AC-3** Per agent stage with tools: separate tool-branch Mermaid; MCP `tool_names` or `mcp:<server>`; no cross-product; no live MCP probe
- [ ] **AC-4** `--workflow-diagram-only` refreshes diagram **and** paths; CLI help mentions both
- [ ] **AC-5** Doctor warns when paths missing or stale vs `workflow.yaml` **or** workflow agent `agent.yaml` files
- [ ] **AC-6** Deploy: `copy_rules` **and** packager explicit copy for `docs/workflow-paths.md`
- [ ] **AC-7** User-docs + Architecture §5.4 + CLI; example + install templates stay in sync

### Implementation tasks (build)

- [ ] `compile/workflow_paths.py` + wire into compile / `--workflow-diagram-only` / `--agent`
- [ ] Doctor staleness (workflow + agent yaml); deploy copy_rules + packager; CLI help; regenerate example + templates
- [ ] User-docs + Architecture §5.4

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Full AC → test map: [66-story.md](epic-stories/66-story.md#verification-after-build). Test file header: `# Story: E4-S09 / E4.8`.

| AC | Test |
|---|---|
| AC-1–AC-4 | `tests/unit/compile/test_workflow_paths.py` (`-k e4_s09`; diagram-only / no live LLM) |
| AC-5 | `tests/integration/test_doctor.py::test_e4_s09_ac5_*` |
| AC-6 | `tests/unit/deploy/test_copy_rules.py::test_e4_s09_ac6_*` + packager/golden |
| AC-7 | `tests/unit/docs/test_workflow_paths_docs.py` (substring checklist) |
| Regression | `tests/unit/compile/test_workflow_diagram.py` (E4-S08) |

### Definition of done

- [ ] `docs/workflow-paths.md` enumerates stage routes + configured tool branches as Mermaid under the harness `docs/` dir
- [ ] Compile / `--workflow-diagram-only` / doctor / deploy stay in sync with E4-S08 diagram
- [ ] Verification checklist complete (see [66-story.md](epic-stories/66-story.md))

**PO decisions (2026-08-26):** Soft conflicts resolved in [66-story.md](epic-stories/66-story.md#po-decisions-2026-08-26).

**Architect decisions (2026-08-26):** Approve-with-changes applied — [66-story.md](epic-stories/66-story.md#architect-decisions-2026-08-26).

**Tester decisions (2026-08-26):** Approve-with-changes applied — [66-story.md](epic-stories/66-story.md#tester-decisions-2026-08-26).

---
