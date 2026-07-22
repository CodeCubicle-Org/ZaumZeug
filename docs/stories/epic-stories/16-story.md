# E3-S07 — OpenAI REST contract tests

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/16-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-22 |
| **Story ID** | E3-S07 |
| **Status** | Done |
| **Epic** | [E3 — Runtime and Local Serve](../02-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 2 of 8 |
| **Story sequence** | 16 of 63 (global build order) |
| **Source** | Extracted from [`02-epic.md`](../02-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1) · [Architecture](../../architecture.md) · **DoD closed by** [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) |

---

## E3-S07 — OpenAI REST contract tests

| Field | Value |
|---|---|
| **Feature** | PRD E3 story seed |
| **Persona** | SDK maintainer |
| **Priority** | P1 |
| **Prerequisites** | [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) · [E3-S05](09-story.md#e3-s05-mock-model-profile) |
| **Status** | Done (2026-07-21) |
| **Open — carried forward** | — |
| **Closed by E1-S07** | [DoD *Green on all three OS*](#definition-of-done) → [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) (2026-07-22) |

### User story

As an **SDK maintainer**, I want automated OpenAI-shaped request/response tests, so that client integrators can rely on a stable REST contract.

### References

- [PRD E3 story seeds](../../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §9.4 — OpenAI-compatible](../../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)


### Implementation resources

**Libraries & docs**

- [OpenAI Chat Completions — response shape](https://platform.openai.com/docs/api-reference/chat/object)
- [httpx](https://www.python-httpx.org/) · [pytest-httpx / respx](https://lundberg.github.io/respx/) for stubbing `web_fetch`
- [Architecture §9.4 — OpenAI-compatible layouts](../../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)

**Minimal response shape to assert**

```json
{"choices": [{"message": {"role": "assistant", "content": "..."}}]}
```

### Acceptance criteria

- [x] **AC-1** Integration test POST `/v1/chat/completions` with mock model returns expected JSON shape (`choices`, `message`, `role`, `content`)
- [x] **AC-2** Test accepts optional `model_id` in request body for ModelRouter override
- [x] **AC-3** Test runs in CI without network (mock model, stub `web_fetch` if tool invoked)

### Implementation tasks (build)

- [x] Add `tests/integration/test_openai_contract.py`
- [x] Start serve on ephemeral port via subprocess or test fixture
- [x] Stub HTTP for `web_fetch` when tool invoked in contract tests
- [x] Wire request `model_id` through `AgentPipelineWrapper.run_chat_completion` → ModelRouter

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S07`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_openai_contract.py::test_e3_s07_ac1_chat_completions_openai_shape` |
| AC-2 | `tests/integration/test_openai_contract.py::test_e3_s07_ac2_request_model_id_override` |
| AC-3 | `tests/integration/test_openai_contract.py::test_e3_s07_ac3_no_network_mock_and_stub_fetch` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/test_openai_contract.py -v` passes

### Definition of done

- [x] Green on all three OS in CI matrix *(closed by [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) — matrix runs `pytest tests/integration/test_openai_contract.py` — Done 2026-07-22)*
- [x] Verification checklist complete; all ACs traced to tests

---
