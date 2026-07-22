# Installation

Get from a fresh clone to a working ZaumZeug dev environment with one command.

> This page covers OS install entry points and what install scaffolds. Prerequisites, disk estimates, optional extras, and troubleshooting will expand here as onboarding docs land.

## Commands

| Platform | Command |
|---|---|
| **Windows** (PowerShell) | `.\install\client-install.ps1` |
| **Windows** (cmd) | `python install\client_install.py` |
| **macOS / Linux** | `./install/client-install.sh` |
| **Any OS** | `python install/client_install.py` |

The `.sh` / `.ps1` wrappers only locate Python and forward arguments to `install/client_install.py`. All install logic lives in the Python script.

## What install does

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

## Optional flags

Same flags on every platform (passed through wrappers unchanged):

| Flag | Effect |
|---|---|
| `--verify` | Run `zaumzeug doctor` after install |
| `--no-example` | Skip scaffolding the example harness |
| `--skip-venv` | Use the current Python (CI / pre-activated venv) |
| `--cursor-mcp` | Opt-in Cursor MCP config write (live `.cursor/mcp.json`) |

Examples:

```powershell
.\install\client-install.ps1 --verify
```

```bash
./install/client-install.sh --verify
```

## Next steps

- Run the shipped example — [Your first harness](first-harness.md)
- Add another harness — [Project setup](project-setup.md) (`zaumzeug init <name>`)
- CLI reference — [cli.md](../reference/cli.md)
