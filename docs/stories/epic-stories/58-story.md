# E8-S01 — Pipeline exposure via `serve.expose`

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/58-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E8-S01 |
| **Epic** | [E8 — RAG and Production Hardening](../08-epic.md) |
| **Phase** | 4 |
| **Epic build order** | 8 of 8 |
| **Story sequence** | 58 of 63 (global build order) |
| **Source** | Extracted from [`08-epic.md`](../08-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E8](../../prd.md#epic-e8--rag-and-production-hardening-phase-4) · [Architecture](../../architecture.md) |

---

## E8-S01 — Pipeline exposure via `serve.expose`

| Field | Value |
|---|---|
| **Feature** | E8.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E5-S02](42-story.md#e5-s02-dev-vs-deploy-copy-rules) · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) |

### User story

As a **harness developer**, I want user pipelines exposed via config, so that I can ship RAG and batch flows alongside the agent.

### References

- [PRD E8.1](../../prd.md#epic-e8--rag-and-production-hardening-phase-4)
- [Architecture §3.3 — `pipelines/`](../../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- [Architecture §10.1 — pipeline copy rules](../../architecture/07-deploy-packaging.md#101-dev-vs-deploy)
- [Haystack Pipelines](https://docs.haystack.deepset.ai/docs/pipelines)


### Implementation resources

**Libraries & docs**

- [Haystack Pipelines](https://docs.haystack.deepset.ai/docs/pipelines)
- [Architecture §10.1 — pipeline copy rules](../../architecture/07-deploy-packaging.md#101-dev-vs-deploy)

**Config sketch**

```yaml
serve:
  expose:
    - id: rag_pipeline
      path: pipelines/rag.yaml
```

### Acceptance criteria

- [ ] **AC-1** User `pipelines/` exposed via `serve.expose` in yaml
- [ ] **AC-2** RAG path documented with retriever → prompt → generator pattern
- [ ] **AC-3** Pipelines listed in `serve.expose` copied to deploy bundle
- [ ] **AC-4** `POST /{pipeline}/run` available per Architecture §9.1

### Implementation tasks (build)

- [ ] Extend serve runner to register exposed pipelines
- [ ] Add Phase 4 config schema for `serve.expose`
- [ ] Example RAG harness in user-docs (optional)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E8-S01 / E8.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/pipelines/test_serve_expose.py::test_e8_s01_ac1_pipelines_registered_from_yaml` |
| AC-2 | **manual:** user-docs RAG pattern documented |
| AC-3 | `tests/unit/deploy/test_copy_rules.py::test_e8_s01_ac3_exposed_pipelines_in_deploy` |
| AC-4 | `tests/integration/pipelines/test_serve_expose.py::test_e8_s01_ac4_post_pipeline_run_endpoint` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/pipelines/test_serve_expose.py -v` passes

### Definition of done

- [ ] `search_docs` builtin can attach when RAG pipeline present (§6.5 Phase 4)
- [ ] Verification checklist complete; all ACs traced to tests

---
