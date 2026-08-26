# E6-S08 — Human quality rating → compile feedback loop

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/65-story.md` |
| **Created** | 2026-08-26 |
| **Last modified** | 2026-08-26 (implemented; verification complete) |
| **Status** | Done |
| **Story ID** | E6-S08 |
| **Epic** | [E6 — Evaluation and Quality](../05-epic.md) |
| **Phase** | 2+ *(post–Phase 4 backlog; Journey C human gate)* |
| **Epic build order** | 5 of 8 |
| **Story sequence** | 65 of 65 (global build order) |
| **Source** | Developer feedback: rate harness output when building harnesses / features or switching LLM versions (2026-08-26) |
| **Related** | [Stories index](../00-README.md) · [Epic E6](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) · [Journey C](../../prd.md#73-journey-c--improve-after-failure-phase-2) · [E6-S05](38-story.md) · [E6-S07](40-story.md) · [E8-S03](60-story.md) · [E4-S02b](27.2-story.md) |

---

## E6-S08 — Human quality rating → compile feedback loop

| Field | Value |
|---|---|
| **Feature** | E6.8 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E6-S05](38-story.md#e6-s05-trace-test-case) ✅ · [E6-S07](40-story.md#e6-s07-gepa--deepeval-bridge) ✅ · [E8-S03](60-story.md#e8-s03-trace--dataset-ratchet) ✅ · [E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts) ✅ · [E3-S08](17-story.md#e3-s08-zaumzeug-run-serial-workflow) ✅ |
| **Surface** | `zaumzeug rate` · optional `zaumzeug run --rate` · `data/traces/` + `data/ratings/` · val/train merge · optional `--compile` |

### User story

As a **harness developer**, I want a fast way to rate harness output and leave short feedback (especially when developing a new harness or feature, or switching LLM / model version), so that my ratings and corrected answers flow into `val.jsonl` / `train.jsonl` and I can recompile prompts with GEPA without hand-editing JSONL.

### Why (scope guardrails)

Journey C already captures traces and merges them into datasets once `expected_output` is known ([E8-S03](60-story.md)). The missing piece is a **developer-facing rating gate**: score quality, write the gold answer / notes, choose keep-val / keep-train / discard, then optionally compile.

| In scope | Out of scope (this story) |
|---|---|
| `zaumzeug rate` (interactive + flags) over traces or last `run` | Chainlit / Open WebUI thumbs UI |
| Optional `zaumzeug run --rate` (prompt after run) | Production end-user rating APIs |
| Rating JSONL under `data/ratings/`; merge into val/train | Multi-dimension rubric UI (optional `dimensions` field OK; no UI) |
| Optional `--compile` after apply (invoke existing `run_compile`) | Auto-judge / LLM-as-judge replacing human rate |
| Model / artifact metadata on each rating | Side-by-side bake-off TUI (document pair workflow; no dedicated UI) |
| Docs for new-harness and LLM-switch loops | Confident AI annotation sync (Mode B stays separate) |
| Core path — **no** `[eval]` / DeepEval required | `zaumzeug replay --trace` (still deferred, PRD §9) |
| `RateError` domain errors (same pattern as `EvalError` / `TraceError`) | Extending `StageResult` with `haystack_result` (optional follow-up; v1 synthesizes) |
| | Per-stage `--stage` picker (v1 rates last **agent** stage only) |

### References

- [PRD E6.8](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) *(added with this story)*
- [PRD Journey C](../../prd.md#73-journey-c--improve-after-failure-phase-2)
- [Architecture §5.5 — continuous improvement](../../architecture/04-data-flows.md#55-continuous-improvement-loop)
- [user-docs — Journey C](../../../user-docs/guides/testing.md#trace--test-case-journey-c)
- [E6-S05 — Trace → test case](38-story.md)
- [E6-S07 — GEPA ↔ DeepEval bridge](40-story.md)
- [E8-S03 — Trace → dataset ratchet](60-story.md)

### Implementation resources

**Internal**

- `src/zaumzeug/eval/rate.py` — **Done** (2026-08-26) `RateError`, rating schema, gold validation, path resolve + dedup, `--unrated` index, `--force`, decision apply wrapper; **`run_rate()` is the primary unit/SDK hook** (CLI is a thin wrapper; prefer `run_rate` + `--no-input` in tests)
- `src/zaumzeug/eval/trace.py` — `build_trace_row` / `export_haystack_trace` for `run --rate` export (do **not** reuse serve `ProductionTraceHook`)
- `src/zaumzeug/eval/ratchet.py` — `merge_traces_into_datasets`; call from rate apply (thin wrapper — do not put rating semantics in ratchet)
- `src/zaumzeug/eval/gepa_bridge.py` — train aliases (`question` / `answer`)
- `src/zaumzeug/cli.py` — `rate` subcommand + `run --rate` (not a `cli/` package)
- `src/zaumzeug/compile/runner.py` — `run_compile` when `--compile` (integration tests use `gepa_cls=StubGEPA` per `test_journey_c.py`)
- `src/zaumzeug/runtime/workflow.py` — `StageResult` (`stage_id`, `kind`, `output`, `model_id`); **no `agent` field** — use `stage_id` when `kind == "agent"`
- Fixtures to reuse: `_write_jsonl` / `_minimal_eval_harness` (`tests/unit/eval/test_trace.py`), `_haystack_result` (`test_trace_ratchet.py`), `_scaffold_journey_harness` + `StubGEPA` (`tests/integration/eval/test_journey_c.py`)
- `usr-harnesses/<name>/data/traces/` — immutable source turns
- `usr-harnesses/<name>/data/ratings/` — rating records (dev-only)

**Libraries**

- stdlib only for rating I/O (JSONL) — no DeepEval dependency on the rate path
- Existing compile / GEPA stack when `--compile` is passed

**Happy path (required)**

```text
zaumzeug run <harness> --input "…" --rate
  → select last StageResult with kind == "agent" (error if none)
  → show that stage’s output
  → export data/traces/<stem>.jsonl (synthetic Haystack dict + build_trace_row; source=run)
  → prompt: quality + notes + expected_output + decision
  → write data/ratings/<stem>.jsonl (trace_path set; --force to overwrite)
  → on keep_val / keep_train: merge (gold required) into resolved, deduped val/train paths
  → optional --compile → run_compile(agent_name=stage_id)
```

```text
# Batch / after capture — one turn per invocation
zaumzeug rate <harness> --trace data/traces/….jsonl
zaumzeug rate <harness> --unrated          # pick oldest unrated stem; rate that one turn
zaumzeug rate <harness> --apply --compile  # merge then GEPA for rated agent
zaumzeug rate <harness> --trace … --force  # overwrite existing data/ratings/<stem>.jsonl
```

**Ratings layout (locked)**

| Path | Role |
|---|---|
| `data/traces/<stem>.jsonl` | Immutable captured turn (unchanged by rate) |
| `data/ratings/<stem>.jsonl` | Human rating for that stem; must include `trace_path` |

`--unrated` = files under `data/traces/` whose stem has no matching `data/ratings/<stem>.jsonl`, oldest-first. **One interactive (or non-interactive) turn per CLI invocation** — does not batch-rate all pending stems in one call. Re-rate of an existing stem errors unless `--force`.

**Rating record sketch** (one JSON object; valset-compatible + rating-only fields)

```json
{
  "schema_version": 1,
  "input": "…",
  "actual_output": "…",
  "expected_output": "…",
  "quality": "fail",
  "score": 2,
  "notes": "missed citation; tone ok",
  "decision": "keep_train",
  "agent": "researcher",
  "model_id": "openai/gpt-4.1-mini",
  "artifact": "artifacts/current",
  "rater": "dev",
  "rated_at": "2026-08-26T15:00:00Z",
  "trace_path": "data/traces/trace-….jsonl",
  "extra": { "source": "run" }
}
```

`quality` / `score` / `notes` / `decision` / `rater` / `rated_at` are **rating-only** — never copied into val/train rows. Dataset rows get `input` + `expected_output` (val) or `question` + `answer` (train) only. Rating field `agent` is set from `StageResult.stage_id` when `kind == "agent"` (not a separate `StageResult.agent` attribute).

**Path resolution (locked)**

| Target | Resolve from |
|---|---|
| **Val** | `eval.valset` if configured; else harness `data/val.jsonl`. If the rated agent’s `compile.valset` resolves to a **different** file (`Path.resolve()` equality), append there too (E6-S07 shared-val pattern). **Dedup:** same resolved path → append once. Docs: point both at the same file when you want one golden set. |
| **Train** | Rated agent’s `compile.trainset` (typically `agents/<agent>/data/train.jsonl`) |

| `decision` | Effect |
|---|---|
| `keep_val` | Append gold row to resolved **val** path(s) (deduped). Requires non-empty `expected_output`. |
| `keep_train` | Append train row to resolved **train** path **and** same val append as `keep_val`. Requires non-empty `expected_output`. |
| `discard` | Write rating file only — no dataset merge |

**Rules (locked)**

- Gold enforcement lives in `eval/rate.py` **before** calling merge helpers. Do not rely on `append_trace_to_valset` (it does not error on missing gold).
- High `quality` alone must **never** copy `actual_output` as gold.
- `quality` accepts `pass` \| `partial` \| `fail` **or** integer `1–5` (map: 5→pass, 3–4→partial, 1–2→fail for decision defaults; developer can override `decision`).
- **Last agent stage (not `final_output`):** walk `WorkflowRunResult.stages` **reversed**; select the first with `kind == "agent"`. Use that stage’s `output`, `model_id`, and `stage_id` (as `agent`). If no agent stage exists (pipeline-only workflow), exit non-zero with a clear `RateError`. Do **not** rate a trailing pipeline stage via blind `final_output`. Per-stage `--stage` is out of scope.
- **`run --rate` export (v1):** synthesize a minimal Haystack-shaped result from the selected stage’s text (same pattern as existing ratchet tests), then call `build_trace_row` / `export_haystack_trace` with `agent=stage_id`, `extra.source: "run"`. **Not** serve `ProductionTraceHook`. v1 may omit rich `tools_called` until optional follow-up stores `haystack_result` on `StageResult`.
- `--compile` defaults to the **rated agent** only (`run_compile(..., agent_name=stage_id)`). Opt-in `--all-agents` compiles the full harness. Agent without `compile:` → existing `CompileError`.
- Harness without `eval:` → rate still works (fallback `data/val.jsonl`); `zaumzeug eval` still requires an `eval:` block.
- Existing `data/ratings/<stem>.jsonl` → error unless `--force`.
- Non-interactive flags: `--quality`, `--expected`, `--decision`, `--notes`, `--trace`, `--no-input`, `--force` (fail if required fields missing).

### User workflow (document for harness developers)

Ship a dedicated user-facing section so developers can follow rate → gold → recompile **without reading this story**. Canonical home: [user-docs/guides/testing.md](../../../user-docs/guides/testing.md) under Journey C (new subsection, e.g. **Human quality rating → recompile**). Cross-link from [compile.md](../../../user-docs/guides/compile.md), [cli.md](../../../user-docs/reference/cli.md) (`zaumzeug rate`, `run --rate`), and [user-docs/README.md](../../../user-docs/README.md) command list.

**End-to-end loop (must appear as a diagram or numbered steps)**

```text
zaumzeug run … [--rate]  →  data/traces/ + data/ratings/
  → decide keep_val | keep_train | discard  (+ expected_output gold)
  → --apply merges into val/train
  → --compile (rated agent) regenerates prompts/artifacts
  → optional: zaumzeug eval → zaumzeug deploy → serve --deploy
```

**Workflow A — New harness or feature (primary happy path)**

Document copy-paste commands (example harness or `<name>` placeholder):

```bash
# 1. Run and rate the last agent stage
zaumzeug run <harness> --input "…" --rate
# prompts: quality · notes · expected_output (gold) · decision

# 2. Or rate an existing / production trace later
zaumzeug rate <harness> --unrated
# zaumzeug rate <harness> --trace data/traces/<stem>.jsonl

# 3. Merge gold into datasets and recompile prompts for that agent
zaumzeug rate <harness> --trace data/traces/<stem>.jsonl \
  --quality fail --expected "…" --decision keep_train \
  --apply --compile --no-input

# 4. Optional regression check + ship
zaumzeug eval <harness> --framework builtin   # needs eval: in harness.yaml
zaumzeug deploy <harness>
zaumzeug serve <harness> --deploy
```

Explain in prose: interactive `--rate` / `rate` already applies on `keep_val` / `keep_train`; step 3 shows the scripted form. Gold (`expected_output`) is required before merge — a high quality score alone does not train GEPA.

**Workflow B — Switch LLM or model version**

```bash
# Same input under model A, then model B (change agents-models.yaml / default_model_id between runs)
zaumzeug run <harness> --input "…" --rate   # rate A; note model_id on rating
zaumzeug run <harness> --input "…" --rate   # rate B
# Prefer B’s gold → keep_train/keep_val on the preferred rating (--force if re-rating)
zaumzeug rate <harness> --trace data/traces/<preferred-stem>.jsonl --apply --compile
```

Document that ratings store `model_id` / optional `artifact` for comparison; pin/rollback of compile artifacts remains via [compile.md — Rollback](../../../user-docs/guides/compile.md#rollback-to-a-pinned-run).

**Workflow C — Production / serve traces (extends E8-S03)**

```text
serve capture → copy data/traces/ back to usr-harnesses/<name>/
→ zaumzeug rate <harness> --unrated  (set gold + decision)
→ --apply [--compile]
```

Point to existing Journey C capture flags (`eval.trace_capture` / `ZAUMZEUG_TRACE_CAPTURE`); clarify that **rating and compile stay on the dev machine** — production does not run GEPA (NG3).

**Decision cheat-sheet (must be in user-docs)**

| Decision | When to use | Datasets | Recompile? |
|---|---|---|---|
| `keep_val` | Good gold for regression | Val only | Optional `--compile` |
| `keep_train` | Bad/partial output; teach GEPA | Train **and** val | Yes — `--apply --compile` |
| `discard` | Noise / one-off | None | No |

**Also document (short bullets)**

- Rates the **last agent stage** only (not a trailing pipeline).
- Layout: `data/traces/` immutable; `data/ratings/<stem>.jsonl`; `--unrated` = one stem; `--force` to overwrite a rating.
- Val/train paths come from `eval.valset` / `compile.valset` / `compile.trainset` (shared file recommended).
- No DeepEval required for rate; `[eval]` only if you run DeepEval metrics / Mode B.
- `data/ratings/` is never shipped in `deploy/` (same as other `data/`).

Install templates that mirror user-docs (`install/templates/user-docs/…`) must receive the same Journey C subsection when user-docs are updated.

### Acceptance criteria

- [x] **AC-1** `zaumzeug rate <harness>` rates a turn from `--trace PATH` or via `--unrated` (**one** oldest unrated stem per invocation). Interactive prompts collect `quality`, optional `notes`, `expected_output`, and `decision`. Writes `data/ratings/<stem>.jsonl` with `trace_path`; leaves the original trace immutable. Existing rating file errors unless `--force`. **No DeepEval / `[eval]` required.** Domain failures raise `RateError` (CLI exit non-zero).
- [x] **AC-2** `zaumzeug run <harness> --rate` (after a successful run) selects the **last agent stage** (walk `stages` reversed for `kind == "agent"`; `RateError` if none). When stages are `[agent, pipeline]`, rate the **agent** stage (output / `stage_id` / `model_id`), not the trailing pipeline or blind `final_output`. Exports a trace via synthetic Haystack dict + `build_trace_row` / `export_haystack_trace` (`extra.source: "run"`, `agent=stage_id`, `model_id` from that `StageResult`), then offers the same prompt as `rate`. Skipping / Ctrl-C leaves datasets unchanged (rating file may exist; no merge). Unit/CLI tests may inject a synthetic `WorkflowRunResult` (mocked `run_workflow`).
- [x] **AC-3** `--apply` (default when `decision` is `keep_val` / `keep_train` in interactive mode; explicit in non-interactive) resolves val/train paths per the path-resolution table, **dedupes** resolved val paths, validates non-empty `expected_output` in `eval/rate.py`, then merges via `merge_traces_into_datasets` / train helpers. `keep_val` touches val only; `keep_train` touches train **and** val; `discard` never merges. High `quality` alone must not copy `actual_output` as gold. Rating-only fields never appear in dataset rows. Missing gold → clear non-zero `RateError` (do not call append helpers that silently skip).
- [x] **AC-4** `zaumzeug rate <harness> --apply --compile` runs merge then `run_compile` for the **rated agent** (`agent_name=stage_id` / rating `agent`) by default. `--all-agents` compiles the whole harness. Compile failures surface as today (`CompileError`); ratings already written are not rolled back. Agent without `compile:` → `CompileError`. Integration tests use `run_compile(..., gepa_cls=StubGEPA)` (same pattern as `tests/integration/eval/test_journey_c.py`) — no live LLM.
- [x] **AC-5** Non-interactive rate works for scripts: `--quality`, `--expected`, `--decision`, `--notes`, `--trace`, `--no-input`, `--force`. Integer `quality` `1–5` maps per rules (5→pass, 3–4→partial, 1–2→fail). Exit non-zero when required fields for the chosen decision are missing.
- [x] **AC-6** Each rating stores `model_id` when resolvable and optional `artifact` pin/path so LLM or version switches remain comparable.
- [x] **AC-7** **User workflow docs (required).** Publish the [User workflow](#user-workflow-document-for-harness-developers) content for harness developers:
  - New subsection under Journey C in `user-docs/guides/testing.md` (and matching install template) titled clearly for human rating → recompile, with Workflows **A** (new harness/feature), **B** (LLM switch), and **C** (production traces), the end-to-end loop diagram, decision cheat-sheet, and “also document” bullets above. Live and template trees must stay in sync.
  - Full CLI reference for `zaumzeug rate` and `zaumzeug run --rate` in `user-docs/reference/cli.md` (flags, one-stem `--unrated`, `--force`, `--apply --compile`, last-agent-stage note).
  - Cross-links: testing Journey C ↔ compile guide (recompile after rating) ↔ CLI; mention `zaumzeug rate` in `user-docs/README.md` command overview.
  - Architecture: §5.5 human gate; §6.3 rate path (no DeepEval required); §9 `eval/rate.py`; layout `data/ratings/`.
  - Deploy: seed `data/ratings/` in copy-rules / golden harness and assert it is **not** in the deploy bundle (covered by top-level `data/` exclude; explicit AC assertion).

### Implementation tasks (build)

- [x] Add `eval/rate.py`: `RateError`, schema, write `data/ratings/<stem>.jsonl`, `--unrated` (one stem / oldest-first), `--force`, gold validation, path resolution + dedup, decision apply wrapper; **`run_rate()` required**
- [x] Implement `zaumzeug rate` in `cli.py` (interactive + non-interactive; `--trace` / `--unrated` / `--apply` / `--compile` / `--all-agents` / `--force` / `--no-input`)
- [x] Add `zaumzeug run --rate`: last-agent-stage selection; synthetic Haystack export + rate prompt
- [x] Wire decisions to `merge_traces_into_datasets` / train append (reuse E8-S03 / E6-S07; no rating logic inside ratchet)
- [x] Capture `model_id` / `artifact` / `agent` (`stage_id`) on rating records
- [x] **User docs:** Journey C subsection (Workflows A/B/C + decision table + loop diagram); CLI `rate` / `run --rate`; cross-links from compile.md + user-docs README; sync `install/templates/user-docs/`
- [x] Architecture §5.5 / §6.3 / §9 / layout `data/ratings/`
- [x] Extend deploy copy-rules / golden tests: seed `data/ratings/` and assert absent from deploy bundle

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E6-S08 / E6.8`.

**Primary automation:** call `run_rate(...)` in unit tests; CLI tests use `--no-input` + flags (optional one mocked-`input` smoke). AC-4 uses `StubGEPA`. No live LLM.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_rate.py::test_e6_s08_ac1_rate_writes_ratings_jsonl` · `…::test_e6_s08_ac1_unrated_one_stem` · `…::test_e6_s08_ac1_unrated_oldest_first` · `…::test_e6_s08_ac1_force_overwrite` · `…::test_e6_s08_ac1_existing_rating_errors_without_force` · `…::test_e6_s08_ac1_trace_immutable` · `…::test_e6_s08_ac1_no_eval_block_fallback` · `…::test_e6_s08_ac1_rate_error_domain` · `…::test_e6_s08_ac1_no_deepeval_required` |
| AC-2 | `tests/unit/cli/test_rate_cli.py::test_e6_s08_ac2_run_rate_exports_last_agent_stage` · `…::test_e6_s08_ac2_last_agent_before_pipeline` · `…::test_e6_s08_ac2_pipeline_only_errors` · `…::test_e6_s08_ac2_source_run_not_production` · `…::test_e6_s08_ac2_skip_no_merge` *(mock abort / `KeyboardInterrupt`; assert val/train unchanged)* |
| AC-2 (interactive abort UX) | **manual (optional):** `zaumzeug run … --rate`, Ctrl-C at prompt; confirm val/train unchanged — only if `test_e6_s08_ac2_skip_no_merge` is deferred |
| AC-3 | `tests/unit/eval/test_rate.py::test_e6_s08_ac3_apply_keep_train_merges_val_and_train` · `…::test_e6_s08_ac3_keep_val_val_only` · `…::test_e6_s08_ac3_discard_no_merge` · `…::test_e6_s08_ac3_missing_expected_errors` · `…::test_e6_s08_ac3_high_quality_no_actual_as_gold` · `…::test_e6_s08_ac3_rating_fields_not_in_datasets` · `…::test_e6_s08_ac3_dedupes_same_valset_path` · `…::test_e6_s08_ac3_dual_val_paths_when_different` |
| AC-4 | `tests/integration/eval/test_rate_compile.py::test_e6_s08_ac4_compile_defaults_to_rated_agent` · `…::test_e6_s08_ac4_all_agents_flag` · `…::test_e6_s08_ac4_compile_error_leaves_rating` · `…::test_e6_s08_ac4_agent_without_compile_errors` — all via `run_compile(..., gepa_cls=StubGEPA)` / mocked `run_compile` |
| AC-5 | `tests/unit/cli/test_rate_cli.py::test_e6_s08_ac5_noninteractive_flags` · `…::test_e6_s08_ac5_missing_fields_nonzero` · `…::test_e6_s08_ac5_quality_integer_mapping` |
| AC-6 | `tests/unit/eval/test_rate.py::test_e6_s08_ac6_records_model_id_and_artifact` |
| AC-7 | `tests/unit/docs/test_rate_docs.py::test_e6_s08_ac7_testing_md_workflows_abc` · `…::test_e6_s08_ac7_live_and_template_testing_md_match` · `…::test_e6_s08_ac7_cli_documents_rate` · `…::test_e6_s08_ac7_compile_crosslink` · `…::test_e6_s08_ac7_readme_lists_rate` · `…::test_e6_s08_ac7_architecture_rate_markers` · `tests/unit/deploy/test_copy_rules.py::test_e6_s08_ac7_excludes_data_ratings` |

**AC-7 docs substring checklist** (stable assertions; pattern like `test_production_auth.py`):

| File | Must contain |
|---|---|
| `user-docs/guides/testing.md` (+ install template) | Heading with `Human quality rating`; `Workflow A`; `Workflow B`; `Workflow C`; `zaumzeug run` + `--rate`; `zaumzeug rate` + `--unrated`; `--apply --compile`; `keep_val`; `keep_train`; `discard`; `model_id`; `data/traces/`; `data/ratings/`; `last agent stage` (or equivalent); production copy-back / rate on **dev** |
| `user-docs/reference/cli.md` | `zaumzeug rate` heading; `run --rate`; flags `--trace`, `--unrated`, `--force`, `--apply`, `--compile`, `--all-agents`, `--no-input`, `--quality`, `--expected`, `--decision` |
| `user-docs/README.md` | `` `zaumzeug rate` `` in command overview |
| `user-docs/guides/compile.md` | Cross-link to testing Journey C / human rating subsection |
| Architecture §5.5 / §6.3 / §9 / layout | `zaumzeug rate` or human rate gate; no DeepEval required for rate; `eval/rate.py`; `data/ratings/` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/eval/test_rate.py tests/unit/cli/test_rate_cli.py tests/integration/eval/test_rate_compile.py tests/unit/docs/test_rate_docs.py tests/unit/deploy/test_copy_rules.py -k e6_s08 -v` passes (37 passed, 2026-08-26)

### Definition of done

- [x] Developer can rate a run in one interactive flow (`run --rate` or `rate --trace`) without editing JSONL by hand
- [x] `keep_val` / `keep_train` feed resolved (deduped) datasets; `--compile` recompiles the rated agent’s prompts by default
- [x] Core rate path has no DeepEval dependency; `RateError` for domain failures
- [x] `run_rate()` covered by ≥1 AC-1 / AC-3 unit test; CLI covered via `--no-input`
- [x] `data/ratings/` layout locked; traces immutable; last-**agent**-stage rule (incl. agent-before-pipeline); ratings excluded from deploy (asserted in tests)
- [x] **User workflow documented:** testing.md Journey C subsection (A/B/C + decision table + loop), live↔template sync, CLI reference, compile + README cross-links, Architecture §5.5 / §6.3 / §9 / layout
- [x] Verification checklist complete; all ACs traced to tests (including AC-7 doc + architecture markers)

### Implementation note (2026-08-26)

Shipped: `src/zaumzeug/eval/rate.py` (`run_rate`, `RateError`), CLI `zaumzeug rate` + `run --rate`, `data/ratings/<stem>.jsonl` layout, val/train merge + optional `--compile` (rated agent default). Tests: 37 × `-k e6_s08` (unit + CLI + integration + docs + deploy). Third-party DSPy `InputField`/`OutputField` `prefix=` deprecation warnings filtered in `pyproject.toml` (library internals — ZaumZeug uses string signatures only).
### PO decisions (2026-08-26)

Locked after validation against E6-S05 / E6-S07 / E8-S03 / run / deploy code — no hard conflicts; soft conflicts resolved as: config-resolved val/train paths, `data/ratings/<stem>.jsonl`, last-stage `run --rate` export (not serve hook), gold check in `rate.py`, `--compile` defaults to rated agent, explicit copy-rules test for `data/ratings/`.

### Architect decisions (2026-08-26)

**Approve with changes** — applied:

1. Last **agent** stage = walk `stages` reversed for `kind == "agent"`; never blind `final_output` (pipeline-safe).
2. `agent` on ratings = `StageResult.stage_id`; v1 export synthesizes Haystack dict (optional later: store `haystack_result` on `StageResult`).
3. Val dual-append only when `Path.resolve()` paths differ (dedup).
4. `--unrated` = one stem per invocation; re-rate requires `--force`.
5. Introduce `RateError`; **`run_rate()` required** as primary unit/SDK hook.
6. Ship-time docs: §5.5, §6.3, §9, harness layout `data/ratings/`.
7. **User workflow docs (required):** Journey C subsection with Workflows A/B/C, decision cheat-sheet, and CLI/compile/README cross-links — see [User workflow](#user-workflow-document-for-harness-developers); AC-7 enforces via `tests/unit/docs/test_rate_docs.py`.

### Tester decisions (2026-08-26)

**Approve with changes** — applied:

1. Expanded Verification for locked rules (force-error, immutability, oldest-first, agent-before-pipeline, skip/no-merge, keep_val-only, no actual-as-gold, dual val paths, rating fields not in datasets, compile-error leaves rating, no-eval fallback, quality 1–5).
2. AC-4 locked to `StubGEPA` / `test_journey_c.py` pattern (no live LLM / vague dry-run).
3. `run_rate()` primary unit hook; CLI via `--no-input`.
4. AC-7 substring checklist + live↔template sync + architecture marker tests.
5. Deploy: explicit `data/ratings/` seed assertion (not optional `data/traces/`).
6. Optional manual Ctrl-C only if automated skip test is deferred.

---
