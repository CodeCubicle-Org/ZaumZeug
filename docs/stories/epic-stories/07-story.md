# E2-S06 — Structured logging

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/07-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-08 |
| **Story ID** | E2-S06 |
| **Status** | Done |
| **Epic** | [E2 — Configuration and Validation](../01-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 1 of 8 |
| **Story sequence** | 7 of 63 (global build order) |
| **Source** | Extracted from [`01-epic.md`](../01-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E2](../../prd.md#epic-e2--configuration-and-validation-phase-1) · [Architecture](../../architecture.md) |

---

## E2-S06 — Structured logging

| Field | Value |
|---|---|
| **Feature** | E2.6 |
| **Persona** | Harness developer |
| **Priority** | P2 |
| **Prerequisites** | [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) · [E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want verbose logging on serve and compile, so that I can debug model routing and tool calls per request.

### References

- [PRD E2.6](../../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §13](../../architecture/10-operations-and-reference.md#13-debug-and-test-architecture)


### Implementation resources

**Libraries & docs**

- [Python logging](https://docs.python.org/3/library/logging.html)
- [Haystack logging](https://docs.haystack.deepset.ai/docs/logging) (wire level when `--verbose`)
- [Architecture §13.2 — `HARNESS_LOG_LEVEL`](../../architecture/10-operations-and-reference.md#132-mechanisms)

**Code**

- `src/zaumzeug/logging.py` — `configure_logging()`, `log_request()`, `redact_secrets()`, `SecretRedactingFilter`
- `src/zaumzeug/cli.py` — `--verbose` on `serve` and `compile`; calls `configure_logging()` at command entry
- `user-docs/reference/cli.md` — `HARNESS_LOG_LEVEL` and `--verbose` documentation

### Acceptance criteria

- [x] **AC-1** `--verbose` on serve/compile enables SDK + Haystack structured logging
- [x] **AC-2** `HARNESS_LOG_LEVEL=DEBUG` env var works equivalently
- [x] **AC-3** Logs include `model_id`, tool name, artifact path per request where applicable
- [x] **AC-4** No secrets logged (API keys redacted)

### Implementation tasks (build)

- [x] Centralize logging config in `src/zaumzeug/logging.py`
- [x] Wire Haystack log level when verbose
- [x] Document env var in `user-docs/reference/cli.md`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S06 / E2.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/test_logging.py::test_e2_s06_ac1_verbose_flag_sets_debug_level` |
| AC-2 | `tests/unit/test_logging.py::test_e2_s06_ac2_harness_log_level_env_equivalent` |
| AC-3 | `tests/unit/test_logging.py::test_e2_s06_ac3_log_record_includes_model_tool_artifact` |
| AC-4 | `tests/unit/test_logging.py::test_e2_s06_ac4_api_keys_redacted_in_logs` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/test_logging.py -v` passes

### Definition of done

- [x] No secrets logged (API keys redacted)
- [x] Verification checklist complete; all ACs traced to tests

---
