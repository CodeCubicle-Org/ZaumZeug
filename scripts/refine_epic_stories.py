"""Apply scrum-master refinements: sub-story splits, prerequisites, cross-links."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "stories" / "epic-stories"
TODAY = date.today().isoformat()

# Stories replaced by decimal sub-stories
REMOVE = ["05-story.md", "27-story.md", "28-story.md", "49-story.md"]

PREREQUISITES: dict[str, str] = {
    "01-story.md": "None — **start here**",
    "02-story.md": "[E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation)",
    "03-story.md": "[E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation)",
    "04-story.md": "[E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E2-S02](03-story.md#e2-s02-modelsyaml-merge)",
    "05.1-story.md": "[E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E2-S02](03-story.md#e2-s02-modelsyaml-merge) · [E2-S03](04-story.md#e2-s03-runtime-agent-resolution-rules)",
    "05.2-story.md": "[E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) · [E2-S07](08-story.md#e2-s07-workflowyaml-schema-serial)",
    "05.3-story.md": "[E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) · [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy)",
    "06-story.md": "[E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) · [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) · [E2-S01](02-story.md#e2-s01-pydantic-config-schemas)",
    "07-story.md": "[E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) · [E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation)",
    "08-story.md": "[E2-S01](02-story.md#e2-s01-pydantic-config-schemas)",
    "09-story.md": "[E2-S02](03-story.md#e2-s02-modelsyaml-merge)",
    "10-story.md": "[E3-S05](09-story.md#e3-s05-mock-model-profile) · [E2-S02](03-story.md#e2-s02-modelsyaml-merge)",
    "11-story.md": "[E2-S01](02-story.md#e2-s01-pydantic-config-schemas)",
    "12-story.md": "[E3-S01](10-story.md#e3-s01-modelrouter) · [E3-S03](11-story.md#e3-s03-builtin-tool-web_fetch) · [E2-S03](04-story.md#e2-s03-runtime-agent-resolution-rules)",
    "13-story.md": "[E3-S00](12-story.md#e3-s00-runtime-factory-haystack-agent-builder) · [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks)",
    "14-story.md": "[E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E3-S03](11-story.md#e3-s03-builtin-tool-web_fetch)",
    "15-story.md": "[E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode)",
    "16-story.md": "[E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) · [E3-S05](09-story.md#e3-s05-mock-model-profile)",
    "17-story.md": "[E2-S07](08-story.md#e2-s07-workflowyaml-schema-serial) · [E3-S00](12-story.md#e3-s00-runtime-factory-haystack-agent-builder) · [E3-S01](10-story.md#e3-s01-modelrouter)",
    "18-story.md": "[E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation) · [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) · [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent)",
    "19-story.md": "[E1-S01](18-story.md#e1-s01-cross-platform-install-script)",
    "20-story.md": "[E1-S01](18-story.md#e1-s01-cross-platform-install-script) · [E3-S04](14-story.md#e3-s04-example-harness-general-research-agent)",
    "21-story.md": "[E1-S03](20-story.md#e1-s03-project-scaffolding-on-install) · [E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation)",
    "22-story.md": "[E1-S03](20-story.md#e1-s03-project-scaffolding-on-install)",
    "23-story.md": "[E1-S05](22-story.md#e1-s05-user-documentation-skeleton)",
    "24-story.md": "[E1-S01](18-story.md#e1-s01-cross-platform-install-script) through [E1-S03](20-story.md#e1-s03-project-scaffolding-on-install) · [E2-S04a](05.1-story.md) · [E2-S04b](05.2-story.md) · [E3](../02-epic.md) runtime stories complete",
    "26-story.md": "[E2-S03](04-story.md#e2-s03-runtime-agent-resolution-rules) · [E3-S00](12-story.md#e3-s00-runtime-factory-haystack-agent-builder)",
    "27.1-story.md": "[E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E2-S03](04-story.md#e2-s03-runtime-agent-resolution-rules) · [E4-S01](26-story.md#e4-s01-dspy-module-loader)",
    "27.2-story.md": "[E4-S02a](27.1-story.md#e4-s02a-compile-cli-and-phase-2-schema) · [E4-S01](26-story.md#e4-s01-dspy-module-loader)",
    "28.1-story.md": "[E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts)",
    "28.2-story.md": "[E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest) · [E3-S00](12-story.md#e3-s00-runtime-factory-haystack-agent-builder)",
    "30-story.md": "[E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest) · [E4-S03b](28.2-story.md#e4-s03b-runtime-input_rewrite-preprocess) · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode)",
    "31-story.md": "[E4-S02a](27.1-story.md#e4-s02a-compile-cli-and-phase-2-schema) · [E4-S01](26-story.md#e4-s01-dspy-module-loader)",
    "32-story.md": "[E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts) · [E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest)",
    "33-story.md": "[E2-S07](08-story.md#e2-s07-workflowyaml-schema-serial) · [E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts)",
    "34-story.md": "[E2-S00](01-story.md#e2-s00-sdk-package-skeleton-and-cli-foundation)",
    "35-story.md": "[E6-S01](34-story.md#e6-s01-optional-eval-extra) · [E2-S01](02-story.md#e2-s01-pydantic-config-schemas)",
    "36-story.md": "[E5-S06](46-story.md#e5-s06-deploy-eval-gate) *(implementation owner)* · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command)",
    "37-story.md": "[E6-S02](35-story.md#e6-s02-zaumzeug-eval-command) · [E6-S01](34-story.md#e6-s01-optional-eval-extra)",
    "38-story.md": "[E6-S02](35-story.md#e6-s02-zaumzeug-eval-command)",
    "39-story.md": "[E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode) · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command)",
    "40-story.md": "[E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts) · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command)",
    "41-story.md": "[E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts) · [E5-S02](42-story.md#e5-s02-dev-vs-deploy-copy-rules) · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command)",
    "42-story.md": "[E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest)",
    "43-story.md": "[E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode)",
    "44-story.md": "[E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy)",
    "45-story.md": "[E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy) · [E5-S09c](49.3-story.md#e5-s09c-target-install-verify-integration)",
    "46-story.md": "[E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E6-S02](35-story.md#e6-s02-zaumzeug-eval-command)",
    "47-story.md": "[E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command)",
    "48-story.md": "[E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix)",
    "49.1-story.md": "[E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks)",
    "49.2-story.md": "[E5-S09a](49.1-story.md#e5-s09a-target-install-core-script)",
    "49.3-story.md": "[E5-S09a](49.1-story.md#e5-s09a-target-install-core-script) · [E5-S09b](49.2-story.md#e5-s09b-target-install-shell-wrappers) · [E2-S04c](05.3-story.md#e2-s04c-zaumzeug-doctor-deploy-mode) · [E2-S05](06-story.md#e2-s05-dry-run-on-serve)",
    "50-story.md": "[E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E2-S04b](05.2-story.md#e2-s04b-zaumzeug-doctor-phase-aware-warnings)",
    "51-story.md": "[E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E3-S03](11-story.md#e3-s03-builtin-tool-web_fetch)",
    "52-story.md": "[E1-S03](20-story.md#e1-s03-project-scaffolding-on-install) · [E7-S01](50-story.md#e7-s01-mcp-tool-configuration) · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode)",
    "53-story.md": "[E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode)",
    "54-story.md": "[E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode)",
    "55-story.md": "[E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy) · [E7-S01](50-story.md#e7-s01-mcp-tool-configuration)",
    "56-story.md": "[E3-S03](11-story.md#e3-s03-builtin-tool-web_fetch) · [E7-S01](50-story.md#e7-s01-mcp-tool-configuration)",
    "57-story.md": "[E7-S04](53-story.md#e7-s04-chainlit-embedded-ui) · [E7-S05](54-story.md#e7-s05-acp-adapter)",
    "58-story.md": "[E5-S02](42-story.md#e5-s02-dev-vs-deploy-copy-rules) · [E3-S02](13-story.md#e3-s02-zaumzeug-serve-dev-mode)",
    "59-story.md": "[E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy)",
    "60-story.md": "[E6-S05](38-story.md#e6-s05-trace-test-case)",
    "62-story.md": "[E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E5-S08](48-story.md#e5-s08-deploy-platform-policy)",
    "63-story.md": "[E6-S01](34-story.md#e6-s01-optional-eval-extra) · [E5-S09c](49.3-story.md#e5-s09c-target-install-verify-integration)",
}

LINK_REPLACEMENTS = [
    ("05-story.md#e2-s04-zaumzeug-doctor-command", "05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks"),
    ("[E2-S04](05-story.md", "[E2-S04a](05.1-story.md"),
    ("27-story.md#e4-s02-gepa-compile-command", "27.2-story.md#e4-s02b-gepa-runner-and-artifacts"),
    ("28-story.md#e4-s03-export-contract-haystack-artifacts", "28.1-story.md#e4-s03a-export-contract-and-manifest"),
    ("49-story.md#e5-s09-target-runtime-install-script", "49.1-story.md#e5-s09a-target-install-core-script"),
    ("(E4-S03)", "(E4-S03b)"),
    ("*(extends E2-S04)*", "*(extends E2-S04b)*"),
]

SUB_STORIES: dict[str, str] = {}  # filled below in main


def header(
    story_id: str,
    title: str,
    filename: str,
    seq: str,
    total: int,
    epic_id: str,
    epic_title: str,
    epic_file: str,
    phase: str,
    epic_build: str,
    prd_anchor: str,
) -> str:
    return (
        f"# {story_id} — {title}\n\n"
        f"| | |\n"
        f"|---|---|\n"
        f"| **Document** | User story |\n"
        f"| **File** | `docs/stories/epic-stories/{filename}` |\n"
        f"| **Created** | 2026-07-04 |\n"
        f"| **Last modified** | {TODAY} |\n"
        f"| **Story ID** | {story_id} |\n"
        f"| **Parent story** | Split from monolithic story in same sequence slot |\n"
        f"| **Epic** | [{epic_id} — {epic_title}](../{epic_file}) |\n"
        f"| **Phase** | {phase} |\n"
        f"| **Epic build order** | {epic_build} of 8 |\n"
        f"| **Story sequence** | {seq} of {total} (global build order) |\n"
        f"| **Related** | [Stories index](../00-README.md) · "
        f"[Epic {epic_id}](../../prd.md{prd_anchor}) · [Architecture](../../architecture.md) |\n\n"
        f"---\n\n"
    )


def build_sub_stories(total: int) -> dict[str, str]:
    h2 = lambda sid, title, fn, seq, eid, et, ef, ph, eb, prd, body: (
        header(sid, title, fn, seq, total, eid, et, ef, ph, eb, prd)
        + body
    )

    stories: dict[str, str] = {}

    stories["05.1-story.md"] = h2(
        "E2-S04a", "`zaumzeug doctor` — core checks", "05.1-story.md", "5.1", "E2",
        "Configuration and Validation", "01-epic.md", "1", "1",
        "#epic-e2--configuration-and-validation-phase-1",
        """## E2-S04a — `zaumzeug doctor` — core checks

| Field | Value |
|---|---|
| **Feature** | E2.4 (part 1) |
| **Persona** | Harness developer · Ops |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E2-S02](03-story.md#e2-s02-modelsyaml-merge) · [E2-S03](04-story.md#e2-s03-runtime-agent-resolution-rules) |

### User story

As a **harness developer**, I want `zaumzeug doctor` to preflight my environment and core harness config, so that I catch problems before starting a server.

### References

- [PRD E2.4](../../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §13](../../architecture/10-operations-and-reference.md#13-debug-and-test-architecture)
- [PRD G6](../../prd.md#3-goals)

### Acceptance criteria

- [ ] **AC-1** Checks Python version (3.11+)
- [ ] **AC-2** Checks install / package import
- [ ] **AC-3** Checks `.env` presence (warn if live model configured without keys)
- [ ] **AC-5** Validates runtime path (artifact / system_prompt)
- [ ] **AC-6** Validates model registry keys referenced in harness
- [ ] **AC-7** Warns on port conflicts when detectable
- [ ] **AC-9** Supports `--verbose`, `--json`
- [ ] **AC-10** Optional harness name or project-wide scan

### Implementation tasks (build)

- [ ] Add `doctor` subcommand in CLI
- [ ] Implement core check modules with pass/warn/fail severity (env, config, runtime, models, port)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S04a / E2.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/cli/test_doctor.py::test_e2_s04_ac1_python_version_check` |
| AC-2 | `tests/unit/cli/test_doctor.py::test_e2_s04_ac2_package_import_check` |
| AC-3 | `tests/unit/cli/test_doctor.py::test_e2_s04_ac3_env_warn_without_keys` |
| AC-5 | `tests/integration/test_doctor.py::test_e2_s04_ac5_missing_artifact_and_system_prompt_fails` |
| AC-6 | `tests/unit/cli/test_doctor.py::test_e2_s04_ac6_unknown_model_id_fails` |
| AC-7 | `tests/unit/cli/test_doctor.py::test_e2_s04_ac7_port_conflict_warn` |
| AC-9 | `tests/unit/cli/test_doctor.py::test_e2_s04_ac9_verbose_and_json_output` |
| AC-10 | `tests/integration/test_doctor.py::test_e2_s04_ac10_named_harness_and_project_scan` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/cli/test_doctor.py tests/integration/test_doctor.py -v -k e2_s04` passes

### Definition of done

- [ ] Used by install `--verify` and CI matrix ([E1-S07](24-story.md#e1-s07-cross-platform-ci-matrix))
- [ ] JSON output stable for scripting
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    stories["05.2-story.md"] = h2(
        "E2-S04b", "`zaumzeug doctor` — phase-aware warnings", "05.2-story.md", "5.2", "E2",
        "Configuration and Validation", "01-epic.md", "1", "1",
        "#epic-e2--configuration-and-validation-phase-1",
        """## E2-S04b — `zaumzeug doctor` — phase-aware warnings

| Field | Value |
|---|---|
| **Feature** | E2.4 (part 2) |
| **Persona** | Harness developer · Ops |
| **Priority** | P0 |
| **Prerequisites** | [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) · [E2-S07](08-story.md#e2-s07-workflowyaml-schema-serial) |

### User story

As a **harness developer**, I want doctor to warn about phase-mismatched config and missing tooling, so that I do not accidentally rely on Phase 2+ features too early.

### References

- [PRD E2.4](../../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §13](../../architecture/10-operations-and-reference.md#13-debug-and-test-architecture)

### Acceptance criteria

- [ ] **AC-1** Validates config including optional `eval` section (warn when present in Phase 1)
- [ ] **AC-2** Warns when MCP configured but `uv` missing
- [ ] **AC-3** Warns when `workflow.yaml` is newer than `docs/workflow-diagram.md` (missing diagram = warn)

### Implementation tasks (build)

- [ ] Add eval-section phase hint check (warn, not fail, in Phase 1)
- [ ] Add MCP/`uv` presence warn check
- [ ] Add workflow-diagram staleness warn check

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S04b / E2.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/cli/test_doctor.py::test_e2_s04_ac4_eval_section_phase1_warn` |
| AC-2 | `tests/unit/cli/test_doctor.py::test_e2_s04_ac8_mcp_without_uv_warns` |
| AC-3 | `tests/integration/test_doctor.py::test_e2_s04_ac11_stale_workflow_diagram_warn` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/cli/test_doctor.py tests/integration/test_doctor.py -v -k "e2_s04_ac4 or e2_s04_ac8 or e2_s04_ac11"` passes

### Definition of done

- [ ] Warnings do not block Phase 1 serve/run
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    stories["05.3-story.md"] = h2(
        "E2-S04c", "`zaumzeug doctor --deploy` mode", "05.3-story.md", "5.3", "E2",
        "Configuration and Validation", "01-epic.md", "2", "1",
        "#epic-e2--configuration-and-validation-phase-1",
        """## E2-S04c — `zaumzeug doctor --deploy` mode

| Field | Value |
|---|---|
| **Feature** | E2.4 (part 3) / E5 deploy integration |
| **Persona** | Ops / platform |
| **Priority** | P1 |
| **Prerequisites** | [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) · [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy) |

### User story

As **ops**, I want `zaumzeug doctor --deploy` to validate a production deploy bundle, so that target install `--verify` catches deploy-specific issues.

### References

- [PRD E2.4](../../prd.md#epic-e2--configuration-and-validation-phase-1)
- [Architecture §10.3](../../architecture/07-deploy-packaging.md#103-deploy-manifestjson)
- [E5-S09c — target install verify](49.3-story.md#e5-s09c-target-install-verify-integration)

### Acceptance criteria

- [ ] **AC-1** `--deploy` resolves harness from `deploy/<name>/` (or `HARNESS_ROOT=deploy`)
- [ ] **AC-2** Validates deploy `manifest.json` and runtime-only artifact paths
- [ ] **AC-3** Reuses E2-S04a core checks against deploy bundle layout
- [ ] **AC-4** Exit non-zero on missing manifest or broken artifact refs

### Implementation tasks (build)

- [ ] Add `--deploy` flag to doctor; wire deploy root resolution ([E5-S04](44-story.md#e5-s04-harness_rootdeploy-environment-override))
- [ ] Add deploy manifest + artifact checks

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E2-S04c / E2.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/test_doctor.py::test_e2_s04c_ac1_deploy_root_resolution` |
| AC-2 | `tests/integration/test_doctor.py::test_e2_s04c_ac2_validates_deploy_manifest` |
| AC-3 | `tests/integration/test_doctor.py::test_e2_s04c_ac3_reuses_core_checks` |
| AC-4 | `tests/integration/test_doctor.py::test_e2_s04c_ac4_fails_on_broken_bundle` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/test_doctor.py -v -k e2_s04c` passes

### Definition of done

- [ ] Called by [E5-S09c](49.3-story.md#e5-s09c-target-install-verify-integration) `--verify`
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    stories["27.1-story.md"] = h2(
        "E4-S02a", "Compile CLI and Phase 2 schema", "27.1-story.md", "27.1", "E4",
        "Compile and GEPA Pipeline", "04-epic.md", "2", "4",
        "#epic-e4--compile-and-gepa-pipeline-phase-2",
        """## E4-S02a — Compile CLI and Phase 2 schema

| Field | Value |
|---|---|
| **Feature** | E4.2 (part 1) |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) · [E2-S03](04-story.md#e2-s03-runtime-agent-resolution-rules) · [E4-S01](26-story.md#e4-s01-dspy-module-loader) |

### User story

As a **harness developer**, I want `zaumzeug compile` to validate Phase 2 config and load DSPy modules, so that compile fails fast before any GEPA run.

### References

- [PRD E4.2](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §6.2 — Config sections](../../architecture/05-configuration.md#62-config-sections)

### Acceptance criteria

- [ ] **AC-1** Phase 2 `compile` section validates via extended Pydantic schemas
- [ ] **AC-2** `zaumzeug compile` requires resolvable `compile.module` per agent ([E2-S03](04-story.md#e2-s03-runtime-agent-resolution-rules))
- [ ] **AC-3** Fails with actionable error when module not importable (no GEPA invocation)
- [ ] **AC-4** Fails with actionable error when task/reflection LM ids missing from registry or `.env` keys absent

### Implementation tasks (build)

- [ ] Extend Pydantic schemas for Phase 2 `compile` section
- [ ] Add `compile` subcommand stub in CLI; wire [E4-S01](26-story.md#e4-s01-dspy-module-loader) module loader
- [ ] Preflight registry + `.env` for compile LM ids before GEPA

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S02a / E4.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_schemas.py::test_e4_s02a_ac1_phase2_compile_schema_validates` |
| AC-2 | `tests/unit/config/test_resolver.py::test_e4_s02a_ac2_compile_requires_module` |
| AC-3 | `tests/unit/compile/test_module_loader.py::test_e4_s02a_ac3_missing_module_actionable_error` |
| AC-4 | `tests/unit/compile/test_gepa_runner.py::test_e4_s02a_ac4_missing_lm_keys_actionable_error` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/config/ tests/unit/compile/ -v -k e4_s02a` passes

### Definition of done

- [ ] Unblocks [E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts)
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    stories["27.2-story.md"] = h2(
        "E4-S02b", "GEPA runner and artifacts", "27.2-story.md", "27.2", "E4",
        "Compile and GEPA Pipeline", "04-epic.md", "2", "4",
        "#epic-e4--compile-and-gepa-pipeline-phase-2",
        """## E4-S02b — GEPA runner and artifacts

| Field | Value |
|---|---|
| **Feature** | E4.2 (part 2) |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E4-S02a](27.1-story.md#e4-s02a-compile-cli-and-phase-2-schema) · [E4-S01](26-story.md#e4-s01-dspy-module-loader) |

### User story

As a **harness developer**, I want `zaumzeug compile` to run GEPA per config, so that prompts and tool text improve from execution traces.

### References

- [PRD E4.2](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §4.2 — GEPA boundaries](../../architecture/03-technology-stack.md#42-library-boundaries-when-to-use-what)
- [Architecture §7 — task/reflection LM](../../architecture/05-configuration.md#7-model-routing)

### Acceptance criteria

- [ ] **AC-1** `zaumzeug compile` runs `dspy.GEPA` per `compile` section in yaml *(stub GEPA OK in CI)*
- [ ] **AC-2** Writes `artifacts/<run_id>/` and updates `artifacts/current`
- [ ] **AC-3** Custom metrics return **textual feedback** (`dspy.Prediction(score=..., feedback=...)`), not scalar-only
- [ ] **AC-4** Module **may** include a clarify/rewrite signature — optimized via same GEPA run, exported in [E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest) (optional)
- [ ] **AC-5** Task and reflection LMs resolved from model registry (LiteLLM strings wired)
- [ ] **AC-6** Respects GEPA budget config (`auto` or `max_metric_calls`)

### Implementation tasks (build)

- [ ] Implement `src/zaumzeug/compile/gepa_runner.py`
- [ ] Wire LiteLLM strings from model registry
- [ ] Generate immutable `run_id` per compile; update `artifacts/current` symlink or copy policy
- [ ] Provide stub GEPA fixture for CI (no live API keys in matrix)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S02b / E4.2`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/compile/test_gepa_runner.py::test_e4_s02_ac1_invokes_dspy_gepa` *(stub GEPA)* |
| AC-2 | `tests/integration/compile/test_gepa_runner.py::test_e4_s02_ac2_writes_run_id_and_current` |
| AC-3 | `tests/unit/compile/test_gepa_runner.py::test_e4_s02_ac3_metric_returns_textual_feedback` |
| AC-4 | `tests/integration/compile/test_gepa_runner.py::test_e4_s02_ac4_optional_input_rewrite_in_run` |
| AC-5 | `tests/unit/compile/test_gepa_runner.py::test_e4_s02_ac5_task_and_reflection_lm_from_registry` |
| AC-6 | `tests/unit/compile/test_gepa_runner.py::test_e4_s02_ac6_respects_gepa_budget` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/compile/test_gepa_runner.py tests/integration/compile/ -v -k e4_s02` passes

### Definition of done

- [ ] Compile example harness story seed passes ([PRD E4](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2))
- [ ] Document compile requires API keys for task/reflection models
- [ ] Unblocks [E4-S03a](28.1-story.md) and [E4-S08](33-story.md#e4-s08-workflow-diagram-at-compile) *(diagram is separate story)*
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    stories["28.1-story.md"] = h2(
        "E4-S03a", "Export contract and manifest", "28.1-story.md", "28.1", "E4",
        "Compile and GEPA Pipeline", "04-epic.md", "2", "4",
        "#epic-e4--compile-and-gepa-pipeline-phase-2",
        """## E4-S03a — Export contract and manifest

| Field | Value |
|---|---|
| **Feature** | E4.3 (part 1) |
| **Persona** | Harness developer · SDK maintainer |
| **Priority** | P0 |
| **Prerequisites** | [E4-S02b](27.2-story.md#e4-s02b-gepa-runner-and-artifacts) |

### User story

As a **harness developer**, I want compile output mapped to Haystack-compatible artifacts, so that runtime loads optimized prompts without DSPy.

### References

- [PRD E4.3](../../prd.md#epic-e4--compile-and-gepa-pipeline-phase-2)
- [Architecture §5.3 — Artifact layout](../../architecture/04-data-flows.md#53-artifact-layout)
- [Architecture §12 Pattern A](../../architecture/08-compile-and-optimization.md#pattern-a-default-phase-2-v1)

### Acceptance criteria

- [ ] **AC-1** `dump_state()` maps to Haystack `system_prompt`, tool descriptions, pipeline Jinja templates
- [ ] **AC-2** **Optional input handling:** when module exports clarify/rewrite signature text → write `prompts/input_rewrite.md` (or path listed in `artifact-manifest.json`)
- [ ] **AC-3** `artifact-manifest.json` lists exported paths including optional `input_rewrite` when present
- [ ] **AC-4** Harnesses without input handling in module omit `input_rewrite` — no error
- [ ] **AC-5** Document: GEPA optimizes the **template**, not end-user chat; runtime applies fixed exported text only
- [ ] **AC-6** Writes `artifact-manifest.json` per run (not deploy `manifest.json`)
- [ ] **AC-7** Golden snapshot tests for export shape (with and without optional input rewrite)
- [ ] **AC-8** Legacy `manifest.json` alias accepted during migration if documented

### Implementation tasks (build)

- [ ] Implement exporter in `src/zaumzeug/compile/export.py`
- [ ] Map optional DSPy clarify/rewrite predictor to `prompts/input_rewrite.md`
- [ ] Write `artifact-manifest.json` with module hash, run metadata, optional `input_rewrite` path

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S03a / E4.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/compile/test_export_snapshots.py::test_e4_s03_ac1_minimal_export_snapshot` |
| AC-2 | `tests/compile/test_export_snapshots.py::test_e4_s03_ac2_export_with_input_rewrite` |
| AC-3 | `tests/unit/compile/test_export.py::test_e4_s03_ac3_manifest_lists_paths` |
| AC-4 | `tests/unit/compile/test_export.py::test_e4_s03_ac4_no_input_rewrite_when_absent` |
| AC-5 | **manual:** user-docs compile guide states template-only optimization |
| AC-6 | `tests/unit/compile/test_export.py::test_e4_s03_ac6_writes_artifact_manifest_not_deploy` |
| AC-7 | `tests/compile/test_export_snapshots.py::test_e4_s03_ac7_golden_with_and_without_rewrite` |
| AC-8 | `tests/unit/compile/test_export.py::test_e4_s03_ac8_legacy_manifest_alias` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/compile/ tests/unit/compile/test_export.py -v -k e4_s03` passes

### Definition of done

- [ ] Runtime resolver loads exported artifact ([E2-S03](04-story.md), [E4-S05](30-story.md))
- [ ] Unblocks [E4-S03b](28.2-story.md#e4-s03b-runtime-input_rewrite-preprocess)
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    stories["28.2-story.md"] = h2(
        "E4-S03b", "Runtime `input_rewrite` preprocess", "28.2-story.md", "28.2", "E4",
        "Compile and GEPA Pipeline", "04-epic.md", "2", "4",
        "#epic-e4--compile-and-gepa-pipeline-phase-2",
        """## E4-S03b — Runtime `input_rewrite` preprocess

| Field | Value |
|---|---|
| **Feature** | E4.3 (part 2) |
| **Persona** | Harness developer |
| **Priority** | P0 |
| **Prerequisites** | [E4-S03a](28.1-story.md#e4-s03a-export-contract-and-manifest) · [E3-S00](12-story.md#e3-s00-runtime-factory-haystack-agent-builder) |

### User story

As a **harness developer**, I want the runtime to apply exported input-rewrite templates before the agent loop, so that compile-time optimized clarify/rewrite text is used without GEPA at serve time.

### References

- [Architecture §5.2 — Runtime resolution](../../architecture/04-data-flows.md#52-runtime-agent-resolution)
- [Architecture §12 Pattern A — optional input rewrite](../../architecture/08-compile-and-optimization.md#pattern-a-default-phase-2-v1)

### Acceptance criteria

- [ ] **AC-1** When `artifact-manifest.json` lists `input_rewrite`, runtime loads template from artifact path
- [ ] **AC-2** User message is preprocessed through fixed template text (Jinja or string format per export contract) before `Agent.run`
- [ ] **AC-3** No DSPy import on serve/run path when only preprocess runs
- [ ] **AC-4** Missing `input_rewrite` file when manifest lists it → actionable error naming path

### Implementation tasks (build)

- [ ] Wire runtime factory: if manifest has `input_rewrite`, run preprocess step then pass result to agent
- [ ] Implement preprocess in `src/zaumzeug/runtime/preprocess.py`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E4-S03b / E4.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/compile/test_compile_serve.py::test_e4_s03b_ac1_loads_input_rewrite_from_manifest` |
| AC-2 | `tests/integration/compile/test_compile_serve.py::test_e4_s03b_ac2_preprocess_before_agent_run` |
| AC-3 | `tests/integration/compile/test_compile_serve.py::test_e4_s03b_ac3_no_dspy_on_serve_path` |
| AC-4 | `tests/integration/compile/test_compile_serve.py::test_e4_s03b_ac4_missing_rewrite_actionable_error` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/compile/test_compile_serve.py -v -k e4_s03b` passes

### Definition of done

- [ ] Integrated with [E4-S05](30-story.md#e4-s05-post-compile-serve-uses-artifact) serve path
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    stories["49.1-story.md"] = h2(
        "E5-S09a", "Target install — core script", "49.1-story.md", "49.1", "E5",
        "Deploy Packaging", "06-epic.md", "2", "6",
        "#epic-e5--deploy-packaging-phase-2",
        """## E5-S09a — Target install — core script

| Field | Value |
|---|---|
| **Feature** | E5.9 (part 1) |
| **Persona** | Ops / platform |
| **Priority** | P0 |
| **Prerequisites** | [E5-S01](41-story.md#e5-s01-zaumzeug-deploy-command) · [E2-S04a](05.1-story.md#e2-s04a-zaumzeug-doctor-core-checks) |

### User story

As **ops**, I want `install/target_install.py` to prepare a runtime venv on the target host, so that production servers can install ZaumZeug without dev extras.

### References

- [PRD E5.9](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §10.7](../../architecture/07-deploy-packaging.md#107-target-runtime-install-script)

### Acceptance criteria

- [ ] **AC-1** `install/target_install.py` runs on target Linux *(Win/macOS via wrappers in E5-S09b)*
- [ ] **AC-2** Assumes Python 3.11+ preinstalled; creates optional `.venv`
- [ ] **AC-3** `pip install zaumzeug` (runtime only — no `[dev]`, `[eval]`, DSPy, GEPA)
- [ ] **AC-4** Copies `.env.example` → `.env` if missing; never overwrites `.env`
- [ ] **AC-5** Idempotent re-run

### Implementation tasks (build)

- [ ] Implement `install/target_install.py`
- [ ] Preflight: verify deploy `manifest.json` + `harness.yaml`

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S09a / E5.9`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_target_install.py::test_e5_s09_ac1_runs_on_linux` |
| AC-2 | `tests/integration/deploy/test_target_install.py::test_e5_s09_ac2_optional_venv` |
| AC-3 | `tests/integration/deploy/test_target_install.py::test_e5_s09_ac3_runtime_only_pip_install` |
| AC-4 | `tests/integration/deploy/test_target_install.py::test_e5_s09_ac5_env_example_copy_preserves_existing` |
| AC-5 | `tests/integration/deploy/test_target_install.py::test_e5_s09_ac8_idempotent_rerun` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/deploy/test_target_install.py -v -k "e5_s09_ac1 or e5_s09_ac2 or e5_s09_ac3 or e5_s09_ac5 or e5_s09_ac8"` passes

### Definition of done

- [ ] Unblocks [E5-S09b](49.2-story.md) and [E5-S09c](49.3-story.md)
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    stories["49.2-story.md"] = h2(
        "E5-S09b", "Target install — shell wrappers", "49.2-story.md", "49.2", "E5",
        "Deploy Packaging", "06-epic.md", "2", "6",
        "#epic-e5--deploy-packaging-phase-2",
        """## E5-S09b — Target install — shell wrappers

| Field | Value |
|---|---|
| **Feature** | E5.9 (part 2) |
| **Persona** | Ops / platform |
| **Priority** | P0 |
| **Prerequisites** | [E5-S09a](49.1-story.md#e5-s09a-target-install-core-script) |

### User story

As **ops**, I want sh/ps1 wrappers for target install, so that I can run install on Windows, macOS, and Linux without invoking Python directly.

### References

- [Architecture §3.4 — Install scripts](../../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)

### Acceptance criteria

- [ ] **AC-1** `target-install.sh` and `target-install.ps1` invoke `target_install.py` with forwarded args
- [ ] **AC-2** Wrappers bundled inside each `deploy/<name>/` ([E5-S01](41-story.md))
- [ ] **AC-3** Same exit code as underlying Python script

### Implementation tasks (build)

- [ ] Add `target-install.sh` / `target-install.ps1` wrappers mirroring dev install pattern ([E1-S02](19-story.md))

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S09b / E5.9`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_target_install.py::test_e5_s09b_ac1_wrappers_invoke_python` |
| AC-2 | `tests/integration/deploy/test_deploy.py::test_e5_s09_ac7_scripts_in_bundle` *(shared E5-S01)* |
| AC-3 | `tests/integration/deploy/test_target_install.py::test_e5_s09b_ac3_wrapper_exit_code_parity` |

- [ ] Every AC row above has a passing test or documented manual exception

### Definition of done

- [ ] Wrappers shipped in deploy bundle
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    stories["49.3-story.md"] = h2(
        "E5-S09c", "Target install — verify integration", "49.3-story.md", "49.3", "E5",
        "Deploy Packaging", "06-epic.md", "2", "6",
        "#epic-e5--deploy-packaging-phase-2",
        """## E5-S09c — Target install — verify integration

| Field | Value |
|---|---|
| **Feature** | E5.9 (part 3) |
| **Persona** | Ops / platform |
| **Priority** | P0 |
| **Prerequisites** | [E5-S09a](49.1-story.md#e5-s09a-target-install-core-script) · [E5-S09b](49.2-story.md#e5-s09b-target-install-shell-wrappers) · [E2-S04c](05.3-story.md#e2-s04c-zaumzeug-doctor-deploy-mode) · [E2-S05](06-story.md#e2-s05-dry-run-on-serve) |

### User story

As **ops**, I want `--verify` on target install to run doctor and serve dry-run, so that I know the deploy bundle is healthy before going live.

### References

- [E2-S04c — doctor --deploy](05.3-story.md#e2-s04c-zaumzeug-doctor-deploy-mode)
- [E2-S05 — serve --dry-run](06-story.md#e2-s05-dry-run-on-serve)

### Acceptance criteria

- [ ] **AC-1** `--verify` runs `zaumzeug doctor <name> --deploy`
- [ ] **AC-2** `--verify` runs `zaumzeug serve <name> --deploy --dry-run`
- [ ] **AC-3** Supports `--skip-venv` passthrough to core script
- [ ] **AC-4** Non-zero exit if doctor or dry-run fails

### Implementation tasks (build)

- [ ] Wire `--verify` flag in `target_install.py` to invoke doctor + serve dry-run against deploy root

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S09c / E5.9`.

| AC | Test |
|---|---|
| AC-1 | `tests/integration/deploy/test_target_install.py::test_e5_s09_ac4_verify_runs_doctor_deploy` |
| AC-2 | `tests/integration/deploy/test_target_install.py::test_e5_s09_ac6_verify_runs_serve_dry_run` |
| AC-3 | `tests/integration/deploy/test_target_install.py::test_e5_s09_ac6_skip_venv_and_verify_flags` |
| AC-4 | `tests/integration/deploy/test_target_install.py::test_e5_s09c_ac4_verify_fails_on_bad_bundle` |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/integration/deploy/test_target_install.py -v -k "e5_s09_ac4 or e5_s09_ac6 or e5_s09c"` passes

### Definition of done

- [ ] Documented in [E5-S05](45-story.md#e5-s05-target-ship-workflow-documentation) target ship guide
- [ ] Verification checklist complete; all ACs traced to tests

---
""",
    )

    return stories


def patch_prerequisites(text: str, filename: str) -> str:
    if filename not in PREREQUISITES:
        return text
    prereq = PREREQUISITES[filename]
    if re.search(r"\| \*\*Prerequisites\*\* \|", text):
        text = re.sub(
            r"\| \*\*Prerequisites\*\* \| [^\n]+ \|",
            f"| **Prerequisites** | {prereq} |",
            text,
            count=1,
        )
    else:
        text = re.sub(
            r"(\| \*\*Priority\*\* \| [^\n]+ \|)\n",
            rf"\1\n| **Prerequisites** | {prereq} |\n",
            text,
            count=1,
        )
    return text


def patch_e3_s08_ac3(text: str) -> str:
    old = "- [ ] **AC-3** Prior stage output passed as context to next agent stage"
    new = (
        "- [ ] **AC-3** Prior stage output passed as context to next agent stage — "
        "append prior agent's final assistant message as a new `user` message: "
        "`{\"role\": \"user\", \"content\": \"<prior_stage_output>\"}` prepended before the workflow input; "
        "full message list forwarded to the next agent's Haystack Agent.run"
    )
    return text.replace(old, new)


def patch_e1_s07(text: str) -> str:
    insert = """
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

"""
    if "### CI workflow skeleton" in text:
        return text
    return text.replace("### Implementation tasks (build)", insert + "### Implementation tasks (build)", 1)


def patch_e3_s01(text: str) -> str:
    insert = """
### Phase 1 provider allowlist

| Provider id | Phase | Notes |
|---|---|---|
| `mock` | 1 | Default for CI and example harness ([E3-S05](09-story.md)) |
| `openrouter` | 1 | Live models via OpenRouter API key in `.env` |
| `openai`, `anthropic`, etc. | 2+ | Phase-gated — fail with phase hint if configured in Phase 1 |

"""
    if "### Phase 1 provider allowlist" in text:
        return text
    return text.replace("### Acceptance criteria", insert + "### Acceptance criteria", 1)


def patch_e6_s03(text: str) -> str:
    note = (
        "| **Status** | Traceability slice — **implementation owner: [E5-S06](46-story.md#e5-s06-deploy-eval-gate)** |\n"
    )
    if "**Status** | Traceability" in text:
        return text
    return text.replace("| **Priority** | P1 |", "| **Priority** | P1 |\n" + note, 1)


def patch_file(text: str, filename: str) -> str:
    for old, new in LINK_REPLACEMENTS:
        text = text.replace(old, new)
    text = patch_prerequisites(text, filename)
    if filename == "17-story.md":
        text = patch_e3_s08_ac3(text)
    if filename == "24-story.md":
        text = patch_e1_s07(text)
    if filename == "10-story.md":
        text = patch_e3_s01(text)
    if filename == "36-story.md":
        text = patch_e6_s03(text)
    if filename == "30-story.md":
        text = text.replace(
            "(E4-S03) — no GEPA at runtime",
            "([E4-S03b](28.2-story.md#e4-s03b-runtime-input_rewrite-preprocess)) — no GEPA at runtime",
        )
    if "**Last modified**" in text and filename not in REMOVE:
        text = re.sub(
            r"\| \*\*Last modified\*\* \| \d{4}-\d{2}-\d{2} \|",
            f"| **Last modified** | {TODAY} |",
            text,
            count=1,
        )
    return text


def build_index() -> str:
    rows = [
        ("01-story.md", "E2-S00", "SDK package skeleton and CLI foundation", "1", "E2", "01-epic.md"),
        ("02-story.md", "E2-S01", "Pydantic config schemas", "1", "E2", "01-epic.md"),
        ("03-story.md", "E2-S02", "`models.yaml` merge", "1", "E2", "01-epic.md"),
        ("04-story.md", "E2-S03", "Runtime agent resolution rules", "1", "E2", "01-epic.md"),
        ("05.1-story.md", "E2-S04a", "`zaumzeug doctor` — core checks", "1", "E2", "01-epic.md"),
        ("05.2-story.md", "E2-S04b", "`zaumzeug doctor` — phase-aware warnings", "1", "E2", "01-epic.md"),
        ("05.3-story.md", "E2-S04c", "`zaumzeug doctor --deploy` mode", "2", "E2", "01-epic.md"),
        ("06-story.md", "E2-S05", "`--dry-run` on serve", "1", "E2", "01-epic.md"),
        ("07-story.md", "E2-S06", "Structured logging", "1", "E2", "01-epic.md"),
        ("08-story.md", "E2-S07", "`workflow.yaml` schema (serial)", "1", "E2", "01-epic.md"),
        ("09-story.md", "E3-S05", "Mock model profile", "1", "E3", "02-epic.md"),
        ("10-story.md", "E3-S01", "ModelRouter", "1", "E3", "02-epic.md"),
        ("11-story.md", "E3-S03", "Builtin tool: `web_fetch`", "1", "E3", "02-epic.md"),
        ("12-story.md", "E3-S00", "Runtime factory (Haystack Agent builder)", "1", "E3", "02-epic.md"),
        ("13-story.md", "E3-S02", "`zaumzeug serve` (dev mode)", "1", "E3", "02-epic.md"),
        ("14-story.md", "E3-S04", "Example harness (general research agent)", "1", "E3", "02-epic.md"),
        ("15-story.md", "E3-S06", "Phase 1 test infrastructure and security baseline", "1", "E3", "02-epic.md"),
        ("16-story.md", "E3-S07", "OpenAI REST contract tests", "1", "E3", "02-epic.md"),
        ("17-story.md", "E3-S08", "`zaumzeug run` (serial workflow)", "1", "E3", "02-epic.md"),
        ("18-story.md", "E1-S01", "Cross-platform install script", "1", "E1", "03-epic.md"),
        ("19-story.md", "E1-S02", "Install shell wrappers", "1", "E1", "03-epic.md"),
        ("20-story.md", "E1-S03", "Project scaffolding on install", "1", "E1", "03-epic.md"),
        ("21-story.md", "E1-S04", "`zaumzeug init` command", "1", "E1", "03-epic.md"),
        ("22-story.md", "E1-S05", "User documentation skeleton", "1", "E1", "03-epic.md"),
        ("23-story.md", "E1-S06", "Root README", "1", "E1", "03-epic.md"),
        ("24-story.md", "E1-S07", "Cross-platform CI matrix", "1", "E1", "03-epic.md"),
        ("25-story.md", "E1-S08", "Future: `zaumzeug install-project` (blocked)", "1", "E1", "03-epic.md"),
        ("26-story.md", "E4-S01", "DSPy module loader", "2", "E4", "04-epic.md"),
        ("27.1-story.md", "E4-S02a", "Compile CLI and Phase 2 schema", "2", "E4", "04-epic.md"),
        ("27.2-story.md", "E4-S02b", "GEPA runner and artifacts", "2", "E4", "04-epic.md"),
        ("28.1-story.md", "E4-S03a", "Export contract and manifest", "2", "E4", "04-epic.md"),
        ("28.2-story.md", "E4-S03b", "Runtime `input_rewrite` preprocess", "2", "E4", "04-epic.md"),
        ("29-story.md", "E4-S04", "Haystack GEPA evaluator wrapper *(deferred)*", "2", "E4", "04-epic.md"),
        ("30-story.md", "E4-S05", "Post-compile serve uses artifact", "2", "E4", "04-epic.md"),
        ("31-story.md", "E4-S06", "`--dry-run` on compile", "2", "E4", "04-epic.md"),
        ("32-story.md", "E4-S07", "Rollback to pinned artifact run", "2", "E4", "04-epic.md"),
        ("33-story.md", "E4-S08", "Workflow diagram at compile", "2", "E4", "04-epic.md"),
        ("34-story.md", "E6-S01", "Optional `[eval]` extra", "2", "E6", "05-epic.md"),
        ("35-story.md", "E6-S02", "`zaumzeug eval` command", "2", "E6", "05-epic.md"),
        ("36-story.md", "E6-S03", "Eval gate on deploy *(traceability)*", "2", "E6", "05-epic.md"),
        ("37-story.md", "E6-S04", "`eval/` pytest scaffold", "2", "E6", "05-epic.md"),
        ("38-story.md", "E6-S05", "Trace → test case", "2", "E6", "05-epic.md"),
        ("39-story.md", "E6-S06", "HTTP black-box eval (Mode C)", "2", "E6", "05-epic.md"),
        ("40-story.md", "E6-S07", "GEPA ↔ DeepEval bridge", "2", "E6", "05-epic.md"),
        ("41-story.md", "E5-S01", "`zaumzeug deploy` command", "2", "E5", "06-epic.md"),
        ("42-story.md", "E5-S02", "Dev vs deploy copy rules", "2", "E5", "06-epic.md"),
        ("43-story.md", "E5-S03", "`zaumzeug serve --deploy`", "2", "E5", "06-epic.md"),
        ("44-story.md", "E5-S04", "`HARNESS_ROOT=deploy` environment override", "2", "E5", "06-epic.md"),
        ("45-story.md", "E5-S05", "Target ship workflow documentation", "2", "E5", "06-epic.md"),
        ("46-story.md", "E5-S06", "Deploy eval gate", "2", "E5", "06-epic.md"),
        ("47-story.md", "E5-S07", "Deploy git policy", "2", "E5", "06-epic.md"),
        ("48-story.md", "E5-S08", "Deploy platform policy", "2", "E5", "06-epic.md"),
        ("49.1-story.md", "E5-S09a", "Target install — core script", "2", "E5", "06-epic.md"),
        ("49.2-story.md", "E5-S09b", "Target install — shell wrappers", "2", "E5", "06-epic.md"),
        ("49.3-story.md", "E5-S09c", "Target install — verify integration", "2", "E5", "06-epic.md"),
        ("50-story.md", "E7-S01", "MCP tool configuration", "3", "E7", "07-epic.md"),
        ("51-story.md", "E7-S02", "Custom tool loader", "3", "E7", "07-epic.md"),
        ("52-story.md", "E7-S03", "Cursor MCP setup", "3", "E7", "07-epic.md"),
        ("53-story.md", "E7-S04", "Chainlit embedded UI", "3", "E7", "07-epic.md"),
        ("54-story.md", "E7-S05", "ACP adapter", "3", "E7", "07-epic.md"),
        ("55-story.md", "E7-S06", "MCP from deploy bundle", "3", "E7", "07-epic.md"),
        ("56-story.md", "E7-S07", "Extended builtin tools catalog", "3", "E7", "07-epic.md"),
        ("57-story.md", "E7-S08", "Web client deployment layouts", "3", "E7", "07-epic.md"),
        ("58-story.md", "E8-S01", "Pipeline exposure via `serve.expose`", "4", "E8", "08-epic.md"),
        ("59-story.md", "E8-S02", "Production auth", "4", "E8", "08-epic.md"),
        ("60-story.md", "E8-S03", "Trace → dataset ratchet", "4", "E8", "08-epic.md"),
        ("61-story.md", "E8-S04", "Optional A2A agent card *(deferred)*", "4", "E8", "08-epic.md"),
        ("62-story.md", "E8-S05", "Dockerfile template", "4", "E8", "08-epic.md"),
        ("63-story.md", "E8-S06", "DeepEval production observe (opt-in)", "4", "E8", "08-epic.md"),
    ]
    total = len(rows)
    lines = [
        "# Epic stories — index",
        "",
        "| | |",
        "|---|---|",
        "| **Document** | Individual user stories (extracted from epic files) |",
        "| **Folder** | `docs/stories/epic-stories/` |",
        f"| **Created** | 2026-07-05 |",
        f"| **Last modified** | {TODAY} |",
        "| **Related** | [Epic index](../00-README.md) · [PRD](../../prd.md) |",
        "",
        "---",
        "",
        f"Stories numbered in **global build order**. Split stories use decimal suffixes (e.g. `05.1-story.md`). **Total: {total}** story files.",
        "",
        "| File | Story | Phase | Epic |",
        "|---|---|---|---|",
    ]
    for i, (fn, sid, title, phase, epic, epic_file) in enumerate(rows, 1):
        lines.append(f"| [{fn}]({fn}) | {sid} — {title} | {phase} | [{epic}](../{epic_file}) |")
    lines.extend(["", "---", ""])
    return "\n".join(lines) + "\n"


def main() -> None:
    total = 70  # 63 - 4 + 11
    sub_stories = build_sub_stories(total)

    for fn in REMOVE:
        path = OUT / fn
        if path.exists():
            path.unlink()
            print(f"Removed {fn}")

    for fn, content in sub_stories.items():
        (OUT / fn).write_text(content, encoding="utf-8")
        print(f"Wrote {fn}")

    for path in sorted(OUT.glob("*-story.md")) + sorted(OUT.glob("*.*-story.md")):
        if path.name == "00-README.md":
            continue
        text = path.read_text(encoding="utf-8")
        patched = patch_file(text, path.name)
        if patched != text:
            path.write_text(patched, encoding="utf-8")
            print(f"Patched {path.name}")

    (OUT / "00-README.md").write_text(build_index(), encoding="utf-8")
    print("Wrote 00-README.md")


if __name__ == "__main__":
    main()
