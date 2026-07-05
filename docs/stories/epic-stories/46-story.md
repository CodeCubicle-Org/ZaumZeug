# E5-S06 — Deploy eval gate

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/46-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E5-S06 |
| **Epic** | [E5 — Deploy Packaging](../06-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 6 of 8 |
| **Story sequence** | 46 of 63 (global build order) |
| **Source** | Extracted from [`06-epic.md`](../06-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E5](../../prd.md#epic-e5--deploy-packaging-phase-2) · [Architecture](../../architecture.md) |

---

## E5-S06 — Deploy eval gate

| Field | Value |
|---|---|
| **Feature** | E5.6 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command) |

### User story

As a **harness developer**, I want configurable eval gates on deploy, so that I can optionally block shipping when regression tests fail.

### References

- [PRD E5.6](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §6.4 — Deploy eval gate](../../architecture/05-configuration.md#64-deploy-eval-gate)
- [E6-S02 — zaumzeug eval](../05-epic.md#e6-s02-zaumzeug-eval-command)


### Implementation resources

**Libraries & docs**

- [DeepEval CLI / thresholds](https://docs.confident-ai.com/)
- [Architecture §6.4 — deploy eval gate](../../architecture/05-configuration.md#64-deploy-eval-gate)
- Requires [E6-S02](35-story.md) `zaumzeug eval` before gate can run

**Config example**

```yaml
deploy:
  eval_gate: block   # skip | warn | block
```

### Acceptance criteria

- [ ] **AC-1** `deploy.eval_gate`: `skip` | `warn` | `block` behaves per §6.4
- [ ] **AC-2** CLI override: `zaumzeug deploy <name> --eval-gate block`
- [ ] **AC-3** If no `eval` section, `block` is no-op
- [ ] **AC-4** `warn` continues deploy after printing failures

### Implementation tasks (build)

- [ ] Add eval gate to deploy packager pre-step
- [ ] Wire to `zaumzeug eval` when configured

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S06 / E5.6` *(shared E6-S03)*.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/deploy/test_eval_gate.py::test_e5_s06_ac1_skip_warn_block_behaviors` |
| AC-2 | `tests/unit/deploy/test_eval_gate.py::test_e5_s06_ac2_cli_override_eval_gate` |
| AC-3 | `tests/unit/deploy/test_eval_gate.py::test_e5_s06_ac3_block_noop_without_eval_section` |
| AC-4 | `tests/unit/deploy/test_eval_gate.py::test_e5_s06_ac4_warn_continues_after_failures` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/deploy/test_eval_gate.py -v` passes

### Definition of done

- [ ] Covered by E6-S03 cross-reference
- [ ] Verification checklist complete; all ACs traced to tests

---
