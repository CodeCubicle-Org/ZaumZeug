# Runtime, CLI, and protocols

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 8. CLI and runtime layering

Command list and epic mapping: **[PRD §9](../prd.md#9-cli-surface-epic-mapping)**. Below: runtime behavior only.

### 8.1 Source roots

| Mode | Path | Flag / env |
|---|---|---|
| Development | `usr-harnesses/<name>/` | default |
| Production | `deploy/<name>/` | `--deploy` or `HARNESS_ROOT=deploy` |

### 8.2 `harness` vs raw `hayhooks`

**Canonical:** `zaumzeug serve|mcp|acp|run`. SDK loads config, builds agents from `agents/<name>/`, invokes **self-hosted Hayhooks** for serve paths.

| Command | Behavior |
|---|---|
| `zaumzeug serve <harness>` | Interactive: workflow `entry` agent via Hayhooks (`/v1/chat/completions`, optional MCP/ACP) |
| `zaumzeug run <harness>` | **Serial workflow:** executes `workflow.yaml` stages in order; stage-scoped `ModelRouter` per agent ([PRD E3.6](../prd.md#epic-e3--runtime-and-local-serve-phase-1)) |
| `zaumzeug run <harness> --from <stage>` | Partial run from a workflow stage (debug) |

Production targets bare metal, VM, or container — not Haystack Enterprise Platform ([PRD §12 resolved](../prd.md#12-open-decisions-blockers-for-some-stories)).

**Escape hatch:** `hayhooks run` / `hayhooks mcp run` for low-level Haystack debugging only.

### 8.3 Multi-harness serving

**Default:** one Hayhooks process per `zaumzeug serve <name>`. One process = one harness name = one port pair from that harness's `serve.hayhooks`.

Multi-tenant single process (many harness instances, one Hayhooks) is **explicitly out of scope v1** — [PRD NG1](../prd.md#4-non-goals-v1), [open #6](../prd.md#12-open-decisions-blockers-for-some-stories). Do not document multi-harness routing in Phase 1–3 implementations.

---


## 9. Client access and protocols

Product context: [PRD §5, §7](../prd.md#5-users-and-personas). Web UI choice: [open #2](../prd.md#12-open-decisions-blockers-for-some-stories).

> **ACP naming:** **Agent Client Protocol** (Zed/JetBrains) ≠ IBM Agent Communication Protocol (merged into **A2A**).

### 9.1 Protocol selection

| Protocol | Layer | Best for | Cursor | Web app | Zed / JetBrains |
|---|---|---|---|---|---|
| **MCP** | Host calls harness as tools | Capability plugin inside another agent | **Primary** | Rare | Internal tools |
| **ACP** | IDE drives harness as agent | Full agent UX in editor | Limited¹ | No | **Primary** |
| **OpenAI REST** | HTTP chat completions | Custom web, Chainlit, Open WebUI | No | **Primary** | No |
| **A2A** | Agent ↔ agent delegation | Multi-agent fleets | Future | Via gateway | Via gateway |
| **Direct REST** | `POST /{pipeline}/run` | Batch, webhooks | No | Yes | No |

¹ Cursor is primarily an ACP **server** for other editors — practical external harness path today is **MCP**.

| Client | Protocol | Command | Endpoint |
|---|---|---|---|
| Web app, Chainlit, Open WebUI | OpenAI-compatible REST | `zaumzeug serve` | `/v1/chat/completions` |
| Cursor, Claude Desktop | MCP | `zaumzeug mcp` | `{host}:{mcp_port}/mcp` |
| Zed, JetBrains, Neovim | ACP | `zaumzeug acp` | stdio JSON-RPC |
| Batch jobs | Direct REST | `zaumzeug serve` | `POST /{pipeline}/run` |
| Agent fleets (Phase 4) | A2A | `serve.a2a: true` | Agent Card |

**Insight:** MCP and ACP sit on different sides — ACP = editor drives your harness; MCP = your harness as tools **or** harness calls external tools.

### 9.2 MCP — when to use

Use when harness is a **capability** invoked by Cursor's (or another host's) agent. Limitations: no native IDE agent UX; host stays in control; not designed for agent-to-agent delegation.

### 9.3 ACP — when to use

Use when harness **is** the primary agent in Zed/JetBrains/Neovim. Harness may still use MCP internally for its own tools. Limitations: Cursor does not generically adopt third-party ACP agents; more implementation work than MCP expose.

### 9.4 Web deployment layouts

**OpenAI-compatible** means Hayhooks exposes `/v1/chat/completions` with OpenAI JSON shape — clients use `baseURL` pointing at your server (not OpenAI).

| Layout | How it works |
|---|---|
| **Chainlit embedded** | `chainlit: true` — UI at `/chat` on same port as API |
| **Open WebUI + Hayhooks** | Two containers; Open WebUI → `http://hayhooks:1416/v1` |
| **Custom SPA + proxy** | Nginx serves static UI; `/api/v1/*` → `127.0.0.1:1416` |
| **Next.js co-located** | App on `:3000` calls `localhost:1416` |

Also exposed: `GET /v1/models`, `POST /{pipeline}/run`, optional `/docs` (Swagger) for manual probes.

Clients use OpenAI-shaped requests against your `baseURL` (e.g. `http://127.0.0.1:1416/v1`) — not the OpenAI API. Any HTTP client or OpenAI SDK with custom `baseURL` works.

### 9.5 What does NOT call the harness directly

| Component | Runs where | Relationship |
|---|---|---|
| DSPy + GEPA | CI / offline | Export artifacts only; never request path |
| Cursor built-in agent | Cursor | Calls harness via **MCP tools** |
| LLM providers | External API | Called **by** ModelRouter inside harness |

```mermaid
flowchart TB
    cursor[Cursor] -->|MCP| mcp_srv[MCP_Server]
    zed[Zed] -->|ACP| acp_srv[ACP_Process]
    web[Web_App] -->|HTTP| rest[REST_API]
    mcp_srv --> core[Haystack_Agent]
    acp_srv --> core
    rest --> core
    core -->|MCP client| ext_tools[External_MCP_Tools]
```

---
