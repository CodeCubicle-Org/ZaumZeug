# ZaumZeug — New contributor guide

| | |
|---|---|
| **Audience** | New contributors · harness developers |
| **Last updated** | 2026-08-21 (E7-S07 extended builtin catalog) |
| **Related** | [Root README](README.md) · [Installation (full)](user-docs/getting-started/installation.md) |

Short entry point for vision, install, and first commands — without reading the full PRD. Depth lives in [user-docs/getting-started/installation.md](user-docs/getting-started/installation.md).

**Vision:** A harness SDK and factory for configurable multi-agent AI workflows.

**Formula:** `Harness = Workflow + Agents + Machinery`

---

## Prerequisites (summary)

| Requirement | Required? | Notes |
|---|---|---|
| **Python 3.11+** | Yes | Only hard prerequisite for the default dev install |
| **Git** | Optional | Install warns if missing; not blocking |
| **`uv` / `uvx`** | Optional | Needed for MCP tool servers; not required for Phase 1 mock serve |
| **API keys** (`.env`) | Live models only | Not needed for mock; copy from `.env.example` later |

You do **not** manually install Haystack, DSPy, GEPA, or LiteLLM — the client install runs `pip install -e ".[dev]"` inside a project `.venv`.

---

## Install

| Platform | Command |
|---|---|
| **Windows** (PowerShell) | `.\install\client-install.ps1` |
| **Windows** (cmd) | `python install\client_install.py` |
| **macOS / Linux** | `./install/client-install.sh` |
| **Any OS** | `python install/client_install.py` |

| Expectation | Planning range |
|---|---|
| Time to first `zaumzeug serve` | **Target < 15 minutes** on typical broadband (mock model, no API keys); up to ~30 minutes on slow networks |
| Dev venv size (`pip install -e ".[dev]"`) | **~1–2.5 GB** (approximate; first install dominates download time) |

Optional flags (same on every platform): `--verify`, `--no-example`, `--skip-venv`, `--cursor-mcp`.

Full walkthrough, disk breakdown, and troubleshooting: [installation.md](user-docs/getting-started/installation.md).

---

## Mock-first quick start

Use the **mock model** first (no API keys). The example harness ships with `default_model_id: mock`.

```powershell
# Windows
.\.venv\Scripts\Activate.ps1
zaumzeug serve example              # mock model — no .env required
```

```bash
# macOS / Linux
source .venv/bin/activate
zaumzeug serve example              # mock model — no .env required
```

Phase 1 path: install → `zaumzeug serve example` with **mock** → optional `.env` + provider package for live models.

Useful next commands: `zaumzeug doctor`, `zaumzeug init <name>`, `zaumzeug run <name>`, `zaumzeug serve <name> --dry-run`, `zaumzeug compile <name> --dry-run`, `zaumzeug compile <name> --workflow-diagram-only`.

For batch / local-model runs, `zaumzeug run` supports optional `runtime.retry`, agent `output.format: json`, and INFO stage logs (`HARNESS_LOG_LEVEL=INFO`) — see [Run reliability](user-docs/guides/multi-agent-workflow.md#run-reliability-zaumzeug-run) (E8-S07).

---

## Optional extras

Not required for mock serve:

- **Compile / GEPA** — included in `[dev]` (`zaumzeug compile`, Phase 2; `--dry-run` validates modules/registry without GEPA; writes immutable Haystack export under `artifacts/<run_id>/`; regenerates `docs/workflow-diagram.md` (or `--workflow-diagram-only`); pin/rollback to a prior run without re-GEPA; optional `input_rewrite` applied at serve/run; mock/stub offline, live models need `.env` keys). See [user-docs/guides/compile.md](user-docs/guides/compile.md).
- **DeepEval** — `pip install "zaumzeug[eval]"` (optional extra **Done** E6-S01 — core install stays lean; `zaumzeug eval` CLI **Done** E6-S02; deploy eval gate **Done** E6-S03 / E5-S06 — `deploy.eval_gate` / `--eval-gate`; harness `eval/` pytest scaffold **Done** E6-S04 — `zaumzeug init --with-eval` / `deepeval test run`; trace → test case **Done** E6-S05 — `data/traces/` + `zaumzeug eval --trace`; Mode C HTTP black-box **Done** E6-S06 — `zaumzeug eval --base-url` / `eval.base_url`, staging/debug only; GEPA ↔ DeepEval bridge **Done** E6-S07 — `append_failed_eval_to_train`, shared val aliases, optional `modules/metrics.py` DeepEval metric)
- **Deploy packaging** — `zaumzeug deploy` (**Done** E5-S01 / E5-S02) writes `deploy/<name>/`; ops ships with copy → `target_install` → `.env` → `zaumzeug serve <name> --deploy` (**Done** E5-S03) or `zaumzeug mcp <name> --deploy` (**Done** E7-S06) or `HARNESS_ROOT=deploy` (**Done** E5-S04). Ship workflow docs **Done** E5-S05 — see [Deploy and ship](user-docs/guides/deploy.md), [CLI — serve](user-docs/reference/cli.md#zaumzeug-serve) / [CLI — mcp](user-docs/reference/cli.md#zaumzeug-mcp) / [Global environment](user-docs/reference/cli.md#global-environment), and bundle `README.deploy.md`. Deploy git policy **Done** E5-S07 — default ignore `deploy/` + `usr-harnesses/*/artifacts/`; optional release commit or CI artifact upload ([Git policy](user-docs/guides/deploy.md#git-policy-for-deploy-bundles)). Platform policy **Done** E5-S08 — Linux-first production; OS-neutral bundle; Win/macOS best-effort not CI-gated; Linux CI `deploy` → `serve --deploy` smoke ([Platforms](user-docs/guides/deploy.md#platforms)). Target install **Done** E5-S09a/b/c — optional `.venv`, `pip install zaumzeug` (runtime only), `.env` seed, wrappers, `--verify` (doctor `--deploy` + serve `--deploy --dry-run`) ([Deploy and ship — Target install](user-docs/guides/deploy.md#target-install--win--macos--linux)).
- **Provider plugins** — e.g. `openai-haystack`, `anthropic-haystack` (live models only)
- **MCP in Cursor** — install `--cursor-mcp` writes live `.cursor/mcp.json`; `uv` only if the harness uses stdio `tools.mcp`. Production: `zaumzeug mcp <name> --deploy` (or `HARNESS_ROOT=deploy`). See [Cursor MCP setup](user-docs/guides/cursor-mcp.md).
- **Builtin tools** — `tools.builtin` on `agent.yaml`: `web_fetch` (Phase 1), `calculator` and `read_file` (Phase 3; `read_file` sandboxed to the harness folder). `search_docs` is Phase 4. See [Custom tools — Builtin catalog](user-docs/guides/custom-tools.md#builtin-catalog).
- **ACP in Zed / JetBrains** — `zaumzeug acp <harness>` (Agent Client Protocol stdio JSON-RPC; not IBM ACP/A2A). Cursor uses MCP. See [ACP](user-docs/guides/acp.md).
- **Chainlit UI** — `pip install "hayhooks[chainlit]"` then `serve.hayhooks.chainlit: true` (embedded `/chat` on the serve port; optional, not a primary-UI decision). See [Web deployment](user-docs/guides/web-deployment.md).

---

## Updating dependencies

There is **no `zaumzeug update-deps` command in v1**. Re-run the install path (idempotent) after pulls.

```powershell
# Windows — after git pull
git pull
.\install\client-install.ps1 --verify
```

```bash
# macOS / Linux — after git pull
git pull
./install/client-install.sh --verify
```

Manual refresh in the venv:

```bash
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
zaumzeug doctor
```

Production targets are updated by **redeploying** a `deploy/<name>/` bundle and re-running `target_install` — not by ad-hoc `pip upgrade` on the server. Details: [installation.md — Updating dependencies](user-docs/getting-started/installation.md#updating-dependencies) and [Deploy and ship](user-docs/guides/deploy.md).

---

## Project layout (abbreviated)

```text
├── usr-harnesses/     # Dev workspace — author, compile, experiment
├── deploy/            # Production bundles (generated; do not hand-edit)
├── config/            # Shared models.yaml (and related project config)
├── user-docs/         # End-user guides
├── install/           # Client install + templates
└── src/zaumzeug/      # SDK source
```

`zaumzeug init <name>` scaffolds another harness under `usr-harnesses/`. Pass `--with-eval` to include an optional DeepEval pytest scaffold under `eval/` (dev-only; excluded from deploy). See [project setup](user-docs/getting-started/project-setup.md) and [your first harness](user-docs/getting-started/first-harness.md).

---

## Where to go next

| Need | Doc |
|---|---|
| Full install / updates / troubleshooting | [user-docs/getting-started/installation.md](user-docs/getting-started/installation.md) |
| Testing / CI expectations | [user-docs/guides/testing.md](user-docs/guides/testing.md) |
| ACP in Zed / JetBrains | [user-docs/guides/acp.md](user-docs/guides/acp.md) |
| User guides hub | [user-docs/README.md](user-docs/README.md) |
| Product overview (existing root README) | [README.md](README.md) |

### Maintainers only

Internal design and backlog — not required for first serve:

- [PRD](docs/prd.md)
- Cross-platform CI: [`.github/workflows/ci-matrix.yml`](.github/workflows/ci-matrix.yml)
- [Architecture](docs/architecture.md)
- [Stories / backlog](docs/stories/00-README.md)

#### Deploy git policy (maintainers)

Default `.gitignore` (via install scaffolding) keeps `deploy/` and compile artifacts out of git — local-only bundles. Two audited alternatives:

1. **Release commit** — force-add a single bundle for a tag (`git add -f deploy/<name>/`), then tag. Documented for harness teams in [Deploy and ship — Git policy](user-docs/guides/deploy.md#git-policy-for-deploy-bundles).
2. **CI workflow artifact** — run `zaumzeug deploy <name>` in CI and upload `deploy/<name>/` with `actions/upload-artifact` (see commented example in [ci-matrix.yml](.github/workflows/ci-matrix.yml)). Prefer this when you want an audited binary without permanent git history of generated trees.

Never commit `.env` (always gitignored).

#### Deploy platform policy (maintainers)

Production serve is **Linux-first** (VM, bare metal, Docker/K8s). The deploy bundle is OS-neutral; Windows/macOS production serve is best-effort and **not CI-gated** in v1. Phase 2+ CI requires `zaumzeug deploy example` → `ci_serve_smoke.py example --deploy` on `ubuntu-latest` only ([ci-matrix.yml](.github/workflows/ci-matrix.yml)). See [Platforms](user-docs/guides/deploy.md#platforms) and [Architecture §10.6](docs/architecture/07-deploy-packaging.md#106-deploy-platform-targets).
