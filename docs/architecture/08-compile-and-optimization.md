# Compile and optimization patterns

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 12. Integration patterns

**Phase scope (resolved):** **Phase 2 v1** ships **Pattern A** only (`dspy.GEPA` → export → Haystack). **Pattern B** (`optimize_anything`) is specified for a **later phase (Phase 4+)** — see E4.4 / `compile/gepa_adapter.py`.

### Pattern A — Default *(Phase 2 v1)*

1. Prototype as `dspy.Module` mirroring Haystack behavior (same tool boundaries).
2. Optimize with `dspy.GEPA(metric=metric_with_textual_feedback, reflection_lm=...)`.
3. Export from `dump_state()` / `.save()`.
4. Inject into Haystack `Agent`, pipeline templates, tool descriptions.
5. **Optional — input rewrite/clarify (still Pattern A):** If the DSPy module includes a clarify/rewrite signature, export its optimized instruction to `prompts/input_rewrite.md` (or manifest path). At runtime, apply that **fixed** template to preprocess user messages before the agent loop. GEPA optimizes the **template**, not each end-user chat message. Default harnesses (e.g. Phase 1 `example`) omit this — user text goes directly to the agent.
6. `zaumzeug deploy` → `zaumzeug serve --deploy`.

DSPy and GEPA never run in production. End-user chat is never a GEPA optimization target at runtime.

**Implementation (E4-S01, 2026-07-28):** Step 1 (load DSPy `Module`) is implemented by `zaumzeug.compile.module_loader` — resolves `compile.module` from `agent.yaml`, safe agent-folder import, `dspy.Module` subclass check.

**Implementation (E4-S02a, 2026-07-28):** Compile CLI + Phase 2 schema + LM preflight (`compile/runner.py`, `CompileConfig`, `preflight_compile_lms`).

**Implementation (E4-S02b, 2026-07-28):** GEPA optimize + immutable artifacts (`invoke_gepa`, `StubGEPA` for mock/CI).

**Implementation (E4-S03a, 2026-07-28):** Export contract (`compile/export.py`) — `dump_state()` → Haystack `prompts/system.md`, optional `input_rewrite.md`, `agent.json`, `artifact-manifest.json`. GEPA optimizes the **template** only; runtime applies fixed exported text.

**Implementation (E4-S03b, 2026-07-28):** Runtime preprocess (`runtime/preprocess.py`) — load manifest `paths.input_rewrite`, apply Jinja/`str.format`/plain prepend before `Agent.run` on serve and `zaumzeug run`.

### Pattern B — `optimize_anything` *(deferred — Phase 4+)*

Optimize Haystack-native artifacts (pipeline YAML, prompt files) directly:

1. Seed artifact → evaluator runs `Agent.run()` / `Pipeline.run()`, captures trace.
2. Returns `score` + textual feedback (Actionable Side Information).
3. `gepa.optimize_anything(artifact=seed, evaluator=eval_fn, mode=...)`.

**Optimization modes:** `single-task` | `multi-task` | `generalization` (train/val split — best for production).

**Gap (when Pattern B ships):** GEPA has LangChain adapter but **no Haystack adapter yet** — build `compile/gepa_adapter.py` (PRD E4.4).

### Pattern C — DSPy tools mirror Haystack (eval only)

Wrap Haystack pipelines as DSPy tools inside `ReAct` during compile for train/serve fidelity. Higher latency — use small trainsets or `auto="light"`.

---
