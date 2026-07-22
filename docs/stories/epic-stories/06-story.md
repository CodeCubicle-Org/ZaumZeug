# E2-S05 — `--dry-run` on serve

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/06-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-22 |
| **Story ID** | E2-S05 |
| **Status** | Done |
| **Epic** | [E2 — Configuration and Validation](../01-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 1 of 8 |
| **Story sequence** | 6 of 63 (global build order) |
| **Source** | Extracted from [`01-epic.md`](../01-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E2](../../prd.md#epic-e2--configuration-and-validation-phase-1) · [Architecture](../../architecture.md) |

---

## E2-S05 — `--dry-run` on serve

| Field | Value |
|---|---|
| **Feature** | E2.5 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) · [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) · [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want `zaumzeug serve --dry-run`, so that I can validate config and resolved paths without starting Hayhooks or calling an LLM.

### References

- [PRD E2.5](../../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §8](../../architecture/06-runtime-and-protocols.md#8-cli-and-runtime-layering)


### Implementation resources

**Internal spec**

- [Architecture §8.2 — serve layering](../../architecture/06-runtime-and-protocols.md#82-harness-vs-raw-hayhooks)
- Reuse config loader + resolver from [E2-S03](04-story.md); no Hayhooks bind on dry-run path

**Code**

- `src/zaumzeug/serve/validate.py` — `validate_serve()` (shared with E3-S02 real serve)
- `src/zaumzeug/serve/dry_run.py` — human-readable and `--json` report formatting
- `src/zaumzeug/cli.py` — `serve <harness> --dry-run [--deploy] [--json]`

### Acceptance criteria

- [x] **AC-1** Validates config via same path as real serve
- [x] **AC-2** Prints resolved config summary (model id, artifact path, tools, port)
- [x] **AC-3** Does not bind port or invoke LLM
- [x] **AC-4** Exit 0 on success, non-zero on validation failure

### Implementation tasks (build)

- [x] Add `--dry-run` flag to serve command
- [x] Reuse config loader + runtime resolver + doctor checks
- [x] Human-readable and optional `--json` output

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S05 / E2.5`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_serve_dry_run.py::test_e2_s05_ac1_same_validation_path_as_serve` |
| AC-2 | `tests/integration/test_serve_dry_run.py::test_e2_s05_ac2_prints_resolved_summary` |
| AC-2 | `tests/integration/test_serve_dry_run.py::test_e2_s05_ac2_json_output_shape` |
| AC-3 | `tests/integration/test_serve_dry_run.py::test_e2_s05_ac3_no_port_bind_no_llm` |
| AC-4 | `tests/integration/test_serve_dry_run.py::test_e2_s05_ac4_exit_zero_on_valid_config` |
| AC-4 | `tests/integration/test_serve_dry_run.py::test_e2_s05_ac4_exit_nonzero_on_invalid_config` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/integration/test_serve_dry_run.py -v` passes

### Definition of done

- [x] Called by [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) CI matrix ([AC-3](24-story.md#acceptance-criteria); wired in `.github/workflows/ci-matrix.yml` — Done 2026-07-22)
- [ ] Called by [E5-S09c](49.3-story.md#e5-s09c-target-install-verify-integration) `--verify` ([AC-2](49.3-story.md#acceptance-criteria); serve dry-run ready — wire in `target_install.py`)
- [x] Verification checklist complete; all ACs traced to tests

---
