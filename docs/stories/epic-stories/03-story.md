# E2-S02 — `models.yaml` merge

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/03-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E2-S02 |
| **Epic** | [E2 — Configuration and Validation](../01-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 1 of 8 |
| **Story sequence** | 3 of 63 (global build order) |
| **Source** | Extracted from [`01-epic.md`](../01-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E2](../../prd.md#epic-e2--configuration-and-validation-phase-1) · [Architecture](../../architecture.md) |

---

## E2-S02 — `models.yaml` merge

| Field | Value |
|---|---|
| **Feature** | E2.2 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation) |

### User story

As a **harness developer**, I want global, harness, and per-agent model registries to deep-merge, so that each agent can use a different LLM without duplicating the full registry.

### References

- [PRD E2.2](../../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §6.1 — Merge rules](../../architecture/05-configuration.md#61-model-registry-merge)
- [Architecture §3.3.1](../../architecture/02-repository-and-layout.md#331-model-config-files-naming)


### Implementation resources

**Internal spec**

- [Architecture §6.1 — deep-merge rules](../../architecture/05-configuration.md#61-model-registry-merge)
- [Architecture §3.3.1 — model file naming](../../architecture/02-repository-and-layout.md#331-model-config-files-naming)

**Code sketch — recursive merge**

```python
def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out
```

### Acceptance criteria

- [ ] **AC-1** Global `config/models.yaml` deep-merges with harness `models.yaml` (when present)
- [ ] **AC-2** Per-agent `agents/<name>/agents-models.yaml` deep-merges over harness + global
- [ ] **AC-3** Nested dicts merge recursively; child keys win
- [ ] **AC-4** Lists in child file **replace** parent lists entirely
- [ ] **AC-5** Each agent's `default_model_id` validated against that agent's merged registry

### Implementation tasks (build)

- [ ] Implement merge in `src/zaumzeug/config/models.py`
- [ ] Support `models: models.yaml` file reference in `harness.yaml`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S02 / E2.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac1_global_harness_deep_merge` |
| AC-2 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac2_nested_dict_harness_wins` |
| AC-3 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac3_list_replace_not_append` |
| AC-4 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac4_same_model_id_override` |
| AC-5 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac5_missing_default_model_id_fails` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/config/test_models_merge.py -v` passes

### Definition of done

- [ ] Merge rules covered by unit tests ([PRD story seed](../../prd.md#epic-e2--configuration-and-validation-phase-1))
- [ ] Secrets never loaded from YAML (`.env` only)
- [ ] Verification checklist complete; all ACs traced to tests

---
