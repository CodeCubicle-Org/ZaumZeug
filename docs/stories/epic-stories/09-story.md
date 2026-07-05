# E3-S05 — Mock model profile

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/09-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E3-S05 |
| **Epic** | [E3 — Runtime and Local Serve](../02-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 2 of 8 |
| **Story sequence** | 9 of 63 (global build order) |
| **Source** | Extracted from [`02-epic.md`](../02-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1) · [Architecture](../../architecture.md) |

---

## E3-S05 — Mock model profile

| Field | Value |
|---|---|
| **Feature** | E3.5 |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S02](03-story.md#e2-s02-modelsyaml-merge) |

### User story

As an **SDK maintainer**, I want a mock model in the registry, so that CI and first-run docs never require live API keys.

### References

- [PRD E3.5](../../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §6.6](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [Architecture §7 — Mock profile](../../architecture/05-configuration.md#7-model-routing)
- [Architecture §13.2 — Mock profile](../../architecture/10-operations-and-reference.md#132-mechanisms)


### Implementation resources

**Config example — mock profile**

```yaml
# agents-models.yaml
default_model_id: mock
models:
  mock:
    provider: mock
    model: harness-fixture
```

- [Architecture §6.6 — example harness mock setup](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [Architecture §13.2 — mock profile mechanism](../../architecture/10-operations-and-reference.md#132-mechanisms)

### Acceptance criteria

- [ ] **AC-1** `models.yaml` defines `mock` provider per §6.6
- [ ] **AC-2** Canned responses from `tests/fixtures/responses/`
- [ ] **AC-3** CI matrix uses mock exclusively ([E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix))
- [ ] **AC-4** Mock works without provider Haystack integration packages

### Implementation tasks (build)

- [ ] Implement mock `ChatGenerator` in `src/zaumzeug/runtime/model_router.py`
- [ ] Add fixture JSON/text under `tests/fixtures/responses/` for deterministic assertions
- [ ] Ship `mock` entry in `install/templates/config/models.example.yaml`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S05 / E3.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/test_model_router.py::test_e3_s05_ac1_mock_provider_in_registry` |
| AC-2 | `tests/unit/runtime/test_model_router.py::test_e3_s05_ac2_returns_fixture_response` |
| AC-3 | **shared:** traced in [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) workflow (mock-only jobs) |
| AC-4 | `tests/unit/runtime/test_model_router.py::test_e3_s05_ac4_no_provider_package_required` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/runtime/test_model_router.py -v -k e3_s05` passes

### Definition of done

- [ ] ModelRouter returns fixture response for `model_id: mock`
- [ ] Verification checklist complete; all ACs traced to tests

---
