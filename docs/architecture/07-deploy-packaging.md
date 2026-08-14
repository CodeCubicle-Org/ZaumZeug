# Deploy packaging

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 10. Deploy packager

Requirements: **[PRD E5](../prd.md#epic-e5--deploy-packaging-phase-2)**.

### 10.1 Dev vs deploy

| | `usr-harnesses/<harness>/` | `deploy/<harness>/` |
|---|---|---|
| Purpose | Author, compile, experiment | Ship and run |
| Edited by | Developer | **Generated** by `zaumzeug deploy` |
| `harness.yaml`, `workflow.yaml` | Full | Stripped — runtime + serve + workflow only |
| `agents/<agent-name>/` | Full per-agent tree | Runtime subset per agent |
| `agents/<agent-name>/modules/`, `skills/` | Present | **Excluded** |
| `agents/<agent-name>/artifacts/` | Working / `current` | **Pinned copy** per agent |
| `agents/<agent-name>/agents-models.yaml` | Dev | **Included** — merged at packager |
| `data/`, `eval/` | Present | **Excluded** |
| `pipelines/` | Haystack YAML | **Included** — ids in `serve.expose` only (Phase 4+) |

**Runtime-reference rules (packager v1):**

| Asset | Copy when |
|---|---|
| `agents/<name>/prompts/*`, `artifacts/*` | Referenced by that agent's `agent.yaml` |
| `agents/<name>/agents-models.yaml` | Always (required per agent) |
| `agents/<name>/tools/*.py` | Listed in that agent's `tools.custom` (path, dotted module, or `module:attr` — resolved to `tools/<name>.py`) |
| `agents/<name>/hooks.py` | `hooks.enabled: true` in that agent's `agent.yaml` |
| `pipelines/*` | Pipeline id listed in `serve.expose` |
| `docs/workflow-diagram.md` | Generated at compile (E4-S08) | **Included** in `deploy/<harness>/docs/` |
| `agents/<name>/modules/`, `skills/`, `data/`, `eval/` | Dev only | **Never** |

Requirements: [PRD E5.2](../prd.md#epic-e5--deploy-packaging-phase-2). **Done** ([E5-S02](../stories/epic-stories/42-story.md), 2026-07-28) — `resolve_deploy_copy_plan` / `assert_required_paths` in `deploy/copy_rules.py`; golden `tests/integration/deploy/test_deploy_golden.py`.

### 10.2 Packager steps

`zaumzeug deploy <name>`:

1. Validate (`zaumzeug doctor`, resolvable runtime path).
2. Apply **eval gate** per [§6.4](05-configuration.md#64-deploy-eval-gate).
3. Write stripped `harness.yaml` (no `compile`/`eval`/`deploy`).
4. Pin per-agent artifacts; copy `agents/*/agents-models.yaml`, tools, pipelines, hooks, `docs/workflow-diagram.md`.
5. Merge harness `models.yaml`; write `manifest.json` (per-agent `artifact_run_id` map), `README.deploy.md`.
6. Copy `target_install.py`, `target-install.sh`, `target-install.ps1` into `deploy/<name>/` (from `install/templates/` or SDK `install/`).

Idempotent — overwrites `deploy/<name>/`. Future: `zaumzeug export` tarball of bundle.

**Implementation (E6-S03 / E5-S06, 2026-07-28):** Step 2 (eval gate) is live in `src/zaumzeug/deploy/packager.py` (`apply_eval_gate` → `package_harness`); CLI `zaumzeug deploy --eval-gate`.

**Implementation (E5-S02, 2026-07-28):** `resolve_deploy_copy_plan` / `assert_required_paths` encode the §10.1 include matrix; packager validates before writing `deploy/<name>/`. Tests: `tests/unit/deploy/test_copy_rules.py` (`e5_s02`), golden `tests/integration/deploy/test_deploy_golden.py`.

**Implementation (E7-S02, 2026-08-14):** `custom_tool_source_rel` in `deploy/copy_rules.py` maps dotted `tools.search_docs` and `tools.search_docs:attr` entries to `tools/search_docs.py`, so deploy still copies **listed** custom-tool files only. Tests: `tests/unit/deploy/test_copy_rules.py::test_e7_s02_ac4_custom_tools_in_deploy`.

**Implementation (E5-S01, 2026-07-28):** Steps 1 and 3–6 are live: doctor preflight → `write_deploy_bundle` (stripped yaml, pin/copy, merged harness `models.yaml`, `manifest.json`, `README.deploy.md` from `install/templates/deploy/`, target install scripts from `install/`). Tests: `tests/integration/deploy/test_deploy.py` (`e5_s01`). Target install **Done** ([E5-S09a](../stories/epic-stories/49.1-story.md)–[E5-S09c](../stories/epic-stories/49.3-story.md), 2026-07-29) — core, wrappers, `--verify`.

**Implementation (E6-S04, 2026-07-28):** `deploy/copy_rules.py` exports `is_excluded_from_deploy()` so `eval/` (and other §10.1 dev-only paths) are marked excluded. Strip helpers (`strip_harness_yaml` / `strip_agent_yaml`) landed with E5-S01. Shared test: `tests/unit/deploy/test_copy_rules.py::test_e5_s02_excludes_eval`.

### 10.3 Deploy `manifest.json`

Written to **`deploy/<name>/manifest.json`** only (not to be confused with **`artifact-manifest.json`** under `artifacts/` — [§5.3](04-data-flows.md#53-artifact-layout)).

```json
{
  "build_id": "uuid",
  "source_git_sha": "abc123",
  "harness_yaml_hash": "sha256...",
  "artifact_run_id": "20260624-001",
  "created_at": "2026-06-24T12:00:00Z"
}
```

`target_install` preflight verifies this file plus `harness.yaml` in the bundle directory.

**Implementation (E4-S07, 2026-07-28):** Pin contract — `artifact_run_id` (string or per-agent map) selects an immutable compile run; `zaumzeug doctor --deploy` validates the pinned `artifact-manifest.json`. Dev-side rollback (pin `agent.artifact` without re-GEPA): [user-docs/guides/compile.md](../user-docs/guides/compile.md#rollback-to-a-pinned-run). Tests: `tests/integration/deploy/test_deploy_pin.py`.

**Implementation (E5-S01, 2026-07-28):** `zaumzeug deploy` writes `manifest.json` with per-agent `artifact_run_id` map (empty `{}` when all agents use `system_prompt` only). Tests: `tests/integration/deploy/test_deploy.py::test_e5_s01_ac2_manifest_json_schema`.

### 10.4 Git and `.gitignore`

| Policy | Recommendation |
|---|---|
| **Default** | `deploy/` and `usr-harnesses/*/artifacts/` in `.gitignore` |
| **Release tags** | Optionally commit `deploy/<name>/` for audited releases |
| **CI** | Build `deploy/` in pipeline; upload as deployment artifact |

**Implementation (E1-S03, 2026-07-22):** `client_install.py` ensures `.gitignore` includes `.venv`, `.env`, `/deploy/`, and `artifacts/` (copy/merge, idempotent).

**Implementation (E5-S07, 2026-07-28):** Scaffolding also ensures `usr-harnesses/*/artifacts/` (Architecture §10.4 default). Broad `artifacts/` remains so agent-level `agents/<name>/artifacts/` trees stay ignored. Release-commit and CI upload options documented in [user-docs/guides/deploy.md](../user-docs/guides/deploy.md#git-policy-for-deploy-bundles), [CONTRIBUTING.md](../../CONTRIBUTING.md#deploy-git-policy-maintainers), and commented example in [`.github/workflows/ci-matrix.yml`](../../.github/workflows/ci-matrix.yml). Tests: `tests/unit/install/test_scaffolding.py` (`test_e5_s07_ac1_gitignore_deploy_and_artifacts`).

### 10.5 Production server dependencies

| Component | Dev machine | Production server |
|---|---|---|
| Python | 3.11+ | 3.11+ |
| `pip install zaumzeug` | Yes (editable `[dev]` ok) | Yes (**runtime** install; no `[eval]` unless ops explicitly want eval on server) |
| DSPy, GEPA | Yes (compile) | **No** — compile on dev/CI only |
| DeepEval | Optional (`[eval]` ✅ E6-S01) | **No** (default) |
| `usr-harnesses/<name>/` | Yes | **No** |
| `deploy/<name>/` | Output of deploy | **Yes** — ship this folder |
| `target_install.py` (in bundle) | N/A | **Yes** — run once on target to install runtime deps |
| `.env` (API keys) | Yes | Yes — **never** inside bundle; create on target |
| Haystack/Hayhooks | Via SDK | Via SDK |

**Target command on server:** `zaumzeug serve <name> --deploy` (or `HARNESS_ROOT=deploy`).

**Implementation (E5-S03, 2026-07-28):** Full Hayhooks serve from `deploy/<name>/` is live — same OpenAI REST as dev, fails on missing/invalid manifest, works without `usr-harnesses/`. Tests: `tests/integration/deploy/test_serve_deploy.py`.

**Implementation (E5-S04, 2026-07-28):** `HARNESS_ROOT=deploy` is the env equivalent of `--deploy` for serve / mcp / acp (and doctor / run) via `config/harness_root.resolve_harness_path()`. Docs: `README.deploy.md`, CLI reference. Tests: `tests/unit/deploy/test_harness_root.py` (`e5_s04`). Linux CI smoke **Done** ([E5-S08](../stories/epic-stories/48-story.md), 2026-07-29).

**Implementation (E5-S05, 2026-07-28):** Target ship workflow documented — copy `deploy/<name>/` → `target_install` → create `.env` → `zaumzeug serve --deploy`. Runtime-only `pip install zaumzeug` (no DSPy/GEPA/DeepEval); Python 3.11+ prerequisite; `.env` never in bundle. Docs: `install/templates/deploy/README.deploy.md`, [user-docs/guides/deploy.md](../user-docs/guides/deploy.md), root README production note. Tests: `tests/integration/deploy/test_target_install.py` (`e5_s05`) + `test_deploy.py::test_e5_s05_ac5_no_env_in_bundle`.

### 10.6 Deploy platform targets

Requirements: **[PRD E5.8](../prd.md#epic-e5--deploy-packaging-phase-2)**.

| Role | Windows | macOS | Linux | Notes |
|---|---|---|---|---|
| **Developer workstation** | Primary | Primary | Primary | Install, serve, compile, deploy CLI — CI matrix on all three (E1.7) |
| **Production server** | Best-effort | Best-effort | **Primary** | Ops target: Linux VM, bare metal, or container |
| **CI — Phase 1** | Smoke | Smoke | Smoke | Install, doctor, dry-run, mock-model serve |
| **CI — Phase 2+** | Optional | Optional | **Required** | `zaumzeug deploy` → `zaumzeug serve --deploy` smoke on `ubuntu-latest` |

The `deploy/<name>/` bundle is **OS-neutral** (Python 3.11+, pinned yaml/artifacts, runtime tools only). Production docs (`README.deploy.md`) must state Linux as the supported ops target and reference optional Dockerfile (E8.5). Windows/macOS production serve is not CI-gated in v1 — report issues as best-effort.

**Implementation (E5-S08, 2026-07-29):** Platform matrix in `install/templates/deploy/README.deploy.md` + [user-docs/guides/deploy.md](../user-docs/guides/deploy.md#platforms). OS-neutral bundle test: `tests/integration/deploy/test_deploy_golden.py` (`test_e5_s08_ac2_os_neutral_bundle`). Phase 2+ Linux CI: `zaumzeug deploy example` → `install/ci_serve_smoke.py example --deploy` on `ubuntu-latest` ([ci-matrix.yml](../../.github/workflows/ci-matrix.yml)).

### 10.7 Target runtime install script

Requirements: **[PRD E5.9](../prd.md#epic-e5--deploy-packaging-phase-2)**.

Runs on the **target machine** after the user copies `deploy/<name>/` — desktop PC or server. **Does not install Python**; requires Python 3.11+ already on PATH.

```text
1. Preflight
   ├─ Detect OS: Windows | macOS | Linux
   ├─ Require Python 3.11+
   ├─ Resolve deploy bundle dir (--deploy-dir, default: **current working directory** — run from `deploy/<name>/` so cwd contains `harness.yaml` and `manifest.json`)
   └─ Verify deploy `manifest.json` + `harness.yaml` present

2. Virtual environment (optional)
   ├─ Create .venv beside deploy bundle if missing (unless --skip-venv)
   └─ Use venv python for all pip / harness calls

3. Install runtime dependencies
   ├─ pip install zaumzeug          # Haystack, Hayhooks — NOT [dev], [eval], DSPy, GEPA
   └─ harness --version

4. Validate bundle
   ├─ zaumzeug doctor <name> --deploy
   └─ Optional --verify: zaumzeug serve <name> --deploy --dry-run

5. Environment setup
   ├─ Copy .env.example → .env if .env missing (never overwrite)
   └─ Print: zaumzeug serve <name> --deploy  (and HARNESS_ROOT=deploy if needed)
```

**Invocation on target:**

| OS | Command |
|---|---|
| **Windows (PowerShell)** | `.\deploy\my_agent\target-install.ps1` |
| **macOS / Linux** | `./deploy/my_agent/target-install.sh` |
| **Any OS** | `python deploy/my_agent/target_install.py` |

Bundled copy lives at `deploy/<name>/target_install.py` so the folder is self-describing when copied alone.

**Implementation (E5-S09a, 2026-07-29):** `install/target_install.py` creates optional `.venv`, runs `pip install zaumzeug` (runtime only), seeds `.env` from `.env.example` when missing, and preflights `harness.yaml` + `manifest.json`. Tests: `tests/integration/deploy/test_target_install.py` (`e5_s09_*`).

**Implementation (E5-S09b, 2026-07-29):** `install/target-install.sh` / `target-install.ps1` forward args to sibling `target_install.py` with exit-code parity (same pattern as E1-S02). Bundled into each `deploy/<name>/` by the packager. Tests: `test_e5_s09b_*` + `test_e5_s09_ac7_scripts_in_bundle`.

**Implementation (E5-S09c, 2026-07-29):** `--verify` runs `zaumzeug doctor <name> --deploy` then `zaumzeug serve <name> --deploy --dry-run` from the project root that contains `deploy/<name>/`, using the install Python; non-zero exit on failure. Tests: `test_e5_s09_ac4_*` / `test_e5_s09_ac6_*` / `test_e5_s09c_*`.

**Implementation (E5-S05, 2026-07-28):** Documented ship workflow for this script — [user-docs/guides/deploy.md](../user-docs/guides/deploy.md) + bundle `README.deploy.md` (Win/macOS/Linux table, Python 3.11+, `.env` never in bundle). Tests: `tests/integration/deploy/test_target_install.py`.

---
