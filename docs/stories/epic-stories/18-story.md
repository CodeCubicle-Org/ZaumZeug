# E1-S01 — Cross-platform install script

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/18-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E1-S01 |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 18 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) |

---

## E1-S01 — Cross-platform install script

| Field | Value |
|---|---|
| **Feature** | E1.1 |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation) · [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) · [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent) |

### User story

As a **harness developer**, I want a single Python install script that works on Windows, macOS, and Linux, so that I can onboard in one command without manual dependency juggling.

### References

- [PRD E1.1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1)
- [Architecture §3.4](../../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)
- [Architecture §4.4](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)
- [PRD §7.4 — Install commands](../../prd.md#74-user-installation-guide-content-for-readme--phase-1)


### Implementation resources

**Libraries & docs**

- [venv — Python 3.11+](https://docs.python.org/3/library/venv.html)
- [pip editable install](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-e)
- [Architecture §3.4 — `client_install.py`](../../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)
- [Architecture §4.4 — `pip install -e ".[dev]"`](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)

### Acceptance criteria

- [ ] **AC-1** `install/client_install.py` runs on Windows, macOS, and Linux with Python 3.11+
- [ ] **AC-2** Creates project `.venv` when not present (unless `--skip-venv`)
- [ ] **AC-3** Runs `pip install -e ".[dev]"` successfully per Architecture §4.4
- [ ] **AC-4** Re-running the script is idempotent (no duplicate scaffolding or broken state)
- [ ] **AC-5** Supports flags: `--verify`, `--no-example`, `--skip-venv`, `--cursor-mcp`
- [ ] **AC-6** `--verify` runs `zaumzeug doctor` after install ([E2-S04](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks))
- [ ] **AC-7** Uses `pathlib` only — no hardcoded OS path separators ([Architecture §2.5](../../architecture/01-overview-and-principles.md#25-cross-platform-portability))

### Implementation tasks (build)

- [ ] Create `install/client_install.py` with OS detection via `platform.system()`
- [ ] Implement venv creation and activation path hints (`Scripts` vs `bin`)
- [ ] Wire editable install: `pip install -e ".[dev]"`
- [ ] Parse and forward CLI flags (`--verify`, `--no-example`, `--skip-venv`, `--cursor-mcp`)
- [ ] Add non-blocking Git missing warning
- [ ] Return non-zero exit code on failure with actionable stderr

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E1-S01 / E1.1`.

| AC | Test |
|---|---|
| AC-1 | **shared:** [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix) matrix runs script on three OS |
| AC-2 | `tests/unit/install/test_client_install.py::test_e1_s01_ac2_creates_venv_when_missing` |
| AC-3 | `tests/unit/install/test_client_install.py::test_e1_s01_ac3_editable_dev_install` |
| AC-4 | `tests/unit/install/test_client_install.py::test_e1_s01_ac4_idempotent_rerun` |
| AC-5 | `tests/unit/install/test_client_install.py::test_e1_s01_ac5_cli_flags_parsed` |
| AC-6 | `tests/unit/install/test_client_install.py::test_e1_s01_ac6_verify_invokes_doctor` |
| AC-7 | `tests/unit/install/test_client_install.py::test_e1_s01_ac7_pathlib_no_hardcoded_separators` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/install/test_client_install.py -v` passes

### Definition of done

- [ ] Idempotent re-run verified
- [ ] No secrets written to disk
- [ ] Verification checklist complete; all ACs traced to tests

---
