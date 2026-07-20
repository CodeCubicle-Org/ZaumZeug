# E3-S00 — Runtime factory (Haystack Agent builder)

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/12-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-20 |
| **Story ID** | E3-S00 |
| **Status** | Done |
| **Epic** | [E3 — Runtime and Local Serve](../02-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 2 of 8 |
| **Story sequence** | 12 of 63 (global build order) |
| **Source** | Extracted from [`02-epic.md`](../02-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1) · [Architecture](../../architecture.md) |

---

## E3-S00 — Runtime factory (Haystack Agent builder)

| Field | Value |
|---|---|
| **Feature** | Foundation (Architecture §11 #4) |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E3-S01](10-story.md#e3-s01-modelrouter) · [E3-S03](11-story.md#e3-s03-builtin-tool-web_fetch) · [E2-S03](04-story.md#e2-s03-runtime-agent-resolution-rules) |
| **Status** | Done (2026-07-20) |

### User story

As an **SDK maintainer**, I want a runtime factory that builds a Haystack `Agent` from resolved config, so that serve/MCP/ACP share one code path.

### References

- [Architecture §11 #4 — Runtime factory](../../architecture/09-sdk-module-map.md#11-sdk-modules-to-build)
- [Architecture §2.1 — Golden rules](../../architecture/01-overview-and-principles.md#21-golden-rules)
- [Architecture §2.3 — Agent loop](../../architecture/01-overview-and-principles.md#23-harness-layer-mapping-guides-and-sensors)
- [Haystack Agents](https://docs.haystack.deepset.ai/docs/agents)


### Implementation resources

**Libraries & docs**

- [Haystack Agents](https://docs.haystack.deepset.ai/docs/agents)
- [Haystack Agent — running tools](https://docs.haystack.deepset.ai/docs/agents#adding-tools-to-an-agent)
- [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks)
- [Architecture §2.3 — agent loop mapping](../../architecture/01-overview-and-principles.md#23-harness-layer-mapping-guides-and-sensors)

**Code sketch — factory**

```python
from haystack.components.agents import Agent

def build_agent(*, chat_generator, tools, system_prompt: str) -> Agent:
    return Agent(chat_generator=chat_generator, tools=tools, system_prompt=system_prompt)
```

### Acceptance criteria

- [x] **AC-1** `src/zaumzeug/runtime/factory.py` builds Haystack `Agent` from harness config
- [x] **AC-2** Injects `ModelRouter` as chat generator backend
- [x] **AC-3** Registers builtin tools from `tools.builtin`
- [x] **AC-4** Loads `system_prompt` from resolved file path (E2-S03)
- [x] **AC-5** **No DSPy or GEPA imports** in this module
- [x] **AC-6** **No double agent loops** — single Haystack Agent only

### Implementation tasks (build)

- [x] Implement `build_agent(harness_dir, *, harness_name, agent_name, router) -> Agent` in `runtime/factory.py`
- [x] Wire `config/resolver.py` for prompt path
- [x] Wire `runtime/tools/catalog.py` for builtins

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S00`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac1_builds_agent_from_config` |
| AC-2 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac2_injects_model_router` |
| AC-3 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac3_registers_builtin_tools` |
| AC-4 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac4_loads_system_prompt_from_path` |
| AC-5 | `tests/unit/runtime/test_factory_imports.py::test_e3_s00_ac5_no_dspy_gepa_imports` |
| AC-6 | `tests/integration/test_runtime_factory.py::test_e3_s00_ac6_single_agent_no_nested_loops` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/test_runtime_factory.py tests/unit/runtime/test_factory_imports.py -v` passes

### Definition of done

- [x] Used by `serve/runner.py` ([E3-S02](13-story.md#definition-of-done), 2026-07-20) — not duplicated in serve layer
- [x] Verification checklist complete; all ACs traced to tests
- [x] Reuses `zaumzeug.config.resolver` in `build_agent()`; when complete, check off [E2-S03](04-story.md#definition-of-done) DoD *serve uses same resolution logic*

---
