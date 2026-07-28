# E8-S06 — DeepEval production observe (opt-in)

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/63-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E8-S06 |
| **Epic** | [E8 — RAG and Production Hardening](../08-epic.md) |
| **Phase** | 4 |
| **Epic build order** | 8 of 8 |
| **Story sequence** | 63 of 63 (global build order) |
| **Source** | Extracted from [`08-epic.md`](../08-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E8](../../prd.md#epic-e8--rag-and-production-hardening-phase-4) · [Architecture](../../architecture.md) |

---

## E8-S06 — DeepEval production observe (opt-in)

| Field | Value |
|---|---|
| **Feature** | E8.6 |
| **Persona** | Harness developer |
| **Priority** | P3 |
| **Prerequisites** | [E6-S01](34-story.md#e6-s01-optional-eval-extra) ✅ · [E5-S09c](49.3-story.md#e5-s09c-target-install-verify-integration) |

### User story

As a **harness developer**, I want optional DeepEval `@observe` in production, so that I can sync traces to Confident AI when explicitly opted in.

### References

- [PRD E8.6](../../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §6.3 — Mode B tracing](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)
- [DeepEval](https://github.com/confident-ai/deepeval)


### Implementation resources

**Libraries & docs**

- [DeepEval `@observe` decorator](https://docs.confident-ai.com/docs/tracing)
- [Confident AI](https://www.confident-ai.com/docs)
- [Architecture §6.3 — Mode B tracing](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)

### Acceptance criteria

- [ ] **AC-1** Opt-in only — not default for production ([PRD NG2](../../prd.md#4-non-goals-v1))
- [ ] **AC-2** `@observe` + Confident AI sync when `eval.confident_ai.enabled`
- [ ] **AC-3** Requires `deepeval login` and `[eval]` extra on server if enabled
- [ ] **AC-4** Document privacy and cost implications
- [ ] **AC-5** Default production deploy has no DeepEval dependency (E5-S05)

### Implementation tasks (build)

- [ ] Wrap agent run path with optional observe decorator
- [ ] Config gate: explicit `serve.observability.deepeval: true` or similar
- [ ] Warn in doctor when enabled without credentials

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E8-S06 / E8.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_observe.py::test_e8_s06_ac1_observe_off_by_default` |
| AC-2 | `tests/unit/eval/test_observe.py::test_e8_s06_ac2_observe_when_confident_ai_enabled` |
| AC-3 | `tests/unit/cli/test_doctor.py::test_e8_s06_ac3_doctor_warns_missing_deepeval_login` |
| AC-4 | **manual:** user-docs privacy and cost section |
| AC-5 | **shared:** `tests/integration/deploy/test_target_install.py::test_e5_s05_ac3_no_dspy_gepa_deepeval` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/eval/test_observe.py -v` passes

### Definition of done

- [ ] Default production deploy has no DeepEval dependency (E5-S05)
- [ ] Verification checklist complete; all ACs traced to tests
