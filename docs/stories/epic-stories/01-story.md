# E2-S00 — SDK package skeleton and CLI foundation

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/01-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E2-S00 |
| **Epic** | [E2 — Configuration and Validation](../01-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 1 of 8 |
| **Story sequence** | 1 of 63 (global build order) |
| **Source** | Extracted from [`01-epic.md`](../01-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E2](../../prd.md#epic-e2--configuration-and-validation-phase-1) · [Architecture](../../architecture.md) |

---

## E2-S00 — SDK package skeleton and CLI foundation

| Field | Value |
|---|---|
| **Feature** | Foundation (PRD Phase 1 / Architecture §3, §4.4, §11) |
| **Persona** | SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | None — **start here** |

### User story

As an **SDK maintainer**, I want a pip-installable package with a `harness` CLI entry point, so that all later epics have a repo structure and command surface to build on.

### References

- [Architecture §3 — Repository structure](../../architecture/02-repository-and-layout.md#3-repository-structure)
- [Architecture §3.2 — Package naming](../../architecture/02-repository-and-layout.md#32-package-naming)
- [Architecture §4.4 — pyproject.toml](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)
- [Architecture §11 — SDK modules #1 CLI](../../architecture/09-sdk-module-map.md#11-sdk-modules-to-build)
- [Architecture §2.5 — Cross-platform](../../architecture/01-overview-and-principles.md#25-cross-platform-portability)
- [Architecture §3.2 — Package naming](../../architecture/02-repository-and-layout.md#32-package-naming) (**ZaumZeug** / `zaumzeug`)


### Implementation resources

**Libraries & docs**

- [Python packaging — pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Python argparse subcommands](https://docs.python.org/3/library/argparse.html#sub-commands)
- [Architecture §4.4 — illustrative `pyproject.toml`](../../architecture/03-technology-stack.md#44-pyprojecttoml-dependency-groups-phase-1-stub)

**Code sketch — CLI entry**

```python
# src/zaumzeug/cli.py
def main() -> None:
    parser = argparse.ArgumentParser(prog="zaumzeug")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("serve")
    # ...
    args = parser.parse_args()
```

### Acceptance criteria

- [ ] **AC-1** `pyproject.toml` exists with `name = "zaumzeug"`, `requires-python >= 3.11`, runtime deps per §4.4
- [ ] **AC-2** `[project.optional-dependencies]` includes `dev` (`dspy-ai`, `gepa`, `pytest`, `pytest-asyncio`, `httpx`, `respx`, `debugpy`) and `eval` (`deepeval`) per [Architecture §4.5](../../architecture/03-technology-stack.md#45-test-dependencies)
- [ ] **AC-3** Entry point: `zaumzeug = "zaumzeug.cli:main"`
- [ ] **AC-4** Package layout matches Architecture §3: `src/zaumzeug/` with `cli.py`, `config/`, `runtime/`, `compile/`, `deploy/`, `eval/`, `serve/`, `integrations/`
- [ ] **AC-5** `zaumzeug --help` exits 0 with subcommand stubs: `init`, `doctor`, `serve`, `run`, (`compile`, `deploy`, `eval`, `mcp`, `acp` as Phase 2+ stubs OK)
- [ ] **AC-6** Repo `.gitattributes` normalizes text line endings to `\n`
- [ ] **AC-7** `pip install -e ".[dev]"` succeeds from repo root

### Implementation tasks (build)

- [ ] Create `pyproject.toml` per Architecture §4.4 illustrative fragment
- [ ] Create `src/zaumzeug/__init__.py` and `src/zaumzeug/cli.py` with `argparse` subparsers
- [ ] Create empty module packages: `config/`, `runtime/`, `serve/`, `compile/`, `deploy/`, `eval/`, `integrations/`
- [ ] Add `.gitattributes` for `* text=auto eol=lf`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S00`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/test_e2_s00_package.py::test_e2_s00_ac1_pyproject_metadata` |
| AC-2 | `tests/unit/test_e2_s00_package.py::test_e2_s00_ac2_optional_extras_dev_eval` |
| AC-3 | `tests/unit/test_e2_s00_package.py::test_e2_s00_ac3_entry_point_registered` |
| AC-4 | `tests/unit/test_e2_s00_package.py::test_e2_s00_ac4_package_layout` |
| AC-5 | `tests/unit/test_cli_help.py::test_e2_s00_ac5_help_lists_subcommands` |
| AC-6 | **manual:** `.gitattributes` contains `* text=auto eol=lf` (file inspection) |
| AC-7 | **manual:** `pip install -e ".[dev]"` from clean venv (or CI job in E1-S07) |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/test_e2_s00_package.py tests/unit/test_cli_help.py -v` passes

### Definition of done

- [ ] Editable install works — unblocks E1-S01 and all CLI stories
- [ ] No hardcoded OS paths in skeleton code
- [ ] Verification checklist complete; `pytest` green for automated ACs

---
