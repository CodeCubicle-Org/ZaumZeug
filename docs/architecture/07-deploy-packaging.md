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
| `agents/<name>/tools/*.py` | Listed in that agent's `tools.custom` |
| `agents/<name>/hooks.py` | `hooks.enabled: true` in that agent's `agent.yaml` |
| `pipelines/*` | Pipeline id listed in `serve.expose` |
| `docs/workflow-diagram.md` | Generated at compile (E4-S08) | **Included** in `deploy/<harness>/docs/` |
| `agents/<name>/modules/`, `skills/`, `data/`, `eval/` | Dev only | **Never** |

Requirements: [PRD E5.2](../prd.md#epic-e5--deploy-packaging-phase-2).

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

**Implementation (E5-S01, 2026-07-28):** Steps 1 and 3–6 are live: doctor preflight → `write_deploy_bundle` (stripped yaml, pin/copy, merged harness `models.yaml`, `manifest.json`, `README.deploy.md` from `install/templates/deploy/`, target install scripts from `install/`). Tests: `tests/integration/deploy/test_deploy.py` (`e5_s01`). Full include/pin golden matrix remains [E5-S02](../stories/epic-stories/42-story.md); full `target_install` behaviour remains [E5-S09](../stories/epic-stories/49.1-story.md).

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

**Implementation (E1-S03, 2026-07-22):** `client_install.py` ensures `.gitignore` includes `.venv`, `.env`, `deploy/`, and `artifacts/` (copy/merge, idempotent). Narrower `usr-harnesses/*/artifacts/` pattern remains an [E5-S07](../stories/epic-stories/47-story.md) extension. Tests: `tests/unit/install/test_scaffolding.py` (`test_e1_s03_ac3_gitignore_entries`).

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

### 10.6 Deploy platform targets

Requirements: **[PRD E5.8](../prd.md#epic-e5--deploy-packaging-phase-2)**.

| Role | Windows | macOS | Linux | Notes |
|---|---|---|---|---|
| **Developer workstation** | Primary | Primary | Primary | Install, serve, compile, deploy CLI — CI matrix on all three (E1.7) |
| **Production server** | Best-effort | Best-effort | **Primary** | Ops target: Linux VM, bare metal, or container |
| **CI — Phase 1** | Smoke | Smoke | Smoke | Install, doctor, dry-run, mock-model serve |
| **CI — Phase 2+** | Optional | Optional | **Required** | `zaumzeug deploy` → `zaumzeug serve --deploy` smoke on `ubuntu-latest` |

The `deploy/<name>/` bundle is **OS-neutral** (Python 3.11+, pinned yaml/artifacts, runtime tools only). Production docs (`README.deploy.md`) must state Linux as the supported ops target and reference optional Dockerfile (E8.5). Windows/macOS production serve is not CI-gated in v1 — report issues as best-effort.

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

**Implementation (E5-S01, 2026-07-28):** `install/target_install.py` + `target-install.sh` / `target-install.ps1` exist and are copied into every bundle. The scripts currently preflight `harness.yaml` + `manifest.json` and print next steps; full venv / `pip install zaumzeug` / doctor `--deploy` / `--verify` remains [E5-S09](../stories/epic-stories/49.1-story.md).

---
