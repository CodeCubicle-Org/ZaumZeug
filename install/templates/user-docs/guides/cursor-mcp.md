# Cursor MCP setup

| | |
|---|---|
| **Audience** | Client integrators · Cursor users |
| **Last updated** | 2026-08-21 |

Connect Cursor to a ZaumZeug harness over MCP. Cursor’s agent then invokes the harness as tools (Cursor stays in control — this is not ACP).

ZaumZeug serves Streamable HTTP at:

```text
http://localhost:{mcp_port}/mcp
```

`{mcp_port}` is `serve.hayhooks.mcp_port` in `harness.yaml` (default **1417**). Override at runtime with `zaumzeug mcp <harness> --port N`.

## Install the Cursor config

Install always scaffolds `.cursor/mcp.json.example` (copy-if-missing). Cursor reads the live file `.cursor/mcp.json`, not the example.

**Opt-in live file** — pass `--cursor-mcp` on client install:

```powershell
.\install\client-install.ps1 --cursor-mcp
```

```bash
./install/client-install.sh --cursor-mcp
```

The flag writes `.cursor/mcp.json` from the example template and does **not** overwrite an existing live file.

**Manual copy** — if you skipped the flag, copy `.cursor/mcp.json.example` to `.cursor/mcp.json`.

Default template (port **1417** is the `{mcp_port}` placeholder):

```json
{
  "mcpServers": {
    "zaumzeug": {
      "url": "http://localhost:1417/mcp"
    }
  }
}
```

Match the `url` port to `{mcp_port}`. Cursor also accepts a global MCP config in **Settings → MCP**; project `.cursor/mcp.json` is the ZaumZeug path.

## Start the harness MCP server

```bash
zaumzeug mcp example
```

Keep this process running. Cursor connects to `http://localhost:1417/mcp` (or your `mcp_port`). Health check: `GET http://127.0.0.1:1417/status`.

`zaumzeug mcp` binds **127.0.0.1** only. For a remote host, reverse-proxy to `{mcp_port}/mcp` and put the public HTTPS URL in `mcp.json`.

See [CLI — mcp](../reference/cli.md#zaumzeug-mcp).

## `uv` for MCP tool servers

`uv` is **not** required for Cursor to call `zaumzeug mcp` (HTTP).

Install [`uv`](https://docs.astral.sh/uv/) when the **harness** declares stdio MCP servers in `tools.mcp` (`command: uv`). HTTP `url` entries in `tools.mcp` do not need `uv`. `zaumzeug doctor` warns (non-blocking) when stdio MCP is configured and `uv` is missing from PATH.

```yaml
tools:
  mcp:
    - name: filesystem
      command: uv
      args: ["run", "mcp-server-filesystem", "/workspace"]
```

## End-to-end checklist

Walk this once after install (mock model is enough):

1. [ ] Client install has written `.cursor/mcp.json.example`.
2. [ ] Live `.cursor/mcp.json` exists (install `--cursor-mcp`, or copy the example).
3. [ ] `url` is `http://localhost:{mcp_port}/mcp` (default `http://localhost:1417/mcp`).
4. [ ] `zaumzeug mcp <harness>` is running; `GET /status` returns ok.
5. [ ] Cursor **Settings → MCP** shows the `zaumzeug` server (reload the window if needed).
6. [ ] If any agent uses stdio `tools.mcp`, `uv` is on PATH (`zaumzeug doctor` has no `mcp_uv` warning). HTTP-only MCP does not need `uv`.
7. [ ] Ask Cursor to use the harness tool and confirm a response.

## Related

- [CLI — mcp](../reference/cli.md#zaumzeug-mcp)
- [Installation](../getting-started/installation.md) — `--cursor-mcp` flag
- [Cursor MCP docs](https://cursor.com/docs/mcp)
