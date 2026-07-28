# Epic E6 — Evaluation and Quality (Optional)

| | |
|---|---|
| **Document** | Epic E6 user stories |
| **File** | `docs/stories/05-epic.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 (E6-S02 done) |
| **Status** | In progress |
| **Build order** | **5 of 8** (before E5 — deploy eval gate needs `zaumzeug eval`) |
| **Related** | [PRD](../prd.md) · [Architecture](../architecture.md) · [Index](00-README.md) |

---
| Field | Value |
|---|---|
| **Phase** | 2 |
| **Epic** | E6 |
| **Outcome** | Developers can regression-test; not required for end users |
| **Depends on** | [E3](02-epic.md) runtime · [E4](04-epic.md) for GEPA bridge (E6-S07) |
| **Blocks** | [E5-S06](../06-epic.md#e5-s06-deploy-eval-gate) |
| **PRD** | [Epic E6](../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) |
| **Architecture** | [§6.3 Eval frameworks](../architecture/05-configuration.md#63-zaumzeug-eval-frameworks) · [§11 #10](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build) · [§13 Debug](../architecture/10-operations-and-reference.md#13-debug-and-test-architecture) |
| **Non-goal** | [NG2 — Mandatory DeepEval](../prd.md#4-non-goals-v1) |
| **External** | [DeepEval](https://github.com/confident-ai/deepeval) |

### Story implementation order (within this epic)

1. **E6-S01** — `[eval]` extra ✅ (2026-07-28)
2. **E6-S02** — `zaumzeug eval` *(blocks E5-S06)* ✅ (2026-07-28)
3. **E6-S03** — Eval gate cross-reference
4. **E6-S04** → **E6-S07** — pytest scaffold, trace, HTTP mode, GEPA bridge

---

## E6-S01 — Optional `[eval]` extra

| Field | Value |
|---|---|
| **Feature** | E6.1 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Status** | Done (2026-07-28) |

### User story

As a **harness developer**, I want DeepEval as an optional extra, so that core install stays lean for users who do not run eval.

### References

- [PRD E6.1](../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §4.4](../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)

### Acceptance criteria

- [x] **AC-1** Core `zaumzeug` install has no `deepeval` dependency
- [x] **AC-2** `[eval]` extra installs `deepeval`
- [x] **AC-3** `pip install "zaumzeug[eval]"` documented in user-docs

### Implementation tasks (build)

- [x] Add `eval = ["deepeval"]` to `pyproject.toml` optional-dependencies *(already present from E2-S00; re-asserted)*
- [x] Guard imports in eval module with friendly error

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E6-S01 / E6.1`. Canonical: [34-story.md](epic-stories/34-story.md).

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_eval_extra.py::test_e6_s01_ac1_core_has_no_deepeval_dependency` |
| AC-2 | `tests/unit/eval/test_eval_extra.py::test_e6_s01_ac2_eval_extra_installs_deepeval` |
| AC-3 | `tests/unit/eval/test_eval_extra.py::test_e6_s01_ac3_user_docs_document_eval_extra` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/eval/test_eval_extra.py -v` passes (6 passed, 0 skipped)

### Definition of done

- [x] `zaumzeug doctor` does not require deepeval unless eval configured
- [x] Verification checklist complete; all ACs traced to tests

**E6-S01 Done (2026-07-28):** `eval = ["deepeval"]` in `pyproject.toml`; `zaumzeug.eval.require_deepeval()` friendly install hint; doctor has no deepeval dependency. Tests: **6 passed, 0 skipped**.

---

## E6-S02 — `zaumzeug eval` command

| Field | Value |
|---|---|
| **Feature** | E6.2 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Status** | Done (2026-07-28) |

### User story

As a **harness developer**, I want `zaumzeug eval`, so that I can run builtin JSONL checks or DeepEval metrics without shipping eval to production.

### References

- [PRD E6.2](../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §6.3](../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)

### Acceptance criteria

- [x] **AC-1** `eval.framework: deepeval` requires `[eval]` extra; shows install hint if missing
- [x] **AC-2** `eval.framework: builtin` runs JSONL checks without DeepEval
- [x] **AC-3** Missing `eval` section → clear error exit
- [x] **AC-4** CLI override: `zaumzeug eval <name> --framework builtin`
- [x] **AC-5** Default framework `deepeval` when `eval:` present and `framework` omitted

### Implementation tasks (build)

- [x] Implement `src/zaumzeug/eval/runner.py` ([Architecture §11 #10](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build))
- [x] Builtin: load `eval.valset` JSONL; exact/substring match on `expected_output`
- [x] DeepEval: wire configured metrics and thresholds

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E6-S02 / E6.2`. Canonical: [35-story.md](epic-stories/35-story.md).

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_runner.py::test_e6_s02_ac1_deepeval_missing_extra_hint` |
| AC-2 | `tests/unit/eval/test_runner.py::test_e6_s02_ac2_builtin_jsonl_checks` |
| AC-3 | `tests/unit/eval/test_runner.py::test_e6_s02_ac3_missing_eval_section_error` |
| AC-4 | `tests/unit/eval/test_runner.py::test_e6_s02_ac4_cli_framework_override` |
| AC-5 | `tests/unit/eval/test_runner.py::test_e6_s02_ac5_default_deepeval_when_omitted` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/eval/test_runner.py -v` passes (7 passed, 0 skipped)

### Definition of done

- [x] Eval never runs on production serve path ([PRD NG3 adjacent — compile on prod](../prd.md#4-non-goals-v1))
- [x] Verification checklist complete; all ACs traced to tests

---

---

## E6-S03 — Eval gate on deploy

| Field | Value |
|---|---|
| **Feature** | E6.3 |
| **Persona** | Harness developer |
| **Priority** | P1 |

### User story

As a **harness developer**, I want deploy to respect eval gates, so that failed regression tests can block releases.

### References

- [PRD E6.3](../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [E5-S06 — Deploy eval gate](../06-epic.md#e5-s06-deploy-eval-gate)

### Acceptance criteria

- [ ] **AC-1** Covered by E5-S06 implementation
- [ ] **AC-2** Eval runner invoked from deploy packager when gate is `warn` or `block`

### Implementation tasks (build)

- [ ] Cross-link tests between E5 and E6
- [ ] Document in harness.yaml `deploy.eval_gate` examples

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). **Cross-story** — primary tests live under E5-S06.

| AC | Test |
|---|---|
| AC-1 | **shared:** [E5-S06](../06-epic.md#e5-s06-deploy-eval-gate) Verification table |
| AC-2 | `tests/unit/deploy/test_eval_gate.py::test_e6_s03_ac2_packager_invokes_eval_runner` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] E5-S06 and E6-S03 verification tables both reference same tests

### Definition of done

- [ ] Single source of truth in deploy packager (no duplicate gate logic)
- [ ] Verification checklist complete

---

## E6-S04 — `eval/` pytest scaffold

| Field | Value |
|---|---|
| **Feature** | E6.4 |
| **Persona** | Harness developer |
| **Priority** | P2 |

### User story

As a **harness developer**, I want optional pytest files under `eval/`, so that I can run DeepEval tests with familiar tooling.

### References

- [PRD E6.4](../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §3.3 — `eval/`](../architecture/02-repository-and-layout.md#33-harness-folder-layout)

### Acceptance criteria

- [ ] **AC-1** Optional `usr-harnesses/<name>/eval/test_*.py` runs via `deepeval test run`
- [ ] **AC-2** Custom metrics in `eval/metrics.py` importable
- [ ] **AC-3** `eval/` excluded from deploy bundle (E5-S02)

### Implementation tasks (build)

- [ ] Add eval template in zaumzeug init (optional flag)
- [ ] Document `deepeval test run` workflow in user-docs

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E6-S04 / E6.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/eval/test_deepeval_scaffold.py::test_e6_s04_ac1_deepeval_test_run` *(requires [eval] extra in CI job)* |
| AC-2 | `tests/integration/eval/test_deepeval_scaffold.py::test_e6_s04_ac2_custom_metrics_importable` |
| AC-3 | **shared:** `tests/unit/deploy/test_copy_rules.py::test_e5_s02_excludes_eval` *(E5-S02)* |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/eval/test_deepeval_scaffold.py -v` passes (with eval extra)

### Definition of done

- [ ] Example metric file in example harness (optional, dev-only)
- [ ] Verification checklist complete; all ACs traced to tests

---

## E6-S05 — Trace → test case

| Field | Value |
|---|---|
| **Feature** | E6.5 |
| **Persona** | Harness developer |
| **Priority** | P2 |

### User story

As a **harness developer**, I want to score a production trace as a test case, so that I can turn failures into regression tests ([Journey C](../prd.md#73-journey-c--improve-after-failure-phase-2)).

### References

- [PRD E6.5](../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §5.5](../architecture/04-data-flows.md#55-continuous-improvement-loop)

### Acceptance criteria

- [ ] **AC-1** Haystack trace export to JSONL under `data/traces/`
- [ ] **AC-2** `zaumzeug eval --trace <path>` scores single trace
- [ ] **AC-3** Trace format documented for append to valset

### Implementation tasks (build)

- [ ] Implement trace export helper
- [ ] Add `--trace` CLI flag to eval command

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E6-S05 / E6.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_trace.py::test_e6_s05_ac1_trace_export_jsonl` |
| AC-2 | `tests/unit/eval/test_trace.py::test_e6_s05_ac2_eval_trace_flag_scores` |
| AC-3 | **manual:** user-docs documents trace JSONL schema for valset append |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/eval/test_trace.py -v` passes

### Definition of done

- [ ] Journey C documented end-to-end in user-docs
- [ ] Verification checklist complete; all ACs traced to tests

---

## E6-S06 — HTTP black-box eval (Mode C)

| Field | Value |
|---|---|
| **Feature** | E6.6 |
| **Persona** | Harness developer |
| **Priority** | P3 |

### User story

As a **harness developer**, I want to eval against a running server, so that I can black-box test staging deployments.

### References

- [PRD E6.6](../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §6.3 — Mode C](../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)

### Acceptance criteria

- [ ] **AC-1** Optional Mode C: eval calls running `zaumzeug serve` via `/v1/chat/completions`
- [ ] **AC-2** Configurable base URL (default localhost + harness port)
- [ ] **AC-3** Same metrics as in-process mode where applicable

### Implementation tasks (build)

- [ ] Add HTTP client path in eval runner
- [ ] CLI flag: `--base-url` or config field

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E6-S06 / E6.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/eval/test_http_eval.py::test_e6_s06_ac1_calls_serve_chat_completions` |
| AC-2 | `tests/integration/eval/test_http_eval.py::test_e6_s06_ac2_base_url_override` |
| AC-3 | `tests/integration/eval/test_http_eval.py::test_e6_s06_ac3_same_metrics_as_inprocess` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/eval/test_http_eval.py -v` passes

### Definition of done

- [ ] Documented as staging/debug tool only
- [ ] Verification checklist complete; all ACs traced to tests

---

## E6-S07 — GEPA ↔ DeepEval bridge

| Field | Value |
|---|---|
| **Feature** | E6.7 |
| **Persona** | Harness developer |
| **Priority** | P2 |

### User story

As a **harness developer**, I want failed eval rows to feed compile training data, so that GEPA and DeepEval share one improvement loop.

### References

- [PRD E6.7](../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §6.3 — GEPA ↔ DeepEval bridge](../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)

### Acceptance criteria

- [ ] **AC-1** Failed eval rows can append to `data/train.jsonl`
- [ ] **AC-2** Shared `data/val.jsonl` for compile and eval
- [ ] **AC-3** GEPA custom metric may delegate to DeepEval `.measure()` optionally
- [ ] **AC-4** Story seed: GEPA metric delegates to DeepEval optionally

### Implementation tasks (build)

- [ ] Document JSONL schemas for train/val
- [ ] Helper to append failed rows from eval report
- [ ] Example in `modules/metrics.py` template

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E6-S07 / E6.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_gepa_bridge.py::test_e6_s07_ac1_failed_rows_append_train_jsonl` |
| AC-2 | `tests/unit/eval/test_gepa_bridge.py::test_e6_s07_ac2_shared_val_jsonl` |
| AC-3 | `tests/unit/eval/test_gepa_bridge.py::test_e6_s07_ac3_gepa_metric_delegates_deepeval` |
| AC-4 | `tests/unit/eval/test_gepa_bridge.py::test_e6_s07_ac4_optional_deepeval_measure` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/eval/test_gepa_bridge.py -v` passes

### Definition of done

- [ ] Compile → eval → compile loop documented ([Journey C](../prd.md#73-journey-c--improve-after-failure-phase-2))
- [ ] Verification checklist complete; all ACs traced to tests
