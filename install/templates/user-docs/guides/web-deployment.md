# Web deployment layouts

| | |
|---|---|
| **Audience** | Client integrators · Ops |
| **Last updated** | 2026-08-21 |

OpenAI-compatible REST is the web surface: clients send Chat Completions to your harness, not to OpenAI. Chainlit is an **optional** embedded GUI on the same process and port. It is **not** a resolved “primary web UI” — Open WebUI, a custom SPA + proxy, and Next.js co-location remain valid layouts ([Architecture §9.4](../../docs/architecture/06-runtime-and-protocols.md#94-web-deployment-layouts); PRD open #2).

This page documents **Chainlit embedded** (E7-S04). The other layouts get full recipes in E7-S08.

---

## Chainlit embedded (`/chat`)

One process, one port: `zaumzeug serve` keeps OpenAI REST and mounts Hayhooks’ Chainlit UI at **`/chat`**.

```text
Browser  →  GET  http://127.0.0.1:1416/chat
Clients  →  POST http://127.0.0.1:1416/v1/chat/completions
            GET  http://127.0.0.1:1416/v1/models
```

### 1. Install the optional extra

Chainlit is **not** in the core `zaumzeug` / `hayhooks` install.

```bash
pip install "hayhooks[chainlit]"
```

If `serve.hayhooks.chainlit` is `true` and the extra is missing, `zaumzeug serve` exits with that install hint.

### 2. Enable it in `harness.yaml`

```yaml
serve:
  hayhooks:
    port: 1416
    chainlit: true
```

Default is `false`. Omit the key unless you want the GUI.

### 3. Serve and open `/chat`

```bash
zaumzeug serve example
```

Then open `http://127.0.0.1:1416/chat` (port from `serve.hayhooks.port`, or `--port`). Bind is **127.0.0.1** only in Phase 1.

REST stays on the same origin:

```bash
curl -s http://127.0.0.1:1416/v1/models
curl -s http://127.0.0.1:1416/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"example","messages":[{"role":"user","content":"hi"}]}'
```

The Chainlit app talks to those OpenAI endpoints. OpenAI `model` is the harness name; optional `model_id` selects a registry LLM. See [CLI — serve](../reference/cli.md#zaumzeug-serve).

### Production notes

- **Auth:** the embedded UI is public on the bind address. Put Traefik (or Nginx/Caddy) in front for production — same stance as REST.
- **Persistence / multi-user:** in-memory Chainlit sessions; for conversation history or a richer product UI, use Open WebUI or a custom frontend against `/v1` (E7-S08).
- **Workers:** keep a single uvicorn worker (Hayhooks default) unless the load balancer has sticky sessions.

Low-level Hayhooks equivalent (debug only; bypasses ZaumZeug config): `hayhooks run --with-chainlit`. Prefer `zaumzeug serve`.

---

## Other layouts (preview)

These share the same OpenAI `baseURL` (`http://127.0.0.1:1416/v1`, not `api.openai.com`). Full copy-paste recipes: E7-S08.

| Layout | Idea |
|---|---|
| **Open WebUI + Hayhooks** | Two containers; Open WebUI → `http://hayhooks:1416/v1` |
| **Custom SPA + proxy** | Nginx serves static UI; `/api/v1/*` → `127.0.0.1:1416` |
| **Next.js co-located** | App on `:3000` calls `localhost:1416` |

Also exposed for probes: `GET /v1/models`, `POST /<harness>/run`, optional `/docs` (Swagger).
