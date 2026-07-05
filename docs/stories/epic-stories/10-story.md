# E3-S01 — ModelRouter

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/10-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E3-S01 |
| **Epic** | [E3 — Runtime and Local Serve](../02-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 2 of 8 |
| **Story sequence** | 10 of 63 (global build order) |
| **Source** | Extracted from [`02-epic.md`](../02-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1) · [Architecture](../../architecture.md) |

---

## E3-S01 — ModelRouter

| Field | Value |
|---|---|
| **Feature** | E3.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E3-S05](09-story.md#e3-s05-mock-model-profile) · [E2-S02](03-story.md#e2-s02-modelsyaml-merge) |

### User story

As a **harness developer**, I want a config-driven ModelRouter, so that I can switch LLM providers without code changes.

### References

- [PRD E3.1](../../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §7](../../architecture/05-configuration.md#7-model-routing)
- [Architecture §4.4](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)
- [Architecture §11 #3](../../architecture/09-sdk-module-map.md#11-sdk-modules-to-build)



### Implementation resources

**Libraries & docs**

- [Haystack Chat Generators](https://docs.haystack.deepset.ai/docs/chatgenerators)
- [openrouter-haystack](https://pypi.org/project/openrouter-haystack/)
- [openai-haystack](https://pypi.org/project/openai-haystack/) · [anthropic-haystack](https://pypi.org/project/anthropic-haystack/)
- [LiteLLM provider strings](https://docs.litellm.ai/docs/providers) (compile-time LM wiring in Phase 2)
- [Architecture §7 — ModelRouter](../../architecture/05-configuration.md#7-model-routing)

**Code sketch — provider map**

```python
PROVIDERS = {
    "mock": ("zaumzeug.integrations.mock", "MockChatGenerator"),
    "openrouter": ("haystack_integrations.components.generators.openrouter", "OpenRouterChatGenerator"),
}
```

### Phase 1 provider allowlist

| Provider id | Phase | Notes |
|---|---|---|
| `mock` | 1 | Default for CI and example harness ([E3-S05](09-story.md)) |
| `openrouter` | 1 | Live models via OpenRouter API key in `.env` |
| `openai`, `anthropic`, etc. | 2+ | Phase-gated — fail with phase hint if configured in Phase 1 |

### Acceptance criteria

- [ ] **AC-1** Stage-scoped `ModelRouter` reads active agent's merged `agents-models.yaml`
- [ ] **AC-2** Lazy-builds Haystack `ChatGenerator` per provider
- [ ] **AC-3** OpenRouter via `openrouter-haystack` when registry entry uses `provider: openrouter`
- [ ] **AC-4** Caches generator instances per provider
- [ ] **AC-5** Fails fast with actionable message if provider package missing (include `pip install …` hint)
- [ ] **AC-6** No hardcoded model names in SDK source
- [ ] **AC-7** OpenAI API: optional request `model_id` selects LLM; harness name remains agent identity

### Implementation tasks (build)

- [ ] Implement `src/zaumzeug/runtime/model_router.py`
- [ ] Implement provider map in `src/zaumzeug/integrations/haystack.py` (`provider` → import + generator class)
- [ ] Load secrets from `.env` via `python-dotenv` or stdlib — never from YAML

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S01 / E3.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac1_config_model_id_and_request_override` |
| AC-2 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac2_lazy_build_generator` |
| AC-3 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac3_openrouter_provider_path` |
| AC-4 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac4_generator_cache_per_provider` |
| AC-5 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac5_missing_package_install_hint` |
| AC-6 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac6_no_hardcoded_model_names` |
| AC-7 | `tests/integration/test_openai_contract.py::test_e3_s01_ac7_request_model_id_override` *(shared with E3-S07)* |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/runtime/test_model_router.py -v -k e3_s01` passes

### Definition of done

- [ ] Missing `openai-haystack` produces install hint, not stack trace
- [ ] Verification checklist complete; all ACs traced to tests

---
