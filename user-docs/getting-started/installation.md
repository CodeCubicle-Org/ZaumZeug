# Installation

Get from a fresh clone to a working ZaumZeug dev environment with one command.

> This page covers OS install entry points. Prerequisites, disk estimates, optional extras, and troubleshooting will expand here as onboarding docs land.

## Commands

| Platform | Command |
|---|---|
| **Windows** (PowerShell) | `.\install\client-install.ps1` |
| **Windows** (cmd) | `python install\client_install.py` |
| **macOS / Linux** | `./install/client-install.sh` |
| **Any OS** | `python install/client_install.py` |

The `.sh` / `.ps1` wrappers only locate Python and forward arguments to `install/client_install.py`. All install logic lives in the Python script.

## Optional flags

Same flags on every platform (passed through wrappers unchanged):

| Flag | Effect |
|---|---|
| `--verify` | Run `zaumzeug doctor` after install |
| `--no-example` | Skip scaffolding the example harness |
| `--skip-venv` | Use the current Python (CI / pre-activated venv) |
| `--cursor-mcp` | Opt-in Cursor MCP config write |

Examples:

```powershell
.\install\client-install.ps1 --verify
```

```bash
./install/client-install.sh --verify
```
