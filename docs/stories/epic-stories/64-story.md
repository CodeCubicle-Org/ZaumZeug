# E8-S07 — Workflow run reliability and stage transparency

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/64-story.md` |
| **Created** | 2026-08-01 |
| **Last modified** | 2026-08-01 |
| **Story ID** | E8-S07 |
| **Epic** | [E8 — RAG and Production Hardening](../08-epic.md) |
| **Phase** | 4 *(pull-forward OK after E5 — does not require E7)* |
| **Epic build order** | 8 of 8 |
| **Story sequence** | 64 of 64 (global build order) |
| **Source** | Adoption evaluation gaps (Swiss Made Legal / Jeff Gutierrez, July 2026) |
| **Related** | [Stories index](../00-README.md) · [Epic E8](../../prd.md#epic-e8--rag-and-production-hardening-phase-4) · [Architecture §2.4 failure ladder](../../architecture/01-overview-and-principles.md#24-industry-patterns) · [E3-S08](17-story.md) · [E2-S06](07-story.md) |

---

## E8-S07 — Workflow run reliability and stage transparency

| Field | Value |
|---|---|
| **Feature** | E8.7 |
| **Persona** | Client integrator · Harness developer · Ops |
| **Priority** | P0 |
| **Prerequisites** | [E3-S08](17-story.md#e3-s08-zaumzeug-run-serial-workflow) ✅ · [E2-S06](07-story.md#e2-s06-structured-logging) ✅ · [E2-S04b](05.2-story.md#e2-s04b-zaumzeug-doctor-phase-aware-warnings) ✅ |
| **Surface** | `zaumzeug run` / `run_workflow` **only** — HTTP serve path is a follow-up |

### User story

As a **client integrator running local or flaky model backends**, I want `zaumzeug run` / `run_workflow` to surface stage-scoped failures, optionally retry them, validate JSON stage outputs, and emit structured stage logs — so batch reviews are reliable and debuggable without OpenTelemetry or integration-layer workarounds.

### Why (scope guardrails)

Adoption feedback confirmed serial workflows and local `openai_compatible` (Ollama) fit well, but production batch use needs a narrow reliability layer on the **run** path:

| In scope | Out of scope (this story) |
|---|---|
| Typed live-generation `WorkflowError` on `run_workflow` | OpenTelemetry / distributed tracing |
| Harness-level retry policy applied to each stage’s attempts | Model fallback / full failure ladder |
| Stage lifecycle via `log_request()` at INFO with structured `stage` | Logging full prompts/outputs by default |
| Optional `output.format: json` (parse only) | JSON Schema / `output.schema` (deferred) |
| Doctor **fail** for phase-gated `tools.mcp` / `custom` (dev + `--deploy`) | Serve/HTTP path retry & validation (follow-up) |
| | Memory, multi-turn, streaming, context truncation |
| | Rich structured-output providers / grammar decoding |

**Follow-up (not this story):** share the same stage executor with `zaumzeug serve` / `AgentPipelineWrapper` so REST gets identical retry, logging, and JSON checks.

### References

- [PRD E8.7](../../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §2.4 — failure ladder](../../architecture/01-overview-and-principles.md#24-industry-patterns) *(retry step only)*
- [Architecture §6.2 — agent config](../../architecture/05-configuration.md#62-config-sections)
- [Architecture §6.6 — Phase 1 config schema](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [E2-S06 — `log_request`](07-story.md#e2-s06-structured-logging)
- [E3-S08 — `run_workflow`](17-story.md#e3-s08-zaumzeug-run-serial-workflow)

### Implementation resources

**Internal**

- `src/zaumzeug/runtime/workflow.py` — stage loop; build + message prep once; retry only `agent.run` + output check
- `src/zaumzeug/logging.py` — extend `log_request()` / `_STRUCTURED_KEYS` with required `stage`; emit lifecycle at INFO
- `src/zaumzeug/config/schemas.py` — `HarnessConfig.runtime` (`max_attempts` ≥ 1), optional `AgentConfig.output` (`format: json` only)
- `src/zaumzeug/doctor/checks.py` + `runner.py` — phase-gated tool honesty in **default and `--deploy`** modes
- `src/zaumzeug/config/loader.py` — `strip_phase_gated_agent_tools` currently hides MCP from doctor validation

**Retry boundary (required)**

```text
per stage:
  1. resolve models + build agent once          ← failures: WorkflowError, NO retry
  2. build messages / preprocess once           ← failures: WorkflowError, NO retry
  3. for attempt in 1..max_attempts:            ← max_attempts >= 1
       agent.run(...)                           ← any exception: retryable
       optional JSON validate                   ← invalid (incl. empty text): retryable
       on success → break
       else sleep(initial_delay_s * backoff^(attempt-1))
  4. if still failing → WorkflowError (+ attempt count)
```

**Config sketch**

```yaml
# harness.yaml — defaults keep today's one-shot behavior
runtime:
  retry:
    max_attempts: 3          # default 1 = no retry; schema rejects < 1
    initial_delay_s: 1.0
    backoff: 2.0             # delay = initial_delay_s * backoff^(attempt-1)
```

```yaml
# agents/<name>/agent.yaml — optional; omit = no output validation
output:
  format: json               # parse as JSON after the stage (stdlib json only)
```

**JSON parse notes**

- Strip optional markdown code fences (e.g. ` ```json ` … ` ``` `) before `json.loads`.
- Empty assistant text fails JSON validation and is retryable.
- No JSON Schema validation in this story (`output.schema` deferred — avoids deploy copy-rule and `jsonschema` dependency).

**Libraries**

- stdlib `json` only for AC-4
- No new observability stack; no `jsonschema` dependency

### Acceptance criteria

- [ ] **AC-1** Failures raised during live stage generation (`Agent.run` / provider errors) are caught and re-raised as `WorkflowError` with `harness_name`, `agent_name`, and `stage` set (same shape as config/resolution failures). Cause chained via `__cause__`. Applies to `run_workflow` only.
- [ ] **AC-2** Optional harness-level `runtime.retry` on `harness.yaml` is applied to **each stage’s attempts**. Default `max_attempts: 1` preserves current behavior; schema enforces `max_attempts >= 1`. **Retryable:** any exception from `Agent.run` after a successful build, and output-validation failures (AC-4). **Not retryable:** model resolution, agent build, message prep/preprocess, or config errors — agent build and message construction happen **once** per stage outside the attempt loop. Backoff: `initial_delay_s × backoff^(attempt-1)`. After exhaustion, final `WorkflowError` includes attempt count.
- [ ] **AC-3** Each stage emits structured logs through `log_request()` at **INFO** for start, success, retry, and failure — with `harness`, `agent`, `model_id`, and **`stage`** (structured key required; add `stage` to `_STRUCTURED_KEYS` / `log_request`). Prompt/response **bodies are not logged** by default (lengths optional). Reconstructible stage order requires `HARNESS_LOG_LEVEL=INFO` or `zaumzeug run --verbose` (document this contract; default WARNING stays unchanged for non-stage noise).
- [ ] **AC-4** Optional `output.format: json` on `agent.yaml` validates stage text as JSON (stdlib parse; strip common markdown fences first). Invalid output (including empty text) raises typed `WorkflowError` and participates in retry (AC-2). Agents without `output` behave as today (plain `str`, no validation). **No `output.schema` / JSON Schema in this story.**
- [ ] **AC-5** When `CURRENT_SDK_PHASE < 3` and an agent declares `tools.mcp` or `tools.custom`, `zaumzeug doctor` **and** `zaumzeug doctor --deploy` **fail** (severity `fail`, non-zero exit) with a Phase 3 / unavailable message — they must **not** report a green “MCP configured and `uv` available” (or equivalent) for config that `run_workflow` would reject. The phase-gated check must run in both modes (today `mcp_uv` is skipped under `--deploy`; fix that for this failure). Uv-missing remains a separate concern once MCP is actually allowed.
- [ ] **AC-6** User-docs document `runtime.retry`, `output.format: json`, fence stripping, and the `HARNESS_LOG_LEVEL=INFO` / `--verbose` stage-log contract (include a local-Ollama-oriented example). Architecture §6.2 / §6.6 document the `runtime` and `output` config fields. Follow-up note: serve/HTTP does not yet share this reliability layer.

### Implementation tasks (build)

- [ ] Add `RuntimeRetryConfig` / `HarnessRuntimeConfig` to harness schema (`max_attempts >= 1`); wire into `run_workflow` only
- [ ] Split stage loop: build + message prep once → attempt loop around `agent.run` + optional JSON check
- [ ] Wrap live generation exceptions as `WorkflowError` (AC-1); do not retry build/config/prep failures
- [ ] Extend `log_request()` with required `stage` structured key; emit stage lifecycle at INFO; document INFO/`--verbose` contract
- [ ] Add optional `AgentOutputConfig` with `format: json` only + fence-stripping JSON validator after `_assistant_text`
- [ ] Fix doctor (default **and** `--deploy`): **fail** on phase-gated `tools.mcp` / `tools.custom`; stop false-green `mcp_uv` pass for that case
- [ ] Document `runtime.retry` and `output.format` in user-docs and Architecture §6.2 / §6.6 (AC-6)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E8-S07 / E8.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/test_workflow_reliability.py::test_e8_s07_ac1_live_generation_error_is_workflow_error` |
| AC-2 | `tests/unit/runtime/test_workflow_reliability.py::test_e8_s07_ac2_retry_then_fail` · `…::test_e8_s07_ac2_no_retry_on_config_error` · `…::test_e8_s07_ac2_default_single_attempt` · `…::test_e8_s07_ac2_build_once_then_retry_run` · `…::test_e8_s07_ac2_max_attempts_ge_one` |
| AC-2 | `tests/integration/test_workflow_reliability.py::test_e8_s07_ac2_fail_once_then_succeed` *(mock provider; mock sleep)* |
| AC-3 | `tests/unit/runtime/test_workflow_reliability.py::test_e8_s07_ac3_stage_log_request_records` *(asserts structured `stage` key)* |
| AC-4 | `tests/unit/runtime/test_workflow_reliability.py::test_e8_s07_ac4_invalid_json_retries_then_fails` · `…::test_e8_s07_ac4_strips_markdown_fence` · `…::test_e8_s07_ac4_empty_text_fails_json` · `…::test_e8_s07_ac4_no_output_config_skips_validation` |
| AC-5 | `tests/unit/cli/test_doctor.py::test_e8_s07_ac5_phase_gated_mcp_fails_not_false_pass` · `…::test_e8_s07_ac5_phase_gated_mcp_fails_in_deploy_mode` |
| AC-6 | **manual:** user-docs cover retry / `output.format` / fence strip / INFO log contract + Ollama example; Architecture §6.2 / §6.6 document `runtime` + `output`; serve follow-up noted |
| Regression | `pytest tests/integration/test_workflow_run.py -v` passes (E3-S08 unchanged with defaults) |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/runtime/test_workflow_reliability.py tests/integration/test_workflow_reliability.py tests/unit/cli/test_doctor.py -k e8_s07 -v` passes
- [ ] `pytest tests/integration/test_workflow_run.py -v` passes

### Definition of done

- [ ] Defaults preserve pre-story behavior (`max_attempts: 1`, no `output` → no validation)
- [ ] Existing E3-S08 workflow integration tests still pass
- [ ] Run-path only — no claim that serve/HTTP shares retry/validation yet (follow-up noted in user-docs)
- [ ] User-docs cover `runtime.retry`, `output.format: json`, fence stripping, and `HARNESS_LOG_LEVEL=INFO` / `--verbose` for stage logs (local-Ollama-oriented example)
- [ ] Architecture §6.2 / §6.6 document `runtime` and `output`
- [ ] No OpenTelemetry dependency or span API; no `jsonschema` dependency
- [ ] Verification checklist complete; all ACs traced to tests

---
