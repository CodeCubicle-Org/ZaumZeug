# ZaumZeug — New contributor guide

| | |
|---|---|
| **Audience** | New contributors · harness developers |
| **Last updated** | 2026-07-28 |
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

---

## Optional extras

Not required for mock serve:

- **Compile / GEPA** — included in `[dev]` (`zaumzeug compile`, Phase 2; `--dry-run` validates modules/registry without GEPA; writes immutable Haystack export under `artifacts/<run_id>/`; regenerates `docs/workflow-diagram.md` (or `--workflow-diagram-only`); pin/rollback to a prior run without re-GEPA; optional `input_rewrite` applied at serve/run; mock/stub offline, live models need `.env` keys). See [user-docs/guides/compile.md](user-docs/guides/compile.md).
- **DeepEval** — `pip install "zaumzeug[eval]"` (optional extra **Done** E6-S01 — core install stays lean; `zaumzeug eval` CLI → E6-S02)
- **Provider plugins** — e.g. `openai-haystack`, `anthropic-haystack` (live models only)
- **MCP in Cursor** — `uv` + install `--cursor-mcp` (Phase 3)
- **Chainlit UI** — `hayhooks[chainlit]` (Phase 3)

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

Production targets are updated by **redeploying** a `deploy/<name>/` bundle and re-running `target_install` — not by ad-hoc `pip upgrade` on the server. Details: [installation.md — Updating dependencies](user-docs/getting-started/installation.md#updating-dependencies).

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

`zaumzeug init <name>` scaffolds another harness under `usr-harnesses/`. See [project setup](user-docs/getting-started/project-setup.md) and [your first harness](user-docs/getting-started/first-harness.md).

---

## Where to go next

| Need | Doc |
|---|---|
| Full install / updates / troubleshooting | [user-docs/getting-started/installation.md](user-docs/getting-started/installation.md) |
| Testing / CI expectations | [user-docs/guides/testing.md](user-docs/guides/testing.md) |
| User guides hub | [user-docs/README.md](user-docs/README.md) |
| Product overview (existing root README) | [README.md](README.md) |

### Maintainers only

Internal design and backlog — not required for first serve:

- [PRD](docs/prd.md)
- Cross-platform CI: [`.github/workflows/ci-matrix.yml`](.github/workflows/ci-matrix.yml)
- [Architecture](docs/architecture.md)
- [Stories / backlog](docs/stories/00-README.md)
