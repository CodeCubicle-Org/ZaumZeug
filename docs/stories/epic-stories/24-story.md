# E1-S07 — Cross-platform CI matrix

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/24-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-20 |
| **Story ID** | E1-S07 |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 24 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) · **Closes open ACs from** [E3-S02](13-story.md#acceptance-criteria) |

---

## E1-S07 — Cross-platform CI matrix

| Field | Value |
|---|---|
| **Feature** | E1.7 |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E1-S01](18-story.md#e1-s01-cross-platform-install-script) through [E1-S03](20-story.md#e1-s03-project-scaffolding-on-install) · [E2-S04a](05.1-story.md) · [E2-S04b](05.2-story.md) · [E2-S05](06-story.md#e2-s05-dry-run-on-serve) ✅ · [E3](../02-epic.md) runtime stories complete |
| **Closes open from** | [E3-S02 AC-6](13-story.md#acceptance-criteria) · [E3-S02 AC-7](13-story.md#acceptance-criteria) (three-OS matrix + mock serve smoke) |

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
| **CLI (AC-4)** | `zaumzeug serve example` on ephemeral localhost port with mock model |
| **Programmatic** | `zaumzeug.serve.prepare_serve` / `run_serve` |
| **Closes** | [E3-S02 AC-6](13-story.md#acceptance-criteria) (three OS) · [E3-S02 AC-7](13-story.md#acceptance-criteria) (mock serve smoke) |
| **Requires** | Example harness from [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent) |

Completing **AC-1** and **AC-4** on all three matrix runners closes the open E3-S02 ACs carried forward.
### Acceptance criteria

- [ ] **AC-1** Workflow runs on `windows-latest`, `ubuntu-latest`, `macos-latest`
- [ ] **AC-2** Each job: `python install/client_install.py --skip-venv --verify` (or full venv + editable install)
- [ ] **AC-3** Each job: `zaumzeug doctor`, `zaumzeug serve example --dry-run`
- [ ] **AC-4** Each job: smoke `zaumzeug serve example` on ephemeral port with **mock model only** (no live API keys)
- [ ] **AC-5** All jobs green on default branch
- [ ] **AC-6** Workflow lives in `.github/workflows/`


### CI workflow skeleton

Reference layout for `.github/workflows/ci-matrix.yml`:

```yaml
name: ci-matrix
on: [push, pull_request]
jobs:
  phase1:
    strategy:
      fail-fast: true
      matrix:
        os: [windows-latest, ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install and verify
        run: python install/client_install.py --skip-venv --verify
      - name: Doctor
        run: zaumzeug doctor example
      - name: Serve dry-run
        run: zaumzeug serve example --dry-run
      - name: Serve smoke (mock)
        run: zaumzeug serve example --port 0  # ephemeral; mock model only
```

### Implementation tasks (build)

- [ ] Add GitHub Actions workflow (e.g. `ci-matrix.yml`)
- [ ] Use ephemeral port binding for serve smoke test
- [ ] Set timeout and fail-fast on first step failure
- [ ] Cache pip where practical

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). **CI orchestration** — workflow steps trace to ACs.

| AC | Verification |
|---|---|
| AC-1 | **CI:** workflow `strategy.matrix.os` includes three runners |
| AC-2 | **CI:** job step runs `client_install.py --skip-venv --verify` |
| AC-3 | **CI:** job steps run `doctor` and `serve example --dry-run` |
| AC-4 | **CI:** job step smoke-tests serve on ephemeral port (mock only) |
| AC-5 | **CI:** all matrix jobs green on default branch |
| AC-6 | **manual:** `.github/workflows/ci-matrix.yml` (or equivalent) exists |

- [ ] Workflow green on all three OS; AC table satisfied

### Definition of done

- [ ] 100% install success rate on CI matrix ([PRD §11](../../prd.md#11-success-metrics))
- [ ] Runtime smoke 100% on all three OS jobs
- [ ] Verification checklist complete
- [ ] [E2-S05](06-story.md#definition-of-done) DoD *Called by E1-S07 CI matrix* checked off when AC-3 passes on `windows-latest`, `ubuntu-latest`, and `macos-latest`
- [ ] [E3-S02 AC-6 · AC-7](13-story.md#acceptance-criteria) checked off when AC-1 and AC-4 pass on all three OS runners

---
