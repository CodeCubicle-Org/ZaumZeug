# ACP (Agent Client Protocol) — Zed and JetBrains

| | |
|---|---|
| **Audience** | Client integrators · Zed / JetBrains users |
| **Last updated** | 2026-08-21 |

Connect Zed or JetBrains to a ZaumZeug harness so the **IDE drives the harness as the primary agent** over stdio JSON-RPC.

This is the **Agent Client Protocol** used by Zed and JetBrains ([agentclientprotocol.com](https://agentclientprotocol.com/)). It is **not** IBM Agent Communication Protocol (that work merged into **A2A**, which ZaumZeug does not implement in v1).

## Cursor limitation

**Cursor is not a generic ACP client for third-party agents.** Cursor is primarily an ACP *server* for other editors. To use a ZaumZeug harness from Cursor, use **MCP** instead: `zaumzeug mcp` and [Cursor MCP setup](cursor-mcp.md).

| Client | Protocol | Command |
|---|---|---|
| **Zed, JetBrains, Neovim** | **ACP** (harness *is* the agent) | `zaumzeug acp <harness>` |
| **Cursor, Claude Desktop** | **MCP** (host stays in control) | `zaumzeug mcp <harness>` |

ACP and MCP sit on different sides: ACP = the editor drives your harness; MCP = your harness as tools **or** the harness calling external MCP servers. A harness started with `zaumzeug acp` may still use `tools.mcp` internally for its own tools.

## Start the adapter

From the project root:

```bash
zaumzeug acp example
```

The process speaks **newline-delimited JSON-RPC 2.0 on stdin/stdout**. Status lines go to **stderr** so they do not break the protocol. Keep this process as the command the IDE launches — do not wrap it in a shell that prints to stdout.

Optional: `zaumzeug acp example --deploy` or `HARNESS_ROOT=deploy` to load `deploy/<name>/` only.

See [CLI — acp](../reference/cli.md#zaumzeug-acp).

## Zed — register a custom agent

Open **Agent Settings** (`agent: open settings`) → **External Agents** → **Add Agent** → **Add Custom Agent**. Zed opens `settings.json`. Add an `agent_servers` entry:

```json
{
  "agent_servers": {
    "zaumzeug": {
      "type": "custom",
      "command": "zaumzeug",
      "args": ["acp", "example"],
      "env": {}
    }
  }
}
```

Use the full path to `zaumzeug` (or `python -m zaumzeug.cli`) if the CLI is not on `PATH`. Set `args` to `["acp", "<harness>"]`. Zed detects settings changes without a restart. Select **zaumzeug** from the new-thread menu in the Agent Panel.

Official Zed docs: [External Agents](https://zed.dev/docs/ai/external-agents).

## JetBrains — register a custom agent

In AI Chat, open the overflow menu and choose **Add Custom Agent**, or go to **Settings → Tools → AI Assistant → Agents**. That creates `~/.jetbrains/acp.json`. Add:

```json
{
  "agent_servers": {
    "ZaumZeug": {
      "command": "zaumzeug",
      "args": ["acp", "example"],
      "env": {}
    }
  }
}
```

Prefer the **full path** to the `zaumzeug` executable. After save, the agent appears in AI Chat. Official JetBrains docs: [Agent Client Protocol (ACP)](https://www.jetbrains.com/help/ai-assistant/acp.html).

## Internal MCP tools

ACP does not replace `tools.mcp` on `agent.yaml`. When the harness declares MCP servers, the factory still builds Haystack `MCPToolset`s (deferred connect). Stdio MCP servers still need `uv` on PATH — `zaumzeug doctor` warns if it is missing.

```yaml
tools:
  mcp:
    - name: filesystem
      command: uv
      args: ["run", "mcp-server-filesystem", "/workspace"]
```

## Related

- [CLI — acp](../reference/cli.md#zaumzeug-acp)
- [Cursor MCP setup](cursor-mcp.md) — Cursor path (MCP, not ACP)
- [Agent Client Protocol](https://agentclientprotocol.com/)
