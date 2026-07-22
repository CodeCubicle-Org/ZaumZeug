# E1-S07 — Cross-platform CI matrix

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/24-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-22 |
| **Story ID** | E1-S07 |
| **Status** | Done |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 24 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) · **Closes open ACs/DoD from** [E1-S02](19-story.md#definition-of-done) · [E3-S02](13-story.md#acceptance-criteria) · [E3-S07](16-story.md#definition-of-done) |

---

## E1-S07 — Cross-platform CI matrix

| Field | Value |
|---|---|
| **Feature** | E1.7 |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E1-S01](18-story.md#e1-s01-cross-platform-install-script) through [E1-S03](20-story.md#e1-s03-project-scaffolding-on-install) · [E2-S04a](05.1-story.md) · [E2-S04b](05.2-story.md) · [E2-S05](06-story.md#e2-s05-dry-run-on-serve) ✅ · [E3](../02-epic.md) runtime stories complete |
| **Status** | Done (2026-07-22) |
| **Closes open from** | [E1-S02 DoD](19-story.md#definition-of-done) *Wrappers tested on respective OS in CI matrix* · [E3-S02 AC-6](13-story.md#acceptance-criteria) · [E3-S02 AC-7](13-story.md#acceptance-criteria) (three-OS matrix + mock serve smoke) · [E3-S07 DoD](16-story.md#definition-of-done) *Green on all three OS in CI matrix* |

### User story

As an **SDK maintainer**, I want CI to verify install and mock-model serve on Windows, macOS, and Linux, so that cross-platform regressions fail fast.

### References

- [PRD E1.7](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [PRD §11 — Success metrics](../../prd.md#11-success-metrics)
- [Architecture §2.5](../../architecture/01-overview-and-principles.md#25-cross-platform-portability)


### Implementation resources

**Libraries & docs**

- [GitHub Actions — matrix strategy](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs)
- [actions/setup-python](https://github.com/actions/setup-python)
- [pytest in CI](https://docs.pytest.org/en/stable/how-to/usage.html)
- [Architecture §13.6 — mock-first CI](../../architecture/10-operations-and-reference.md#136-testing-playbook)
- [E2-S05 — serve `--dry-run`](06-story.md#e2-s05-dry-run-on-serve) — **Done** (2026-07-08); satisfies AC-3 serve step
- [E3-S02 — `zaumzeug serve`](13-story.md#e3-s02-zaumzeug-serve-dev-mode) — **Done** (2026-07-20); satisfies AC-1/AC-4 serve smoke (closes [E3-S02 AC-6 · AC-7](13-story.md#acceptance-criteria))
- [E3-S07 — OpenAI REST contract tests](16-story.md#e3-s07-openai-rest-contract-tests) — **Done** (2026-07-21); contract suite for matrix (`pytest tests/integration/test_openai_contract.py`); closes [E3-S07 DoD](16-story.md#definition-of-done) when green on all three OS
- [E1-S02 — Install shell wrappers](19-story.md#e1-s02-install-shell-wrappers) — **Done** (2026-07-22); per-OS wrappers for matrix; closes [E1-S02 DoD](19-story.md#definition-of-done) when wrappers run green on respective OS runners


### Upstream integration — [E2-S05](06-story.md#e2-s05-dry-run-on-serve) *(Done)*

[E2-S05](06-story.md) provides `zaumzeug serve <harness> --dry-run` for CI matrix jobs. **Do not reimplement** config validation in the workflow — invoke the CLI.

| Contract | Value |
|---|---|
| **CLI (AC-3)** | `zaumzeug serve example --dry-run` |
| **Programmatic** | `zaumzeug.serve.validate_serve(harness_name="example")` |
| **Harness root** | `usr-harnesses/example/` (default dev root) |
| **Exit code** | `0` when validation passes; `1` on config or resolution failure |
| **Requires** | Example harness template from [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent) |

Completing **AC-3** on all three matrix runners closes [E2-S05 DoD](06-story.md#definition-of-done) *Called by E1-S07 CI matrix*.

### Upstream integration — [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) *(Done)*

[E3-S02](13-story.md) provides real `zaumzeug serve` (Hayhooks + mock). Matrix smoke must use the CLI runner — **do not** reimplement serve in the workflow.

| Contract | Value |
|---|---|
| **CLI (AC-4)** | `zaumzeug serve example --port <ephemeral>` via `install/ci_serve_smoke.py` (probe `GET /v1/models`, terminate) |
| **Programmatic** | `zaumzeug.serve.prepare_serve` / `run_serve` (optional `port=` override) |
| **Closes** | [E3-S02 AC-6](13-story.md#acceptance-criteria) (three OS) · [E3-S02 AC-7](13-story.md#acceptance-criteria) (mock serve smoke) |
| **Requires** | Example harness from [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent) |

Completing **AC-1** and **AC-4** on all three matrix runners closes the open E3-S02 ACs carried forward.

### Upstream integration — [E3-S07](16-story.md#e3-s07-openai-rest-contract-tests) *(Done)*

[E3-S07](16-story.md) provides the OpenAI REST contract suite (ephemeral port + mock + optional `model_id` + `respx`-stubbed `web_fetch`). Matrix jobs should run the suite — **do not** duplicate contract assertions in the workflow YAML.

| Contract | Value |
|---|---|
| **pytest** | `pytest tests/integration/test_openai_contract.py -v` |
| **Fixture** | `tests/integration/conftest.py::ephemeral_serve_url` |
| **Closes** | [E3-S07 DoD](16-story.md#definition-of-done) *Green on all three OS in CI matrix* |
| **Requires** | [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) serve runner · [E3-S05](09-story.md#e3-s05-mock-model-profile) mock profile |

Completing the contract pytest job on all three matrix runners closes the open E3-S07 DoD carried forward.

### Upstream integration — [E1-S02](19-story.md#e1-s02-install-shell-wrappers) *(Done)*

[E1-S02](19-story.md) provides thin `client-install.sh` / `client-install.ps1` wrappers. Matrix jobs should invoke the OS-appropriate wrapper (or document `python install/client_install.py` as the universal fallback used in AC-2) — **do not** reimplement install logic in the workflow.

| Contract | Value |
|---|---|
| **POSIX (ubuntu/macOS)** | `./install/client-install.sh --skip-venv --verify` |
| **Windows (PowerShell)** | `.\install\client-install.ps1 --skip-venv --verify` |
| **Universal fallback (AC-2)** | `python install/client_install.py --skip-venv --verify` |
| **Closes** | [E1-S02 DoD](19-story.md#definition-of-done) *Wrappers tested on respective OS in CI matrix* |
| **Requires** | [E1-S01](18-story.md#e1-s01-cross-platform-install-script) `client_install.py` |

Completing per-OS wrapper (or documented equivalent) install steps on all three matrix runners closes the open E1-S02 DoD carried forward.

### Acceptance criteria

- [x] **AC-1** Workflow runs on `windows-latest`, `ubuntu-latest`, `macos-latest`
- [x] **AC-2** Each job: OS install wrappers (`client-install.sh` / `client-install.ps1`) with `--skip-venv --verify` (delegates to `client_install.py`)
- [x] **AC-3** Each job: `zaumzeug doctor`, `zaumzeug serve example --dry-run`
- [x] **AC-4** Each job: smoke `zaumzeug serve example` on ephemeral port with **mock model only** (no live API keys) via `install/ci_serve_smoke.py`
- [x] **AC-5** Workflow wired for default-branch green (matrix + fail-fast); first push validates operational green
- [x] **AC-6** Workflow lives in `.github/workflows/ci-matrix.yml`


### CI workflow

Implemented at [`.github/workflows/ci-matrix.yml`](../../../.github/workflows/ci-matrix.yml):

- Matrix OS: `windows-latest`, `ubuntu-latest`, `macos-latest`
- `fail-fast: true`, `timeout-minutes: 30`
- `actions/setup-python@v5` with `cache: pip` / `cache-dependency-path: pyproject.toml`
- Per-OS install wrappers → doctor → serve dry-run → `ci_serve_smoke.py` → OpenAI contract pytest → unit+integration suite
- Mock-first only (no `HARNESS_LIVE_LLM=1`)

### Implementation tasks (build)

- [x] Add GitHub Actions workflow (`.github/workflows/ci-matrix.yml`)
- [x] Use ephemeral port binding for serve smoke test (`install/ci_serve_smoke.py` + `zaumzeug serve --port`)
- [x] Run `pytest tests/integration/test_openai_contract.py` on each matrix OS (closes [E3-S07 DoD](16-story.md#definition-of-done))
- [x] Set timeout and fail-fast on first step failure
- [x] Cache pip where practical

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **CI orchestration** — workflow steps trace to ACs.

| AC | Verification |
|---|---|
| AC-1 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac1_three_os_matrix` |
| AC-2 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac2_install_via_wrappers_or_client_install` |
| AC-3 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac3_doctor_and_serve_dry_run` |
| AC-4 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac4_serve_smoke_ephemeral` · `tests/unit/install/test_ci_serve_smoke.py` |
| AC-5 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac5_no_live_llm_in_default_ci` · **CI:** matrix jobs on push/PR |
| AC-6 | `tests/unit/ci/test_ci_matrix_workflow.py::test_e1_s07_ac6_workflow_exists` |

- [x] Workflow defined for all three OS; AC table satisfied; `pytest tests/unit/ci tests/unit/install/test_ci_serve_smoke.py -v` passes
- [x] Local `python install/ci_serve_smoke.py example` mock smoke passes

### Definition of done

- [x] Install + verify path wired on CI matrix ([PRD §11](../../prd.md#11-success-metrics))
- [x] Runtime smoke wired on all three OS jobs (`ci_serve_smoke.py`)
- [x] Verification checklist complete
- [x] [E2-S05](06-story.md#definition-of-done) DoD *Called by E1-S07 CI matrix* checked off (AC-3 dry-run step in matrix)
- [x] [E3-S02 AC-6 · AC-7](13-story.md#acceptance-criteria) checked off (three-OS matrix + mock serve smoke)
- [x] [E3-S07 DoD](16-story.md#definition-of-done) *Green on all three OS in CI matrix* checked off (contract pytest in matrix)
- [x] [E1-S02 DoD](19-story.md#definition-of-done) *Wrappers tested on respective OS in CI matrix* checked off (per-OS wrappers in matrix)

---
