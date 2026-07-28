# E5-S03 — `zaumzeug serve --deploy`

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/43-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E5-S03 |
| **Status** | Done |
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
| **Prerequisites** | [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) ✅ · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) ✅ |

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

- [x] **AC-1** Loads only from `deploy/<name>/`
- [x] **AC-2** Same OpenAI REST API as dev serve
- [x] **AC-3** Fails if deploy folder missing or invalid manifest
- [x] **AC-4** Works after target_install on clean venv without `usr-harnesses/`

### Implementation tasks (build)

- [x] Add `--deploy` flag to serve command
- [x] Resolve paths relative to `deploy/<name>/`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S03 / E5.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac1_loads_deploy_root_only` |
| AC-2 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac2_openai_rest_parity` |
| AC-3 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac3_fails_missing_manifest` |
| AC-4 | `tests/integration/deploy/test_serve_deploy.py::test_e5_s03_ac4_after_target_install_clean_venv` |
| AC-1–4 | **shared:** E5-S08 Linux CI deploy → serve --deploy smoke |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/deploy/test_serve_deploy.py -v` passes (4 passed, 0 skipped)

### Definition of done

- [x] Documented in `README.deploy.md` and user-docs
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- CLI `--deploy` and `serve/runner.py` / `validate_serve(deploy=…)` already resolved roots via `config/harness_root.py` (E2-S04c / E2-S05 / E3-S02); this story closes full Hayhooks serve from production bundles and AC tests.
- Deploy mode validates `manifest.json` via `check_deploy_manifest` before bind; missing folder → `harness_discovery` fail.
- Docs: `install/templates/deploy/README.deploy.md`, `user-docs/reference/cli.md` (+ install template mirror).
- Shared Linux CI smoke remains [E5-S08](48-story.md).
---
