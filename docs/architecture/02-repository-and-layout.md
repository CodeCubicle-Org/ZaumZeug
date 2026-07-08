# Repository and layout

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 3. Repository structure

```text
HarnessDevelopment/
├── src/zaumzeug/          # SDK internals
│   ├── cli.py
│   ├── config/               # Pydantic schemas, loaders (E2-S01), models merge (E2-S02), resolver (E2-S03)
│   ├── doctor/               # Preflight checks — pass/warn/fail (E2-S04a–S04c)
│   ├── runtime/              # ModelRouter (E3-S01, E3-S05), agent factory, tool registry
│   ├── compile/              # DSPy loader, GEPA runner, export contract
│   ├── deploy/               # usr-harnesses/ → deploy/ packager
│   ├── eval/                 # Optional DeepEval bridge
│   ├── serve/                # validate_serve + dry-run (E2-S05); Hayhooks runner (E3-S02)
│   ├── integrations/         # mock (E3-S05), haystack provider map (E3-S01); DSPy, GEPA, LiteLLM adapters
│   └── fixtures/responses/   # bundled mock LLM fixtures (pip install; mirrors tests/fixtures/responses/)
├── usr-harnesses/<name>/         # USER dev workspace (author, compile, experiment)
├── deploy/<name>/            # PRODUCTION bundle (generated)
├── config/models.yaml        # Global model registry defaults
├── install/                  # client_install.py, target_install.py + templates
├── user-docs/                # End-user manuals
├── docs/                     # PRD, architecture, ideation archive
└── tests/
```

### 3.1 Separation rules

| Path | Purpose | Edited by |
|---|---|---|
| `src/zaumzeug/` | Framework | Maintainers |
| `usr-harnesses/<name>/` | Development harness | Developer |
| `deploy/<name>/` | Production bundle | `zaumzeug deploy` only |
| `user-docs/` | Public docs | Docs authors |
| `docs/` | Internal design | Maintainers |

### 3.2 Package naming

**Resolved ([PRD §12](../prd.md#12-open-decisions-blockers-for-some-stories)):** product name **ZaumZeug**.

| Surface | Name |
|---|---|
| **Product / brand** | **ZaumZeug** |
| PyPI | `zaumzeug` |
| Import | `zaumzeug` |
| CLI | `zaumzeug` |
| Entry point | `zaumzeug = "zaumzeug.cli:main"` |
| Source layout | `src/zaumzeug/` |

**Domain terms:** `harness.yaml`, `usr-harnesses/`, `deploy/` refer to a **multi-agent harness instance**, not the product name and not a single agent. Env vars `HARNESS_ROOT`, `HARNESS_LOG_LEVEL` keep the domain prefix.

### 3.3 Harness folder layout

Each harness lives under `usr-harnesses/<harness-name>/` (dev) or `deploy/<harness-name>/` (production subset). **Every agent** has a **uniquely named** subfolder under `agents/`:

```text
usr-harnesses/<harness-name>/
├── harness.yaml              # harness entry: name, serve, deploy, eval
├── workflow.yaml             # stage graph: which agents run, in what order (parallel later)
├── models.yaml               # optional harness-wide shared registry (aliases only)
├── agents/
│   ├── <agent-name>/         # unique agent id — folder name = agent name
│   │   ├── agent.yaml        # role config: prompts, tools, compile, hooks
│   │   ├── agents-models.yaml  # THIS agent's LLM registry (not models.yaml)
│   │   ├── prompts/
│   │   ├── tools/            # role-specific custom tools
│   │   ├── modules/          # DSPy modules (compile-time; excluded from deploy)
│   │   ├── skills/           # GEPA-optimizable skill files (dev)
│   │   ├── hooks.py          # optional lifecycle hooks for this role
│   │   └── artifacts/        # GEPA exports for this agent (pinned per agent on deploy)
│   └── <another-agent-name>/
│       ├── agent.yaml
│       ├── agents-models.yaml
│       └── ...
├── pipelines/                # Haystack YAML — deterministic steps, orchestration (Phase 4+)
├── data/                     # shared queue, context, train/val JSONL (dev)
├── docs/                     # generated harness docs (workflow-diagram.md at compile)
└── eval/                     # harness-level optional DeepEval pytest (dev only)
    ├── test_*.py
    └── metrics.py
```

**Agent naming:** `<agent-name>` must be unique within the harness (e.g. `recon-analyst`, `vuln-hunter`, `finding-validator`). Used in `workflow.yaml` stage references and CLI (`zaumzeug compile <harness> --agent <agent-name>`).

**Extension points** (user folder only — never in `src/zaumzeug/`). Configuration is YAML-first; optional Python lives under `agents/<agent-name>/modules/`, `tools/`, or `hooks.py` — no top-level `harness.py` bootstrap file.

| Need | Where | How |
|---|---|---|
| Agent role config | `agents/<agent-name>/agent.yaml` | Prompts, tools, compile, hooks per role |
| Per-agent LLM | `agents/<agent-name>/agents-models.yaml` | Independent provider/model per agent |
| Workflow | `workflow.yaml` | Serial stages; `parallelism` per stage (later) |
| Custom agent logic | `agents/<agent-name>/modules/*.py` | DSPy `Module`; `compile.module` in `agent.yaml` |
| Custom tools | `agents/<agent-name>/tools/*.py` | `tools.custom` in `agent.yaml` |
| Custom pipelines | `pipelines/` | YAML or `PipelineWrapper`; `serve.expose` in `harness.yaml` |
| GEPA metrics | `agents/<agent-name>/modules/metrics.py` | Textual feedback per agent |
| DeepEval tests | `eval/test_*.py` | Harness-level; may target specific agents |
| Prompts / skills | `agents/<agent-name>/prompts/`, `skills/` | Per-agent; GEPA-optimized |
| Lifecycle hooks | `agents/<agent-name>/hooks.py` | Per-agent sensors |

#### 3.3.1 Model config files (naming)

Three distinct `models` files — do not conflate:

| File | Scope | Purpose |
|---|---|---|
| **`config/models.yaml`** | Project global | Shared defaults for all harnesses in the repo |
| **`usr-harnesses/<harness>/models.yaml`** | Harness (optional) | Shared registry aliases inherited by agents when not overridden |
| **`agents/<agent-name>/agents-models.yaml`** | **Single agent role** | LLM registry for that agent only — may use a completely different provider than sibling agents |

Each `agents-models.yaml` deep-merges over harness `models.yaml` (if present) over global `config/models.yaml`. When the workflow runs stage `finding-validator`, `ModelRouter` loads **that agent's** merged `agents-models.yaml` and `default_model_id` — not the previous stage's model.

Secrets remain in `.env` only; all model files hold provider + model id + generation kwargs.

### 3.4 Install scripts (dev vs target)

| Script | Scope | When |
|---|---|---|
| `install/client_install.py` | **Dev machine once** — venv, editable install, `usr-harnesses/example/`, user-docs skeleton, global `config/models.yaml`, `.env.example` | First clone or new dev machine |
| `install/target_install.py` | **Target machine once per deploy** — runtime `pip install zaumzeug`, optional venv, `zaumzeug doctor --deploy`, `.env` hints | After copying `deploy/<name>/` to desktop PC or server |
| `zaumzeug init <name>` | **Per harness** — scaffold `usr-harnesses/<name>/` from template | Additional harnesses after project setup |

**Wrappers:** `client-install.sh` / `client-install.ps1` delegate to `client_install.py`; `target-install.sh` / `target-install.ps1` delegate to `target_install.py`. OS-specific behavior lives only in the Python scripts ([§2.5](01-overview-and-principles.md#25-cross-platform-portability)).

**Client install flags:** `--verify`, `--no-example`, `--skip-venv` (CI), `--cursor-mcp`. CI matrix per [PRD E1.7](../prd.md#epic-e1--onboarding-and-project-setup-phase-1).

**Target install flags:** `--deploy-dir` (default: directory containing `harness.yaml` — typically the bundle root when the script is run from `deploy/<name>/`), `--skip-venv`, `--verify` (doctor + serve dry-run). See [PRD E5.9](../prd.md#epic-e5--deploy-packaging-phase-2) and [§10.7](07-deploy-packaging.md#107-target-runtime-install-script).

**Updating dependencies (dev machine):** Re-run `client_install.py` after `git pull` (idempotent; refreshes `pip install -e ".[dev]"`). Optional extras and provider plugins use separate `pip install -U` commands. Production targets update via redeploy + bundled `target_install`, not ad hoc upgrades. User-facing summary: [PRD §7.4](../prd.md#74-user-installation-guide-content-for-readme--phase-1).

### 3.5 User documentation

End-user docs live in `user-docs/` (Markdown) — separate from internal `docs/`. Install copies skeleton:

```text
user-docs/
├── README.md
├── getting-started/   # installation, project-setup, first-harness
├── guides/
│   ├── multi-agent-workflow.md   # workflow.yaml, agents vs pipelines, control flow
│   └── testing.md                # unit, integration, eval; mock profile; CI tiers
└── reference/cli.md
```

Install copies this tree from `install/templates/user-docs/` ([§3.4](02-repository-and-layout.md#34-install-scripts-dev-vs-target)). End-user guides: [multi-agent-workflow.md](../user-docs/guides/multi-agent-workflow.md), [testing.md](../user-docs/guides/testing.md).

**Implementation (E2-S06, 2026-07-08):** [user-docs/reference/cli.md](../user-docs/reference/cli.md) documents `HARNESS_LOG_LEVEL`, `--verbose` on serve/compile, and related CLI flags. Install template: `install/templates/user-docs/reference/cli.md`.

---
