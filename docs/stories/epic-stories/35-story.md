# E6-S02 — `zaumzeug eval` command

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/35-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E6-S02 |
| **Epic** | [E6 — Evaluation and Quality (Optional)](../05-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 5 of 8 |
| **Story sequence** | 35 of 63 (global build order) |
| **Source** | Extracted from [`05-epic.md`](../05-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E6](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional) · [Architecture](../../architecture.md) |

---

## E6-S02 — `zaumzeug eval` command

| Field | Value |
|---|---|
| **Feature** | E6.2 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E6-S01](34-story.md#e6-s01-optional-eval-extra) ✅ · [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) ✅ |

### User story

As a **harness developer**, I want `zaumzeug eval`, so that I can run builtin JSONL checks or DeepEval metrics without shipping eval to production.

### References

- [PRD E6.2](../../prd.md#epic-e6--evaluation-and-quality-phase-2-optional)
- [Architecture §6.3](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)


### Implementation resources

**Libraries & docs**

- [DeepEval docs](https://docs.confident-ai.com/)
- [DeepEval metrics](https://docs.confident-ai.com/docs/metrics-introduction)
- [Architecture §6.3 — eval frameworks](../../architecture/05-configuration.md#63-zaumzeug-eval-frameworks)

### Acceptance criteria

- [ ] **AC-1** `eval.framework: deepeval` requires `[eval]` extra; shows install hint if missing
- [ ] **AC-2** `eval.framework: builtin` runs JSONL checks without DeepEval
- [ ] **AC-3** Missing `eval` section → clear error exit
- [ ] **AC-4** CLI override: `zaumzeug eval <name> --framework builtin`
- [ ] **AC-5** Default framework `deepeval` when `eval:` present and `framework` omitted

### Implementation tasks (build)

- [ ] Implement `src/zaumzeug/eval/runner.py` ([Architecture §11 #10](../../architecture/09-sdk-module-map.md#11-sdk-modules-to-build))
- [ ] Builtin: load `eval.valset` JSONL; exact/substring match on `expected_output`
- [ ] DeepEval: wire configured metrics and thresholds

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E6-S02 / E6.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/eval/test_runner.py::test_e6_s02_ac1_deepeval_missing_extra_hint` |
| AC-2 | `tests/unit/eval/test_runner.py::test_e6_s02_ac2_builtin_jsonl_checks` |
| AC-3 | `tests/unit/eval/test_runner.py::test_e6_s02_ac3_missing_eval_section_error` |
| AC-4 | `tests/unit/eval/test_runner.py::test_e6_s02_ac4_cli_framework_override` |
| AC-5 | `tests/unit/eval/test_runner.py::test_e6_s02_ac5_default_deepeval_when_omitted` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/eval/test_runner.py -v` passes

### Definition of done

- [ ] Eval never runs on production serve path ([PRD NG3 adjacent — compile on prod](../../prd.md#4-non-goals-v1))
- [ ] Verification checklist complete; all ACs traced to tests

---
