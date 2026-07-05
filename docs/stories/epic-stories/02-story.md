# E2-S01 — Pydantic config schemas

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/02-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E2-S01 |
| **Epic** | [E2 — Configuration and Validation](../01-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 1 of 8 |
| **Story sequence** | 2 of 63 (global build order) |
| **Source** | Extracted from [`01-epic.md`](../01-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E2](../../prd.md#epic-e2--configuration-and-validation-phase-1) · [Architecture](../../architecture.md) |

---

## E2-S01 — Pydantic config schemas

| Field | Value |
|---|---|
| **Feature** | E2.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation) |

### User story

As a **harness developer**, I want invalid YAML to fail with field-level errors, so that I can fix config without reading SDK source.

### References

- [PRD E2.1](../../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §6.6 — Phase 1 schema](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [Architecture §6.2 — Config sections](../../architecture/05-configuration.md#62-config-sections)
- [Ideation — full YAML examples](../../ideation-stage.md)


### Implementation resources

**Libraries & docs**

- [Pydantic v2 models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic validation errors](https://docs.pydantic.dev/latest/concepts/validation_errors/)
- [PyYAML safe_load](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [Architecture §6.6 — Phase 1 YAML examples](../../architecture/05-configuration.md#66-phase-1-config-schema)
- [Ideation — full multi-phase YAML](../../ideation-stage.md)

**Code sketch — loader**

```python
from pathlib import Path
import yaml
from zaumzeug.config.schemas import HarnessConfig

def load_harness(path: Path) -> HarnessConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return HarnessConfig.model_validate(data)
```

### Acceptance criteria

- [ ] **AC-1** Invalid `harness.yaml` fails with Pydantic field-level errors
- [ ] **AC-2** Phase 1 minimal example from §6.6 passes validation
- [ ] **AC-3** Unknown sections/fields for current phase fail with phase hint (e.g. “`compile` is Phase 2”)
- [ ] **AC-4** Config validation error clarity meets [PRD §11](../../prd.md#11-success-metrics)

### Implementation tasks (build)

- [ ] Implement schemas in `src/zaumzeug/config/schemas.py`
- [ ] Implement loader in `src/zaumzeug/config/loader.py` (read yaml, invoke schemas, resolve paths via `pathlib`)
- [ ] Phase-gated field allowlists per epic/phase map

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S01 / E2.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_schemas.py::test_e2_s01_ac1_invalid_yaml_field_errors` |
| AC-2 | `tests/unit/config/test_schemas.py::test_e2_s01_ac2_phase1_minimal_valid` |
| AC-3 | `tests/unit/config/test_schemas.py::test_e2_s01_ac3_unknown_key_phase_hint` |
| AC-4 | `tests/unit/config/test_schemas.py::test_e2_s01_ac4_error_includes_path_and_field` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/config/test_schemas.py -v` passes

### Definition of done

- [ ] Example harness config passes
- [ ] Error messages include file path and field name
- [ ] Verification checklist complete; all ACs traced to tests

---
