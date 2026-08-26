# Compile and optimization patterns

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 12. Integration patterns

**Phase scope (resolved):** **Phase 2 v1** ships **Pattern A** (`dspy.GEPA` → export → Haystack) as the default `zaumzeug compile` path. **Pattern B** (`optimize_anything`) shipped early as `compile/gepa_adapter.py` (E4-S04, 2026-07-28).

### Pattern A — Default *(Phase 2 v1)*

1. Prototype as `dspy.Module` mirroring Haystack behavior (same tool boundaries).
2. Optimize with `dspy.GEPA(metric=metric_with_textual_feedback, reflection_lm=...)`.
3. Export from `dump_state()` / `.save()`.
4. Inject into Haystack `Agent`, pipeline templates, tool descriptions.
5. **Optional — input rewrite/clarify (still Pattern A):** If the DSPy module includes a clarify/rewrite signature, export its optimized instruction to `prompts/input_rewrite.md` (or manifest path). At runtime, apply that **fixed** template to preprocess user messages before the agent loop. GEPA optimizes the **template**, not each end-user chat message. Default harnesses (e.g. Phase 1 `example`) omit this — user text goes directly to the agent.
6. `zaumzeug deploy` → `zaumzeug serve --deploy`.

DSPy and GEPA never run in production. End-user chat is never a GEPA optimization target at runtime.

**Implementation (E5-S03, 2026-07-28):** Step 6 production serve — `zaumzeug serve <name> --deploy` loads only `deploy/<name>/` (same OpenAI REST as dev). Tests: `tests/integration/deploy/test_serve_deploy.py`.

**Implementation (E4-S01, 2026-07-28):** Step 1 (load DSPy `Module`) is implemented by `zaumzeug.compile.module_loader` — resolves `compile.module` from `agent.yaml`, safe agent-folder import, `dspy.Module` subclass check. **2026-08-14:** each load drops a stale `sys.modules` chain so the same dotted name from another agent folder is not reused.

**Implementation (E4-S02a, 2026-07-28):** Compile CLI + Phase 2 schema + LM preflight (`compile/runner.py`, `CompileConfig`, `preflight_compile_lms`).

**Implementation (E4-S02b, 2026-07-28):** GEPA optimize + immutable artifacts (`invoke_gepa`, `StubGEPA` for mock/CI).

**Implementation (E6-S07, 2026-07-28):** Optional `agents/<agent>/modules/metrics.py` auto-loaded by `invoke_gepa` (`metric` / `gepa_metric`); may wrap DeepEval `.measure()` via `eval/gepa_bridge.deepeval_gepa_metric`. Failed eval → train helper: `append_failed_eval_to_train`. Docs: [testing.md — GEPA ↔ DeepEval bridge](../user-docs/guides/testing.md#gepa--deepeval-bridge-compile--eval--compile).

**Implementation (E4-S03a, 2026-07-28):** Export contract (`compile/export.py`) — `dump_state()` → Haystack `prompts/system.md`, optional `input_rewrite.md`, `agent.json`, `artifact-manifest.json`. GEPA optimizes the **template** only; runtime applies fixed exported text.

**Implementation (E4-S03b, 2026-07-28):** Runtime preprocess (`runtime/preprocess.py`) — load manifest `paths.input_rewrite`, apply Jinja/`str.format`/plain prepend before `Agent.run` on serve and `zaumzeug run`.

**Implementation (E4-S05, 2026-07-28):** Post-compile serve prefers valid `agent.artifact` over hand-edited `system_prompt` and never imports `compile.module`. Manifest records `source_hash` of the module `.py`; doctor warns on drift. Happy path: [user-docs/guides/compile.md](../user-docs/guides/compile.md#serve-after-compile).

**Implementation (E4-S06, 2026-07-28):** `zaumzeug compile --dry-run` — same validation path as E4-S02a (schema, module load, LM registry preflight) without GEPA, LLM calls, or artifact writes. Summary prints task/reflection model ids. Tests: `tests/integration/compile/test_compile_dry_run.py`.

**Implementation (E4-S07, 2026-07-28):** Immutable `artifacts/<run_id>/` (never overwritten); pin/rollback via `agent.artifact` or `current`; doctor validates pins. Docs: [user-docs/guides/compile.md](../user-docs/guides/compile.md#rollback-to-a-pinned-run).

**Implementation (E4-S08, 2026-07-28):** Every full `zaumzeug compile` (and `--workflow-diagram-only`) regenerates harness `docs/workflow-diagram.md` (Mermaid) from `workflow.yaml` + resolved agent `default_model_id` / provider. Generator: `compile/workflow_diagram.py` + shared `compile/workflow_labels.py`. Doctor warns when the diagram is stale or missing ([§5.4](04-data-flows.md#54-workflow-diagram-and-paths-compile)). Tests: `tests/unit/compile/test_workflow_diagram.py`.

**Implementation (E4-S09, 2026-08-26):** Same compile paths regenerate `docs/workflow-paths.md` (index, serial stage route, per-agent tool branches). Generator: `compile/workflow_paths.py`. Doctor `workflow_paths` check (dev only). Tests: `tests/unit/compile/test_workflow_paths.py`.

### Pattern B — `optimize_anything` *(deferred — Phase 4+)*

> **Shipped early (E4-S04, 2026-07-28):** adapter + schema are available; see implementation note below. Originally scoped to Phase 4+.

Optimize Haystack-native artifacts (pipeline YAML, prompt files) directly:

1. Seed artifact → evaluator runs `Agent.run()` / `Pipeline.run()`, captures trace.
2. Returns `score` + textual feedback (Actionable Side Information).
3. `optimize_haystack_artifact(...)` / `gepa.optimize_anything(artifact=seed, evaluator=eval_fn, mode=...)`.

**Optimization modes:** `single-task` | `multi-task` | `generalization` (train/val split — best for production).

**Implementation (E4-S04, 2026-07-28):** `compile/gepa_adapter.py` — `HaystackGepaAdapter` + `optimize_haystack_artifact`; mode fields on `CompileConfig`. CLI `zaumzeug compile` remains Pattern A; Pattern B is the programmatic adapter path.

### Pattern C — DSPy tools mirror Haystack (eval only)

Wrap Haystack pipelines as DSPy tools inside `ReAct` during compile for train/serve fidelity. Higher latency — use small trainsets or `auto="light"`.

---
