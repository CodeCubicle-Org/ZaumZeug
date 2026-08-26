# Cursor MCP setup

| | |
|---|---|
| **Audience** | Client integrators · Cursor users |
| **Last updated** | 2026-08-21 (E8-S02 production auth reverse-proxy) |

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
# production bundle (same MCP surface; no usr-harnesses/):
zaumzeug mcp example --deploy
# HARNESS_ROOT=deploy zaumzeug mcp example
```

Keep this process running. Cursor connects to `http://localhost:1417/mcp` (or your `mcp_port`). Health check: `GET http://127.0.0.1:1417/status`.

`zaumzeug mcp` binds **127.0.0.1** only. For a remote host, reverse-proxy `{mcp_port}/mcp` with Traefik (or Nginx/Caddy) and put the public HTTPS URL in `mcp.json` — same **proxy-only** auth as REST ([Production auth](production-auth.md)). `--deploy` / `HARNESS_ROOT=deploy` load **only** `deploy/<name>/` (valid `manifest.json` required) — see [Deploy and ship](deploy.md).

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
4. [ ] `zaumzeug mcp <harness>` is running (`--deploy` when serving a production bundle); `GET /status` returns ok.
5. [ ] Cursor **Settings → MCP** shows the `zaumzeug` server (reload the window if needed).
6. [ ] If any agent uses stdio `tools.mcp`, `uv` is on PATH (`zaumzeug doctor` has no `mcp_uv` warning). HTTP-only MCP does not need `uv`.
7. [ ] Ask Cursor to use the harness tool and confirm a response.

## Related

- [CLI — mcp](../reference/cli.md#zaumzeug-mcp)
- [Deploy and ship](deploy.md) — `zaumzeug mcp <name> --deploy` / `HARNESS_ROOT=deploy`
- [Production auth](production-auth.md) — Traefik proxy-only TLS + ForwardAuth in front of `{mcp_port}/mcp`
- [Installation](../getting-started/installation.md) — `--cursor-mcp` flag
- [ACP (Zed / JetBrains)](acp.md) — Agent Client Protocol for IDEs that drive the harness (Cursor uses MCP, not ACP)
- [A2A (agent fleets)](a2a.md) — optional agent-to-agent card hosting (≠ MCP)
- [Web deployment](web-deployment.md) — Chainlit / Open WebUI / SPA / Next.js against OpenAI REST
- [Cursor MCP docs](https://cursor.com/docs/mcp)
