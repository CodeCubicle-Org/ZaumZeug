# E7-S04 — Chainlit embedded UI

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/53-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E7-S04 |
| **Epic** | [E7 — Tools, MCP, and ACP](../07-epic.md) |
| **Phase** | 3 |
| **Epic build order** | 7 of 8 |
| **Story sequence** | 53 of 63 (global build order) |
| **Source** | Extracted from [`07-epic.md`](../07-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E7](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3) · [Architecture](../../architecture.md) |

---

## E7-S04 — Chainlit embedded UI

| Field | Value |
|---|---|
| **Feature** | E7.4 |
| **Persona** | Client integrator |
| **Priority** | P2 |
| **Prerequisites** | [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) |

### User story

As a **web integrator**, I want optional Chainlit at `/chat`, so that I get a quick GUI on the same port as the API.

### References

- [PRD E7.4](../../prd.md#epic-e7--tools-mcp-and-acp-phase-3)
- [Architecture §9.4 — Chainlit embedded](../../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)
- [PRD open #2](../../prd.md#12-open-decisions-blockers-for-some-stories)


### Implementation resources

**Libraries & docs**

- [Chainlit](https://docs.chainlit.io/)
- [Hayhooks Chainlit extra](https://docs.haystack.deepset.ai/docs/hayhooks) — `pip install "hayhooks[chainlit]"`
- [Architecture §9.4 — embedded UI layout](../../architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)

### Acceptance criteria

- [ ] **AC-1** `serve.hayhooks.chainlit: true` serves `/chat` on same port as REST
- [ ] **AC-2** Document `pip install "hayhooks[chainlit]"` as optional extra
- [ ] **AC-3** OpenAI REST remains available alongside Chainlit

### Implementation tasks (build)

- [ ] Wire Chainlit flag in serve runner
- [ ] Document in web deployment guide (E7-S08)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S04 / E7.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/serve/test_chainlit.py::test_e7_s04_ac1_chat_route_loads` |
| AC-2 | **manual:** user-docs lists hayhooks chainlit extra |
| AC-3 | `tests/integration/serve/test_chainlit.py::test_e7_s04_ac3_openai_rest_still_available` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/serve/test_chainlit.py -v` passes

### Definition of done

- [ ] Align docs with open #2 primary web UI decision when resolved
- [ ] Verification checklist complete; all ACs traced to tests

---
