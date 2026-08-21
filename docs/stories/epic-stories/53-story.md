# E7-S04 — Chainlit embedded UI

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/53-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-08-21 |
| **Story ID** | E7-S04 |
| **Status** | Done (2026-08-21) |
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

- [x] **AC-1** `serve.hayhooks.chainlit: true` serves `/chat` on same port as REST
- [x] **AC-2** Document `pip install "hayhooks[chainlit]"` as optional extra
- [x] **AC-3** OpenAI REST remains available alongside Chainlit

### Implementation tasks (build)

- [x] Wire Chainlit flag in serve runner
- [x] Document in web deployment guide (E7-S08)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E7-S04 / E7.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/serve/test_chainlit.py::test_e7_s04_ac1_chat_route_loads` |
| AC-2 | **manual + automated:** user-docs list `pip install "hayhooks[chainlit]"` — [web-deployment.md](../../../user-docs/guides/web-deployment.md) and [installation.md](../../../user-docs/getting-started/installation.md); `test_e7_s04_ac2_user_docs_list_chainlit_extra` |
| AC-3 | `tests/integration/serve/test_chainlit.py::test_e7_s04_ac3_openai_rest_still_available` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/serve/test_chainlit.py -v` passes
- [x] Full suite `pytest tests -q` (2026-08-21): 327 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate)

### Definition of done

- [x] Align docs with open #2 primary web UI decision when resolved — **open #2 remains open**; Chainlit is documented as an **optional** layout, not a product default (Open WebUI / SPA / Next.js recipes **Done** E7-S08)
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-08-21)

- `HayhooksConfig.chainlit` (default `false`) unblocked from `PHASE_GATED_FIELDS`. `CURRENT_SDK_PHASE` stays **1**.
- `serve/runner.py` sets Hayhooks `chainlit_enabled` / `chainlit_path=/chat` / `chainlit_default_model=<harness>` **before** `create_app()`. Missing extra raises `ChainlitMissingError` with `pip install "hayhooks[chainlit]"`.
- CI tests stub the Hayhooks Chainlit mount so the default `[dev]` install stays lean; REST + `/chat` still share one FastAPI app.
- Guide: [web-deployment.md](../../../user-docs/guides/web-deployment.md) (mirrored in `install/templates/user-docs/guides/`).
- Full suite 2026-08-21: 327 passed, 1 skipped (`HARNESS_LIVE_LLM` e2e gate).

---
