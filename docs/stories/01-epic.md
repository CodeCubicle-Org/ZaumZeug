# Epic E2 — Configuration and Validation

| | |
|---|---|
| **Document** | Epic E2 user stories |
| **File** | `docs/stories/01-epic.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-08 (E2-S07 done) |
| **Status** | Done (E2-S00–S07) |
| **Build order** | **1 of 8** (implement first) |
| **Related** | [PRD](../prd.md) · [Architecture](../architecture.md) · [Index](00-README.md) |

---
| Field | Value |
|---|---|
| **Phase** | 1 |
| **Epic** | E2 |
| **Outcome** | Multi-agent harness config: `harness.yaml`, `workflow.yaml`, `agents/<name>/`, `agents-models.yaml` load, merge, and validate |
| **Depends on** | — (starts with E2-S00 package skeleton) |
| **Blocks** | [E3](02-epic.md) · [E1](03-epic.md) |
| **PRD** | [Epic E2](../prd.md#epic-e2--configuration-and-validation-phase-1) |
| **Architecture** | [§6 Configuration](../architecture/05-configuration.md#6-configuration-architecture) · [§5.2 Runtime resolution](../architecture/04-data-flows.md#52-runtime-agent-resolution) · [§11 SDK modules #2](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build) · [§13 Debug](../architecture/10-operations-and-reference.md#13-debug-and-test-architecture) |
| **Principle** | [Fail fast — PRD §6](../prd.md#6-product-principles) |

### Story implementation order (within this epic)

1. **E2-S00** — Package skeleton + CLI stub *(foundation)* — **Done** ([01-story.md](epic-stories/01-story.md))
2. **E2-S01** — Pydantic config schemas — **Done** ([02-story.md](epic-stories/02-story.md))
3. **E2-S02** — `models.yaml` merge — **Done** ([03-story.md](epic-stories/03-story.md))
4. **E2-S03** — Runtime agent resolution rules — **Done** ([04-story.md](epic-stories/04-story.md))
5. **E2-S04a** — `zaumzeug doctor` (core checks) — **Done** ([05.1-story.md](epic-stories/05.1-story.md))
6. **E2-S04b** — `zaumzeug doctor` (phase-aware warnings) — **Done** ([05.2-story.md](epic-stories/05.2-story.md))
7. **E2-S04c** — `zaumzeug doctor --deploy` — **Done** ([05.3-story.md](epic-stories/05.3-story.md))
8. **E2-S05** — Serve `--dry-run` — **Done** ([06-story.md](epic-stories/06-story.md))
9. **E2-S06** — Logging — **Done** ([07-story.md](epic-stories/07-story.md))
10. **E2-S07** — `workflow.yaml` schema (serial stages) — **Done** ([08-story.md](epic-stories/08-story.md))

---

## E2-S00 — SDK package skeleton and CLI foundation

| Field | Value |
|---|---|
| **Feature** | Foundation (PRD Phase 1 / Architecture §3, §4.4, §11) |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | None — **start here** |
| **Status** | Done (2026-07-08) |

### User story

As an **SDK maintainer**, I want a pip-installable package with a `harness` CLI entry point, so that all later epics have a repo structure and command surface to build on.

### References

- [Architecture §3 — Repository structure](../architecture/02-repository-and-layout.md#3-repository-structure)
- [Architecture §3.2 — Package naming](../architecture/02-repository-and-layout.md#32-package-naming)
- [Architecture §4.4 — pyproject.toml](../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)
- [Architecture §11 — SDK modules #1 CLI](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build)
- [Architecture §2.5 — Cross-platform](../architecture/01-overview-and-principles.md#25-cross-platform-portability)
- [Architecture §3.2 — Package naming](../architecture/02-repository-and-layout.md#32-package-naming) (**ZaumZeug** / `zaumzeug`)

### Acceptance criteria

- [x] **AC-1** `pyproject.toml` exists with `name = "zaumzeug"`, `requires-python >= 3.11`, runtime deps per §4.4
- [x] **AC-2** `[project.optional-dependencies]` includes `dev` (`dspy-ai`, `gepa`, `pytest`, `pytest-asyncio`, `httpx`, `respx`, `debugpy`) and `eval` (`deepeval`) per [Architecture §4.5](../architecture/03-technology-stack.md#45-test-dependencies)
- [x] **AC-3** Entry point: `zaumzeug = "zaumzeug.cli:main"`
- [x] **AC-4** Package layout matches Architecture §3: `src/zaumzeug/` with `cli.py`, `config/`, `runtime/`, `compile/`, `deploy/`, `eval/`, `serve/`, `integrations/`
- [x] **AC-5** `zaumzeug --help` exits 0 with subcommand stubs: `init`, `doctor`, `serve`, `run`, (`compile`, `deploy`, `eval`, `mcp`, `acp` as Phase 2+ stubs OK)
- [x] **AC-6** Repo `.gitattributes` normalizes text line endings to `\n`
- [x] **AC-7** `pip install -e ".[dev]"` succeeds from repo root

### Implementation tasks (build)

- [x] Create `pyproject.toml` per Architecture §4.4 illustrative fragment
- [x] Create `src/zaumzeug/__init__.py` and `src/zaumzeug/cli.py` with `argparse` subparsers
- [x] Create empty module packages: `config/`, `runtime/`, `serve/`, `compile/`, `deploy/`, `eval/`, `integrations/`
- [x] Add `.gitattributes` for `* text=auto eol=lf`

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E2-S00`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/test_e2_s00_package.py::test_e2_s00_ac1_pyproject_metadata` |
| AC-2 | `tests/unit/test_e2_s00_package.py::test_e2_s00_ac2_optional_extras_dev_eval` |
| AC-3 | `tests/unit/test_e2_s00_package.py::test_e2_s00_ac3_entry_point_registered` |
| AC-4 | `tests/unit/test_e2_s00_package.py::test_e2_s00_ac4_package_layout` |
| AC-5 | `tests/unit/test_cli_help.py::test_e2_s00_ac5_help_lists_subcommands` |
| AC-6 | **manual:** `.gitattributes` contains `* text=auto eol=lf` (file inspection) |
| AC-7 | **manual:** `pip install -e ".[dev]"` from clean venv (or CI job in E1-S07) |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/test_e2_s00_package.py tests/unit/test_cli_help.py -v` passes

### Definition of done

- [x] Editable install works — unblocks E1-S01 and all CLI stories
- [x] No hardcoded OS paths in skeleton code
- [x] Verification checklist complete; `pytest` green for automated ACs

---

## E2-S01 — Pydantic config schemas

| Field | Value |
|---|---|
| **Feature** | E2.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S00](#e2-s00-sdk-package-skeleton-and-cli-foundation) |
| **Status** | Done (2026-07-08) — see [epic-stories/02-story.md](epic-stories/02-story.md) |

### User story

As a **harness developer**, I want invalid YAML to fail with field-level errors, so that I can fix config without reading SDK source.

### References

- [PRD E2.1](../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §6.6 — Phase 1 schema](../architecture/05-configuration.md#66-phase-1-config-schema)
- [Architecture §6.2 — Config sections](../architecture/05-configuration.md#62-config-sections)
- [Ideation — full YAML examples](../ideation-stage.md)

### Acceptance criteria

- [x] **AC-1** Invalid `harness.yaml` fails with Pydantic field-level errors
- [x] **AC-2** Phase 1 minimal example from §6.6 passes validation
- [x] **AC-3** Unknown sections/fields for current phase fail with phase hint (e.g. “`compile` is Phase 2”)
- [x] **AC-4** Config validation error clarity meets [PRD §11](../prd.md#11-success-metrics)

### Implementation tasks (build)

- [x] Implement schemas in `src/zaumzeug/config/schemas.py`
- [x] Implement loader in `src/zaumzeug/config/loader.py` (read yaml, invoke schemas, resolve paths via `pathlib`)
- [x] Phase-gated field allowlists per epic/phase map

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E2-S01 / E2.1`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_schemas.py::test_e2_s01_ac1_invalid_yaml_field_errors` |
| AC-2 | `tests/unit/config/test_schemas.py::test_e2_s01_ac2_phase1_minimal_valid` |
| AC-3 | `tests/unit/config/test_schemas.py::test_e2_s01_ac3_unknown_key_phase_hint` |
| AC-4 | `tests/unit/config/test_schemas.py::test_e2_s01_ac4_error_includes_path_and_field` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/config/test_schemas.py -v` passes

### Definition of done

- [x] Example harness config passes
- [x] Error messages include file path and field name
- [x] Verification checklist complete; all ACs traced to tests

---

## E2-S02 — `models.yaml` merge

| Field | Value |
|---|---|
| **Feature** | E2.2 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S00](#e2-s00-sdk-package-skeleton-and-cli-foundation) |
| **Status** | Done (2026-07-08) — see [epic-stories/03-story.md](epic-stories/03-story.md) |

### User story

As a **harness developer**, I want global, harness, and per-agent model registries to deep-merge, so that each agent can use a different LLM without duplicating the full registry.

### References

- [PRD E2.2](../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §6.1 — Merge rules](../architecture/05-configuration.md#61-model-registry-merge)
- [Architecture §3.3.1](../architecture/02-repository-and-layout.md#331-model-config-files-naming)

### Acceptance criteria

- [x] **AC-1** Global `config/models.yaml` deep-merges with harness `models.yaml` (when present)
- [x] **AC-2** Per-agent `agents/<name>/agents-models.yaml` deep-merges over harness + global
- [x] **AC-3** Nested dicts merge recursively; child keys win
- [x] **AC-4** Lists in child file **replace** parent lists entirely
- [x] **AC-5** Each agent's `default_model_id` validated against that agent's merged registry

### Implementation tasks (build)

- [x] Implement merge in `src/zaumzeug/config/models.py`
- [x] Support `models: models.yaml` file reference in `harness.yaml`

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E2-S02 / E2.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac1_global_harness_deep_merge` |
| AC-2 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac2_nested_dict_harness_wins` |
| AC-3 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac3_list_replace_not_append` |
| AC-4 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac4_same_model_id_override` |
| AC-5 | `tests/unit/config/test_models_merge.py::test_e2_s02_ac5_missing_default_model_id_fails` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/config/test_models_merge.py -v` passes

### Definition of done

- [x] Merge rules covered by unit tests ([PRD story seed](../prd.md#epic-e2--configuration-and-validation-phase-1))
- [x] Secrets never loaded from YAML (`.env` only)
- [x] Verification checklist complete; all ACs traced to tests

---

## E2-S03 — Runtime agent resolution rules

| Field | Value |
|---|---|
| **Feature** | E2.3 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](#e2-s01-pydantic-config-schemas) · [E2-S02](#e2-s02-modelsyaml-merge) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want runtime agent resolution enforced by mode, so that compile/runtime separation is enforced.

### References

- [PRD E2.3](../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §5.2](../architecture/04-data-flows.md#52-runtime-agent-resolution)
- [Architecture §2.1 — Golden rules](../architecture/01-overview-and-principles.md#21-golden-rules)
- [PRD G2](../prd.md#3-goals)

### Acceptance criteria

- [x] **AC-1** **Serve/run (per agent):** loads `artifact` > `system_prompt` > actionable error
- [x] **AC-2** **Compile (per agent):** requires `compile.module` in `agents/<name>/agent.yaml` (Phase 2+)
- [x] **AC-3** **Serve entry:** uses workflow `entry` agent for interactive `zaumzeug serve`
- [x] **AC-4** Error messages name missing path and suggest fix

### Implementation tasks (build)

- [x] Implement resolver in `src/zaumzeug/config/resolver.py`
- [x] Validate artifact has `artifact-manifest.json` when artifact path set

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E2-S03 / E2.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_resolver.py::test_e2_s03_ac1_serve_artifact_over_system_prompt` |
| AC-1 | `tests/unit/config/test_resolver.py::test_e2_s03_ac1_serve_system_prompt_fallback` |
| AC-1 | `tests/unit/config/test_resolver.py::test_e2_s03_ac1_serve_both_missing_actionable_error` |
| AC-2 | `tests/unit/config/test_resolver.py::test_e2_s03_ac2_compile_requires_module` |
| AC-3 | `tests/unit/config/test_resolver.py::test_e2_s03_ac3_serve_entry_from_workflow` |
| AC-4 | `tests/unit/config/test_resolver.py::test_e2_s03_ac4_error_names_path_and_suggests_fix` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/config/test_resolver.py -v` passes

### Definition of done

- [x] Doctor uses same resolution logic via `resolve_agent_serve()` (E2-S04a, 2026-07-08)
- [ ] Serve uses same resolution logic *(close when E3-S00 / E3-S02 are done)*
- [x] No DSPy import on serve path
- [x] Verification checklist complete; all ACs traced to tests

---

## E2-S04 — `zaumzeug doctor` *(split into sub-stories)*

> **Canonical story files:** [E2-S04a — core](epic-stories/05.1-story.md) · [E2-S04b — warnings](epic-stories/05.2-story.md) · [E2-S04c — `--deploy`](epic-stories/05.3-story.md)

### E2-S04a — core checks

| Field | Value |
|---|---|
| **Feature** | E2.4 (part 1) |
| **Persona** | Harness developer · Ops |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](#e2-s01-pydantic-config-schemas) · [E2-S02](#e2-s02-modelsyaml-merge) · [E2-S03](#e2-s03-runtime-agent-resolution-rules) |
| **Status** | Done (2026-07-08) |

**AC:** Python 3.11+, package import, `.env` warn, runtime path, model registry keys, port conflict warn, `--verbose`/`--json`, harness scan.

**Build:** `doctor` subcommand in `src/zaumzeug/doctor/`; core check modules (pass/warn/fail). See [epic-stories/05.1-story.md](epic-stories/05.1-story.md).

### E2-S04b — phase-aware warnings

| Field | Value |
|---|---|
| **Feature** | E2.4 (part 2) |
| **Prerequisites** | [E2-S04a](epic-stories/05.1-story.md) · [E2-S07](#e2-s07-workflowyaml-schema-serial) |
| **Status** | Done (2026-07-08) |

**AC:** Eval section Phase 1 warn; MCP without `uv` warn; stale workflow-diagram warn.

**Build:** Phase-aware warn checks in `src/zaumzeug/doctor/checks.py`; `load_harness_for_doctor()` in `src/zaumzeug/config/loader.py`. See [epic-stories/05.2-story.md](epic-stories/05.2-story.md).

### E2-S04c — `--deploy` mode

| Field | Value |
|---|---|
| **Feature** | E2.4 (part 3) |
| **Prerequisites** | [E2-S04a](epic-stories/05.1-story.md) · [E5-S01](../06-epic.md#e5-s01-zaumzeug-deploy-command) · [E5-S03](../06-epic.md#e5-s03-zaumzeug-serve-deploy) |
| **Status** | Done (2026-07-08) |

**AC:** `--deploy` / `HARNESS_ROOT=deploy` resolves `deploy/<name>/`; validates deploy `manifest.json` and pinned artifacts; reuses E2-S04a core checks; non-zero exit on missing manifest or broken artifact refs.

**Build:** `check_deploy_manifest()` in `src/zaumzeug/doctor/checks.py`; harness root resolution in `src/zaumzeug/config/harness_root.py`; `run_doctor(deploy=True)` and CLI `--deploy`. See [epic-stories/05.3-story.md](epic-stories/05.3-story.md).

---

## E2-S05 — `--dry-run` on serve

| Field | Value |
|---|---|
| **Feature** | E2.5 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E3-S02](../02-epic.md#e3-s02-zaumzeug-serve-dev-mode) · [E2-S04a](epic-stories/05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) · [E2-S01](#e2-s01-pydantic-config-schemas) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want `zaumzeug serve --dry-run`, so that I can validate config and resolved paths without starting Hayhooks or calling an LLM.

### References

- [PRD E2.5](../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §8](../architecture/06-runtime-and-protocols.md#8-cli-and-runtime-layering)

**AC:** Validates via `load_harness()` + `resolve_serve_entry()`; reuses doctor model/runtime checks; prints port, entry agent, model id, runtime path, and tools; no port bind or LLM; exit 0 on success.

**Build:** `validate_serve()` in `src/zaumzeug/serve/validate.py`; `format_dry_run()` / `dry_run_to_json()` in `src/zaumzeug/serve/dry_run.py`; CLI `serve <harness> --dry-run [--deploy] [--json]`. See [epic-stories/06-story.md](epic-stories/06-story.md).

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

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E2-S05 / E2.5`.

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

- [ ] Called by [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) CI matrix ([AC-3](24-story.md#acceptance-criteria); serve dry-run ready — wire in `.github/workflows/`)
- [ ] Called by [E5-S09c](49.3-story.md#e5-s09c-target-install-verify-integration) `--verify` ([AC-2](49.3-story.md#acceptance-criteria); serve dry-run ready — wire in `target_install.py`)
- [x] Verification checklist complete; all ACs traced to tests

---

## E2-S06 — Structured logging

| Field | Value |
|---|---|
| **Feature** | E2.6 |
| **Persona** | Harness developer |
| **Priority** | P2 |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want verbose logging on serve and compile, so that I can debug model routing and tool calls per request.

### References

- [PRD E2.6](../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §13](../architecture/10-operations-and-reference.md#13-debug-and-test-architecture)

### Acceptance criteria

- [x] **AC-1** `--verbose` on serve/compile enables SDK + Haystack structured logging
- [x] **AC-2** `HARNESS_LOG_LEVEL=DEBUG` env var works equivalently
- [x] **AC-3** Logs include `model_id`, tool name, artifact path per request where applicable
- [x] **AC-4** No secrets logged (API keys redacted)

### Implementation tasks (build)

- [x] Centralize logging config in `src/zaumzeug/logging.py`
- [x] Wire Haystack log level when verbose
- [x] Document env var in `user-docs/reference/cli.md`

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E2-S06 / E2.6`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/test_logging.py::test_e2_s06_ac1_verbose_flag_sets_debug_level` |
| AC-2 | `tests/unit/test_logging.py::test_e2_s06_ac2_harness_log_level_env_equivalent` |
| AC-3 | `tests/unit/test_logging.py::test_e2_s06_ac3_log_record_includes_model_tool_artifact` |
| AC-4 | `tests/unit/test_logging.py::test_e2_s06_ac4_api_keys_redacted_in_logs` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/test_logging.py -v` passes

### Definition of done

- [x] No secrets logged (API keys redacted)
- [x] Verification checklist complete; all ACs traced to tests

---

## E2-S07 — `workflow.yaml` schema (serial)

| Field | Value |
|---|---|
| **Feature** | E2.7 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](#e2-s01-pydantic-config-schemas) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want `workflow.yaml` validated with my agent folders, so that serial multi-agent harnesses fail fast before run or compile.

### References

- [PRD E2.7](../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §3.3](../architecture/02-repository-and-layout.md#33-harness-folder-layout)
- [Architecture §6.6](../architecture/05-configuration.md#66-phase-1-config-schema)

### Implementation resources

- `src/zaumzeug/config/schemas.py` — `WorkflowConfig`, `WorkflowStage`
- `src/zaumzeug/config/loader.py` — `load_workflow()`, agent cross-validation
- `src/zaumzeug/doctor/checks.py` — `check_workflow_config`
- `src/zaumzeug/serve/validate.py` — workflow validation on serve dry-run

### Acceptance criteria

- [x] **AC-1** `workflow.yaml` requires `entry` and non-empty `stages` list
- [x] **AC-2** Each stage is exactly one of `agent: <name>` or `pipeline: <id>` (serial order)
- [x] **AC-3** Every `agent` ref resolves to `agents/<name>/agent.yaml`
- [x] **AC-4** Agent names unique within harness; folder name matches `agent.yaml` `name`
- [x] **AC-5** `parallelism` field fails in Phase 1 with phase hint (deferred)
- [x] **AC-6** `example` harness `workflow.yaml` from §6.6 passes validation

### Implementation tasks (build)

- [x] Add `WorkflowConfig` schema in `src/zaumzeug/config/schemas.py`
- [x] Cross-validate workflow agent refs against `agents/` directory in loader
- [x] Wire into `zaumzeug doctor` and serve/run dry paths

### Verification (after build)

Per [Story verification](00-README.md#story-verification-required). Test file header: `# Story: E2-S07 / E2.7`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac1_requires_entry_and_stages` |
| AC-2 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac2_agent_or_pipeline_stage` |
| AC-3 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac3_unknown_agent_ref_fails` |
| AC-4 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac4_unique_agent_names` |
| AC-5 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac5_parallelism_phase_hint` |
| AC-6 | `tests/unit/config/test_workflow_schema.py::test_e2_s07_ac6_example_workflow_valid` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/config/test_workflow_schema.py -v` passes

### Definition of done

- [x] Doctor validates workflow for named harness
- [x] Verification checklist complete; all ACs traced to tests
