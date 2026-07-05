# E5-S03 — `zaumzeug serve --deploy`

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/43-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E5-S03 |
| **Epic** | [E5 — Deploy Packaging](../06-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 6 of 8 |
| **Story sequence** | 43 of 63 (global build order) |
| **Source** | Extracted from [`06-epic.md`](../06-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E5](../../prd.md#epic-e5--deploy-packaging-phase-2) · [Architecture](../../architecture.md) |

---

## E5-S03 — `zaumzeug serve --deploy`

| Field | Value |
|---|---|
| **Feature** | E5.3 |
| **Persona** | Ops / platform |
| **Priority** | P0 |
| **Prerequisites** | [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) |

### User story

As **ops**, I want `zaumzeug serve <name> --deploy`, so that I run production bundles without the dev `usr-harnesses/` tree.

### References

- [PRD E5.3](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §8.1 — Source roots](../../architecture/06-runtime-and-protocols.md#81-source-roots)


### Implementation resources

**Internal spec**

- [Architecture §8.1 — `HARNESS_ROOT` / `--deploy`](../../architecture/06-runtime-and-protocols.md#81-source-roots)
- Reuse [E3-S02 serve runner](13-story.md) with deploy path resolution

### Acceptance criteria

- [ ] **AC-1** Loads only from `deploy/<name>/`
- [ ] **AC-2** Same OpenAI REST API as dev serve
- [ ] **AC-3** Fails if deploy folder missing or invalid manifest
- [ ] **AC-4** Works after target_install on clean venv without `usr-harnesses/`

### Implementation tasks (build)

- [ ] Add `--deploy` flag to serve command
- [ ] Resolve paths relative to `deploy/<name>/`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S03 / E5.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac1_loads_deploy_root_only` |
| AC-2 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac2_openai_rest_parity` |
| AC-3 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac3_fails_missing_manifest` |
| AC-4 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac4_after_target_install_clean_venv` |
| AC-1–4 | **shared:** E5-S08 Linux CI deploy → serve --deploy smoke |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/deploy/test_serve_deploy.py -v` passes

### Definition of done

- [ ] Documented in `README.deploy.md` and user-docs
- [ ] Verification checklist complete; all ACs traced to tests

---
