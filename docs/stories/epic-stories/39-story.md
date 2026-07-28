# E6-S06 — HTTP black-box eval (Mode C)

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/39-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E6-S06 |
| **Status** | Done |
| **Epic** | [E6 — Evaluation and Quality (Optional)](../05-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 5 of 8 |
| **Story sequence** | 39 of 63 (global build order) |
| **Source** | Extracted from [`05-epic.md`](../05-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E6](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) · [Architecture](../../architecture.md) |

---

## E6-S06 — HTTP black-box eval (Mode C)

| Field | Value |
|---|---|
| **Feature** | E6.6 |
| **Persona** | Harness developer |
| **Priority** | P3 |
| **Status** | Done (2026-07-28) |
| **Prerequisites** | [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command) ✅ |

### User story

As a **harness developer**, I want to eval against a running server, so that I can black-box test staging deployments.

### References

- [PRD E6.6](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §6.3 — Mode C](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)


### Implementation resources

**Libraries & docs**

- [httpx](https://www.python-httpx.org/) — HTTP black-box against running serve
- [DeepEval — Mode C](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)

### Acceptance criteria

- [x] **AC-1** Optional Mode C: eval calls running `zaumzeug serve` via `/v1/chat/completions`
- [x] **AC-2** Configurable base URL (default localhost + harness port)
- [x] **AC-3** Same metrics as in-process mode where applicable

### Implementation tasks (build)

- [x] Add HTTP client path in eval runner
- [x] CLI flag: `--base-url` or config field

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E6-S06 / E6.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/eval/test_http_eval.py::test_e6_s06_ac1_calls_serve_chat_completions` |
| AC-2 | `tests/integration/eval/test_http_eval.py::test_e6_s06_ac2_base_url_override` *(also `test_e6_s06_default_base_url_hits_harness_port`)* |
| AC-3 | `tests/integration/eval/test_http_eval.py::test_e6_s06_ac3_same_metrics_as_inprocess` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/eval/test_http_eval.py -v` passes (4 passed, 0 skipped)

### Definition of done

- [x] Documented as staging/debug tool only
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- `eval/runner.py`: Mode C via `httpx` → `POST {base}/v1/chat/completions`; `resolve_eval_base_url` / `default_eval_base_url`.
- CLI `--base-url [URL]` (`nargs='?'`) and `eval.base_url` in `harness.yaml`; empty → `http://127.0.0.1:<serve.hayhooks.port>`.
- Docs: [testing.md — Mode C](../../../user-docs/guides/testing.md#mode-c--http-black-box-stagingdebug), [cli.md — zaumzeug eval](../../../user-docs/reference/cli.md#zaumzeug-eval).

---
