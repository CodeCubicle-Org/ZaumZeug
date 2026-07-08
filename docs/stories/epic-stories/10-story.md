# E3-S01 — ModelRouter

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/10-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-08 |
| **Story ID** | E3-S01 |
| **Status** | Done |
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
| **Status** | Done (2026-07-08) |

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
- [openai-haystack](https://pypi.org/project/openai-haystack/) — also used for **local OpenAI-compatible** servers (LM Studio, Ollama, vLLM) via `api_base_url`
- [anthropic-haystack](https://pypi.org/project/anthropic-haystack/)
- [LM Studio local server](https://lmstudio.ai/docs/app/api/endpoints/openai) (default `http://localhost:1234/v1`)
- [LiteLLM provider strings](https://docs.litellm.ai/docs/providers) (compile-time LM wiring in Phase 2)
- [Architecture §7 — ModelRouter](../../architecture/05-configuration.md#7-model-routing)

**Code sketch — provider map**

```python
PROVIDERS = {
    "mock": ("zaumzeug.integrations.mock", "MockChatGenerator"),
    "openrouter": ("haystack_integrations.components.generators.openrouter", "OpenRouterChatGenerator"),
    "openai_compatible": ("haystack.components.generators.chat", "OpenAIChatGenerator"),
}
```

**Config sketch — local dev (LM Studio)**

```yaml
# agents/<name>/agents-models.yaml — opt-in; not in shipped models.example.yaml (CI stays mock-only)
default_model_id: local

models:
  local:
    provider: openai_compatible
    model: your-loaded-model-id          # as shown in LM Studio
    api_base_url: http://localhost:1234/v1
```

`.env`: `OPENAI_API_KEY=lm-studio` (or any placeholder — local servers usually ignore it).

### Phase 1 provider allowlist

| Provider id | Phase | Notes |
|---|---|---|
| `mock` | 1 | Default for CI and example harness ([E3-S05](09-story.md)) |
| `openrouter` | 1 | Hosted models via OpenRouter API key in `.env` |
| `openai_compatible` | 1 | Local or self-hosted OpenAI-compatible APIs (LM Studio, Ollama, vLLM); `api_base_url` in YAML; API key optional for localhost |
| `openai`, `anthropic`, etc. | 2+ | Native cloud providers — phase-gated; fail with phase hint if configured in Phase 1 |

### Acceptance criteria

- [x] **AC-1** Stage-scoped `ModelRouter` reads active agent's merged `agents-models.yaml`
- [x] **AC-2** Lazy-builds Haystack `ChatGenerator` per provider
- [x] **AC-3** OpenRouter via `openrouter-haystack` when registry entry uses `provider: openrouter`
- [x] **AC-4** `openai_compatible` via `openai-haystack` when registry entry uses `provider: openai_compatible`; `api_base_url` from YAML (or `OPENAI_API_BASE` in `.env`); suitable for LM Studio and other local OpenAI-compatible servers
- [x] **AC-5** Caches generator instances per provider + endpoint (distinct `api_base_url` values do not share a cache entry)
- [x] **AC-6** Fails fast with actionable message if provider package missing (include `pip install …` hint)
- [x] **AC-7** No hardcoded model names in SDK source
- [x] **AC-8** OpenAI API: optional request `model_id` selects LLM; harness name remains agent identity *(routing layer — full HTTP contract in [E3-S07](16-story.md))*

### Implementation tasks (build)

- [x] Extend `src/zaumzeug/runtime/model_router.py` *(mock provider done in E3-S05)*
- [x] Implement provider map in `src/zaumzeug/integrations/haystack.py` (`provider` → import + generator class)
- [x] Add optional `api_base_url` to `ModelEntryConfig` (non-secret; required for `openai_compatible`)
- [x] Load secrets from `.env` via stdlib `os.environ` — never from YAML

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S01 / E3.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac1_config_model_id_and_request_override` |
| AC-2 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac2_lazy_build_generator` |
| AC-3 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac3_openrouter_provider_path` |
| AC-4 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac4_openai_compatible_local_provider_path` *(also `test_e3_s01_ac4_openai_compatible_env_base_url`, `test_e3_s01_ac4_openai_compatible_requires_base_url`)*
| AC-5 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac5_generator_cache_per_provider_endpoint` |
| AC-6 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac6_missing_package_install_hint` *(also `test_e3_s01_ac6_phase_gated_native_provider`)*
| AC-7 | `tests/unit/runtime/test_model_router.py::test_e3_s01_ac7_no_hardcoded_model_names` |
| AC-8 | `tests/integration/test_openai_contract.py::test_e3_s01_ac8_request_model_id_override` *(routing helper; full `POST /v1/chat/completions` in E3-S07)* |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/runtime/test_model_router.py -v -k e3_s01` passes

### Definition of done

- [x] Missing `openrouter-haystack` / `openai-haystack` produces install hint, not stack trace
- [x] Verification checklist complete; all ACs traced to tests

---
