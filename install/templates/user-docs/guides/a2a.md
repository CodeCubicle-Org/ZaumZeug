# A2A (Agent2Agent) — optional agent card

| | |
|---|---|
| **Audience** | Client integrators building agent fleets |
| **Last updated** | 2026-08-26 (E8-S04) |

Optional **Agent2Agent (A2A)** hosting so other agents can discover and delegate to your harness via an [Agent Card](https://a2a-protocol.org). This is a **separate protocol surface** from MCP and ACP.

## Not MCP, not ACP

| Protocol | Layer | Command / config | Best for |
|---|---|---|---|
| **MCP** | Host calls harness as **tools** | `zaumzeug mcp` | Cursor, Claude Desktop |
| **ACP** | IDE drives harness as **agent** (stdio) | `zaumzeug acp` | Zed, JetBrains |
| **A2A** | Agent ↔ agent **delegation** | `serve.a2a: true` + `zaumzeug a2a` | Multi-agent fleets |

- **MCP** — capability plugin inside another agent (agent→tool).
- **ACP** — Agent Client Protocol for editors (not IBM ACP; that work merged into A2A). See [ACP](acp.md).
- **A2A** — horizontal agent discovery and task handoff (agent→agent). Does **not** replace MCP or ACP.

Cursor uses **MCP**, not A2A. Web apps use OpenAI REST (`zaumzeug serve`), not A2A.

## Enable and install

In `harness.yaml`:

```yaml
serve:
  hayhooks:
    port: 1416
  a2a: true                    # shorthand — same as enabled: true
  # or:
  # a2a:
  #   enabled: true
  #   port: 1418               # default
```

Install the optional Hayhooks extra (not part of the default `zaumzeug` / `[dev]` install):

```bash
pip install "hayhooks[a2a]"
```

Then from the project root:

```bash
zaumzeug a2a example
```

Optional: `zaumzeug a2a example --deploy` or `HARNESS_ROOT=deploy` to load `deploy/<name>/` only. Override the port with `--port N`.

Missing `serve.a2a: true` fails with a clear hint. Missing `hayhooks[a2a]` fails with the install command above.

See [CLI — a2a](../reference/cli.md#zaumzeug-a2a).

## Agent card and endpoints

Default bind: **`127.0.0.1:1418`** (Phase 1 localhost only; same security posture as serve/MCP).

| Endpoint | Description |
|---|---|
| `GET /{harness}/.well-known/agent-card.json` | Agent Card for discovery |
| `POST /{harness}/` | A2A JSON-RPC (`SendMessage`, streaming, …) |
| `GET /status` | Server status + exposed agent list |

Example:

```bash
curl http://127.0.0.1:1418/example/.well-known/agent-card.json
```

Point fleet orchestrators or [a2a-inspector](https://github.com/a2aproject/a2a-inspector) at `http://127.0.0.1:1418/{harness}`.

## Agent fleet layout (one harness per process)

ZaumZeug keeps **one Hayhooks / A2A process per harness name** — the same rule as `zaumzeug serve` / `zaumzeug mcp`. Multi-tenant single process (many harnesses in one process) is **out of scope** ([PRD NG1](../../docs/prd.md#4-non-goals-v1)).

Typical fleet:

```text
orchestrator ──A2A──► zaumzeug a2a research   (:1418)
                  └──► zaumzeug a2a summarizer (:1419)   # separate process + port
```

Each process loads one harness folder (`usr-harnesses/<name>/` or `deploy/<name>/`). Do not document multi-harness routing inside one A2A server for v1.

## Related guides

- [Cursor MCP setup](cursor-mcp.md) — harness as tools
- [ACP (Zed / JetBrains)](acp.md) — IDE as ACP client
- [Web deployment](web-deployment.md) — OpenAI REST for browsers
- [Production auth](production-auth.md) — put Traefik (or Nginx/Caddy) in front of A2A in production
