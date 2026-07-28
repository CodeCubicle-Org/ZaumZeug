# Installation

| | |
|---|---|
| **Audience** | New developers |
| **Last updated** | 2026-07-22 |

Get from a fresh clone to a working ZaumZeug dev environment with one command. This page is the full walkthrough (prerequisites, effort, disk, extras, updates, troubleshooting). The short new-contributor summary is [CONTRIBUTING.md](../../CONTRIBUTING.md); it links here for depth.

Technical install behavior (script steps, flags, idempotency): see internal Architecture §3.4.

---

## Prerequisites

| Requirement | Required? | Notes |
|---|---|---|
| **Python 3.11+** | Yes | Only hard prerequisite for the default dev install |
| **Git** | Optional | Install script warns if missing; not blocking |
| **`uv` / `uvx`** | Optional | Needed when a harness uses MCP tool servers; `zaumzeug doctor` may warn — not required for Phase 1 mock serve |
| **API keys** (`.env`) | For live models only | Not part of install; copy from `.env.example` after scaffold |

You do **not** manually install Haystack, DSPy, GEPA, or LiteLLM for the default path — the client install runs `pip install -e ".[dev]"` inside a project `.venv`.

---

## Effort and complexity

| Question | Answer |
|---|---|
| Is setup complicated? | **No** — one install script, one venv, one editable install; idempotent re-run |
| How long to first harness? | **Target < 15 minutes** on typical broadband (mock model, no API keys); **up to ~30 minutes** on slow networks |
| What does install do? | Creates `.venv`, editable `[dev]` install, scaffolds `usr-harnesses/example/`, `user-docs/`, `config/models.yaml`, `.env.example` / seeded `.env` (never overwrite), `.cursor/mcp.json.example`, and `.gitignore` entries; optional `--verify` runs `zaumzeug doctor` |

---

## Commands

| Platform | Command |
|---|---|
| **Windows** (PowerShell) | `.\install\client-install.ps1` |
| **Windows** (cmd) | `python install\client_install.py` |
| **macOS / Linux** | `./install/client-install.sh` |
| **Any OS** | `python install/client_install.py` |

The `.sh` / `.ps1` wrappers only locate Python 3.11+ and forward arguments to `install/client_install.py`. All install logic lives in the Python script.

### What install does

1. Creates project `.venv` (unless `--skip-venv`) and runs `pip install -e ".[dev]"`.
2. Scaffolds from `install/templates/` (**copy-if-missing**, idempotent on re-run):
   - `usr-harnesses/example/` — mock-first research harness (`default_model_id: mock`)
   - `config/models.yaml` — from `install/templates/config/models.example.yaml`
   - `.env.example` and a seeded `.env` **only when `.env` is missing** (never overwrite)
   - `.cursor/mcp.json.example`
   - `user-docs/` skeleton
   - `.gitignore` entries for `.venv`, `.env`, `deploy/`, `artifacts/`
3. Optional `--verify` runs `zaumzeug doctor`.

After a successful install you can run `zaumzeug serve example` with no API keys.

### Optional flags

Same flags on every platform (passed through wrappers unchanged):

| Flag | Effect |
|---|---|
| `--verify` | Run `zaumzeug doctor` after install |
| `--no-example` | Skip scaffolding the example harness |
| `--skip-venv` | Use the current Python (CI / pre-activated venv) |
| `--cursor-mcp` | Opt-in Cursor MCP config write (live `.cursor/mcp.json`) |

```powershell
.\install\client-install.ps1 --verify
```

```bash
./install/client-install.sh --verify
```

---

## First commands after install

Use the **mock model** first (no API keys). The example harness ships with `default_model_id: mock`.

```powershell
# Windows
.\.venv\Scripts\Activate.ps1
zaumzeug serve example              # mock model — no .env required
# optional live model: edit .env, set default_model_id on the agent, pip install provider package
```

```bash
# macOS / Linux
source .venv/bin/activate
zaumzeug serve example              # mock model — no .env required
# optional live model: edit .env, set default_model_id on the agent, pip install provider package
```

Phase 1 minimum path: install → `zaumzeug serve example` with **mock** → optional `.env` + provider package for live models.

---

## Disk space (planning estimates)

Sizes are **approximate ranges**, not guarantees. The first `pip install` usually dominates download time.

| Component | Approximate size |
|---|---|
| **Dev install** (`.venv`, editable `[dev]`: Haystack, Hayhooks, DSPy, GEPA, LiteLLM) | **~1–2.5 GB** |
| **+ `[eval]` / DeepEval** | **+200–500 MB** |
| **+ provider packages** (install only what you use) | **+50–200 MB** |
| **`uv`** (optional, separate from venv) | **~50–100 MB** |
| **Repo + harness folders** (excluding artifacts) | **< 50 MB** |
| **Compile artifacts** (`usr-harnesses/*/artifacts/`) | Variable over time |

**Production target install** (after copying `deploy/<name>/` to a server or desktop): runtime `zaumzeug` only — **no** DSPy, GEPA, or DeepEval — about **~500 MB–1.5 GB** for the venv. Python 3.11+ must already be on the target (Phase 2 `target_install`).

---

## Optional extras

Not required to start a harness with the mock profile.

| Feature | Extra install | When needed |
|---|---|---|
| **Compile / GEPA** | Included in `[dev]` | Offline prompt optimization + Haystack export (`zaumzeug compile`) — Phase 2 (E4-S02b/S03a); live task/reflection models need API keys in `.env`. See [Compile and export](../guides/compile.md). |
| **DeepEval** | `pip install "zaumzeug[eval]"` | Dev regression only (`zaumzeug eval`) — Phase 2+ |
| **Provider plugins** | e.g. `openai-haystack`, `anthropic-haystack` | Only for configured live providers |
| **MCP in Cursor** | `uv` + install `--cursor-mcp` | Phase 3 IDE integration |
| **Chainlit UI** | `hayhooks[chainlit]` | Phase 3 embedded `/chat` |

---

## Updating dependencies

There is **no `zaumzeug update-deps` command in v1**. Updates stay **pip-based** and reuse the same install path where possible.

**Design principle:** You do **not** pin Haystack, DSPy, GEPA, or LiteLLM versions individually on the default path — `zaumzeug` (`[dev]` extra) pulls the stack. Optional extras and provider plugins are installed separately.

| Situation | Steps |
|---|---|
| **After `git pull`** (SDK repo clone) | Re-run the same client install command (idempotent); then `zaumzeug doctor` or install with `--verify` |
| **Refresh SDK + `[dev]` stack manually** | Activate `.venv`, then `pip install -e ".[dev]"`, then `zaumzeug doctor` |
| **Update optional extras** | `pip install -U "zaumzeug[eval]"`, provider packages, or `hayhooks[chainlit]` as needed |
| **Production server** | Ship a new `deploy/<name>/` bundle → re-run bundled `target_install` (idempotent); do **not** `pip upgrade` ad hoc on the server |
| **PyPI consumer project** (deferred until package publish — [E1-S08](../../docs/stories/epic-stories/25-story.md)) | `pip install -U zaumzeug` then `zaumzeug install-project` (optionally pin `zaumzeug==x.y.z`) |

### After `git pull` (dev machine)

```powershell
# Windows
git pull
.\install\client-install.ps1 --verify
```

```bash
# macOS / Linux
git pull
./install/client-install.sh --verify
```

### Manual refresh in the venv

```bash
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
zaumzeug doctor
```

### Production note

Runtime deps on a target machine are updated by **redeploying** (`zaumzeug deploy` → copy bundle → `target_install`), not by upgrading packages in place. The bundle pins harness config and artifacts; pip lockfiles for deploy are **not** required in v1.

---

## Troubleshooting

| Symptom | What to try |
|---|---|
| `python` not found / wrong version | Confirm `python --version` is **3.11+**. On Windows prefer `py -3` / the PowerShell wrapper so Store stubs are skipped. |
| Wrapper fails to start | Run `python install/client_install.py` directly from the repo root. |
| `pip install -e ".[dev]"` fails or times out | Check disk free space (~1–2.5 GB for the venv), network, and proxy settings; re-run the install (idempotent). |
| `zaumzeug` not found after install | Activate `.venv` first (`Scripts\Activate.ps1` or `source .venv/bin/activate`). |
| Doctor reports missing Git | Optional — install Git if you need clone/pull workflows; not required for mock serve. |
| Doctor warns about `uv` / MCP | Ignore for Phase 1 mock serve; install `uv` only when using MCP tool servers. |
| Serve fails without API keys | Keep the example on `default_model_id: mock`, or add keys to `.env` and a live model entry before switching. |
| Existing `.env` unchanged after re-install | Expected — install never overwrites `.env`. Merge new keys from `.env.example` by hand. |
| Want a clean re-scaffold of docs/example | Delete the specific paths you want refreshed, then re-run install (copy-if-missing). |

Still stuck? Run `zaumzeug doctor` / `zaumzeug serve example --dry-run` and check [CLI reference](../reference/cli.md).

---

## Next steps

- Run the shipped example — [Your first harness](first-harness.md)
- Add another harness — [Project setup](project-setup.md) (`zaumzeug init <name>`)
- Testing with the mock profile — [Testing](../guides/testing.md)
- CLI reference — [cli.md](../reference/cli.md)
