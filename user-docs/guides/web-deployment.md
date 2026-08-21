# Web deployment layouts

| | |
|---|---|
| **Audience** | Client integrators · Ops |
| **Last updated** | 2026-08-21 |

OpenAI-compatible REST is the web surface: clients send Chat Completions to **your harness**, not to OpenAI. Set the client `baseURL` (or Open WebUI `OPENAI_API_BASE_URL`) to the Hayhooks host — for example `http://127.0.0.1:1416/v1` — **never** `https://api.openai.com/v1`.

None of these layouts is a product default ([PRD open #2](../../docs/prd.md#12-open-decisions-blockers-for-some-stories)). Pick the one that matches the client you already have. Spec: [Architecture §9.4](../../docs/architecture/06-runtime-and-protocols.md#94-web-deployment-layouts).

| Layout | When to use | Client `baseURL` |
|---|---|---|
| [Chainlit embedded](#chainlit-embedded-chat) | Fastest GUI; same process and port as REST | same origin (`/v1`) |
| [Open WebUI + Hayhooks](#open-webui--hayhooks-two-containers) | Multi-user chat product; two containers | `http://hayhooks:1416/v1` |
| [Custom SPA + Nginx](#custom-spa--nginx-proxy) | Branded static UI behind a reverse proxy | `/api/v1` (same origin) |
| [Next.js co-located](#nextjs-co-located) | App already on `:3000` on the same host | `http://127.0.0.1:1416/v1` (server-side) |

---

## Shared OpenAI contract

`zaumzeug serve` wraps Hayhooks. OpenAI SDKs and HTTP clients talk to the harness with a **custom** `baseURL`:

```text
http://127.0.0.1:1416/v1          ← harness (correct)
https://api.openai.com/v1        ← OpenAI API (wrong for this product)
```

| Field / env | Value |
|---|---|
| OpenAI `baseURL` / `base_url` | `{harness-host}:{port}/v1` — default `http://127.0.0.1:1416/v1` |
| OpenAI `apiKey` | Hayhooks does not require one; send a dummy (`not-needed` / `sk-not-used`) if the client library insists |
| OpenAI `model` | Harness / pipeline name (for the shipped example: `example`) |
| Optional `model_id` | Registry key from the entry agent's `agents-models.yaml` |

Port comes from `serve.hayhooks.port` (default **1416**) or `zaumzeug serve --port`. Serve binds **127.0.0.1** only until a future explicit wide-open bind ([Architecture §14](../../docs/architecture/10-operations-and-reference.md#14-security-phase-1-stance)). Production: `zaumzeug serve <name> --deploy` or `HARNESS_ROOT=deploy` — same REST surface ([Deploy and ship](deploy.md)).

Python (official SDK):

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:1416/v1",  # harness, not api.openai.com
    api_key="not-needed",
)
response = client.chat.completions.create(
    model="example",
    messages=[{"role": "user", "content": "hi"}],
)
```

### Probe endpoints

Use these from the host (or through the proxy in the SPA / Next.js recipes):

| Endpoint | Purpose |
|---|---|
| `GET /v1/models` | Lists the served harness pipeline — confirm the OpenAI `model` id before wiring a UI |
| `POST /v1/chat/completions` | Chat Completions (OpenAI JSON shape) |
| `GET /docs` | FastAPI Swagger UI for manual REST probes |
| `POST /<harness>/run` | Direct Hayhooks run API (batch / webhooks; not required for chat UIs) |

```bash
zaumzeug serve example
curl -s http://127.0.0.1:1416/v1/models
curl -s http://127.0.0.1:1416/docs | head
curl -s http://127.0.0.1:1416/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"example","messages":[{"role":"user","content":"hi"}]}'
```

See [CLI — serve](../reference/cli.md#zaumzeug-serve).

---

## Chainlit embedded (`/chat`)

One process, one port: `zaumzeug serve` keeps OpenAI REST and mounts Hayhooks’ Chainlit UI at **`/chat`**.

```text
Browser  →  GET  http://127.0.0.1:1416/chat
Clients  →  POST http://127.0.0.1:1416/v1/chat/completions
            GET  http://127.0.0.1:1416/v1/models
            GET  http://127.0.0.1:1416/docs
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
curl -s http://127.0.0.1:1416/docs | head
curl -s http://127.0.0.1:1416/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"example","messages":[{"role":"user","content":"hi"}]}'
```

The Chainlit app talks to those OpenAI endpoints. OpenAI `model` is the harness name; optional `model_id` selects a registry LLM.

### Production notes

- **Auth:** the embedded UI is public on the bind address. Put Traefik (or Nginx/Caddy) in front for production — same stance as REST (Phase 4 [E8-S02](../../docs/stories/epic-stories/59-story.md)).
- **Persistence / multi-user:** in-memory Chainlit sessions; for conversation history or a richer product UI, use [Open WebUI](#open-webui--hayhooks-two-containers) or a custom frontend against `/v1`.
- **Workers:** keep a single uvicorn worker (Hayhooks default) unless the load balancer has sticky sessions.

Low-level Hayhooks equivalent (debug only; bypasses ZaumZeug config): `hayhooks run --with-chainlit`. Prefer `zaumzeug serve`.

---

## Open WebUI + Hayhooks (two containers)

Two containers on one Docker network. Open WebUI is the browser UI; Hayhooks (`zaumzeug serve`) is the OpenAI-compatible backend. Open WebUI must call **`http://hayhooks:1416/v1`**, not `https://api.openai.com/v1`.

```text
Browser → Open WebUI :3000
               │  OPENAI_API_BASE_URL=http://hayhooks:1416/v1
               ▼
         Hayhooks :1416
               GET  /v1/models
               POST /v1/chat/completions
               GET  /docs
```

Ollama is **not** required. Disable it and point Open WebUI at the harness.

### Compose (canonical two-container)

Service name `hayhooks` is the DNS name Open WebUI uses. A generated bundle Dockerfile is Phase 4 ([E8-S05](../../docs/stories/epic-stories/62-story.md)); until then, build (or `CMD`) an image that installs runtime `zaumzeug` and runs `zaumzeug serve <name> --deploy`.

```yaml
services:
  hayhooks:
    image: your-registry/zaumzeug-harness:latest
    hostname: hayhooks
    environment:
      HARNESS_ROOT: deploy
    # Publish for host probes (GET /v1/models, GET /docs).
    ports:
      - "1416:1416"

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    environment:
      OPENAI_API_BASE_URL: http://hayhooks:1416/v1
      OPENAI_API_KEY: sk-not-used
      ENABLE_OLLAMA_API: "false"
    volumes:
      - open-webui:/app/backend/data
    depends_on:
      - hayhooks

volumes:
  open-webui:
```

| Env (Open WebUI) | Value | Why |
|---|---|---|
| `OPENAI_API_BASE_URL` | `http://hayhooks:1416/v1` | Harness OpenAI root — **not** `https://api.openai.com/v1` |
| `OPENAI_API_KEY` | `sk-not-used` | Client library requires a key; Hayhooks ignores it in v1 |
| `ENABLE_OLLAMA_API` | `false` | Avoid a second, unused model source |

After start: open `http://localhost:3000`, pick the model id from `GET /v1/models` (harness name). Host probes:

```bash
curl -s http://127.0.0.1:1416/v1/models
curl -s http://127.0.0.1:1416/docs | head
```

### Reachability (localhost bind)

`zaumzeug serve` currently binds **127.0.0.1** only. On a Docker **bridge** network, Open WebUI cannot reach `hayhooks:1416` until the process listens on `0.0.0.0` (future explicit bind / [E8-S05](../../docs/stories/epic-stories/62-story.md)). Until then, use one of:

1. **Linux host network** — `network_mode: host` on both services, then set `OPENAI_API_BASE_URL=http://127.0.0.1:1416/v1` (the compose DNS name `hayhooks` is not used).
2. **Open WebUI in Docker, serve on the host** (works today):

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      OPENAI_API_BASE_URL: http://host.docker.internal:1416/v1
      OPENAI_API_KEY: sk-not-used
      ENABLE_OLLAMA_API: "false"
```

On the host: `zaumzeug serve example` (or `--deploy`). Probe `http://127.0.0.1:1416/v1/models` and `http://127.0.0.1:1416/docs` locally, then open Open WebUI on `:3000`.

You can also add the connection in the UI: **Admin Settings → Connections → OpenAI → Add** — API URL `http://hayhooks:1416/v1` (or `http://host.docker.internal:1416/v1`), API key `sk-not-used`.

Open WebUI docs: [environment configuration](https://docs.openwebui.com/reference/env-configuration) (`OPENAI_API_BASE_URL`).

---

## Custom SPA + Nginx proxy

Nginx serves the static UI and reverse-proxies `/api/v1/*` to Hayhooks on `127.0.0.1:1416`. The browser stays same-origin (`baseURL: "/api/v1"`), so it never calls `api.openai.com` and you avoid CORS against the Hayhooks port.

```text
Browser → Nginx :80
            │  static files
            │  /api/v1/*  →  127.0.0.1:1416/v1/*
            ▼
         zaumzeug serve (127.0.0.1:1416)
```

### Nginx

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri /index.html;
    }

    # Browser /api/v1/chat/completions → Hayhooks /v1/chat/completions
    location /api/v1/ {
        proxy_pass http://127.0.0.1:1416/v1/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Connection "";
        proxy_buffering off;          # streaming / SSE
        proxy_read_timeout 3600s;
    }

    # Optional: Swagger + models list through the same origin
    location = /api/docs {
        proxy_pass http://127.0.0.1:1416/docs;
        proxy_set_header Host $host;
    }
}
```

Start the harness on the same host, then Nginx:

```bash
zaumzeug serve example
# nginx -c /path/to/nginx.conf
```

### SPA client

```javascript
const baseURL = "/api/v1"; // same origin — not https://api.openai.com/v1

const models = await fetch(`${baseURL}/models`).then((r) => r.json());
const completion = await fetch(`${baseURL}/chat/completions`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "example",
    messages: [{ role: "user", content: "hi" }],
  }),
}).then((r) => r.json());
```

OpenAI JS SDK against the proxy (dummy key; do not point `baseURL` at OpenAI):

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "/api/v1",
  apiKey: "not-needed",
  dangerouslyAllowBrowser: true, // only because Nginx is same-origin
});
```

Probes (host, or via Nginx):

```bash
curl -s http://127.0.0.1:1416/v1/models
curl -s http://127.0.0.1:1416/docs | head
curl -s http://127.0.0.1/api/v1/models
```

Put TLS and auth on Nginx (or Traefik) in production — Hayhooks stays unauthenticated behind the proxy.

---

## Next.js co-located

A Next.js app on **`:3000`** calls Hayhooks on **`localhost:1416`** from **server** code. Keep the harness URL in a server-only env var — do **not** set `NEXT_PUBLIC_*` to `https://api.openai.com/v1`, and do not expose the harness URL to the browser unless you intend to.

```text
Browser → Next.js :3000  (Route Handler / Server Component)
               │  OPENAI_BASE_URL=http://127.0.0.1:1416/v1
               ▼
         zaumzeug serve (127.0.0.1:1416)
```

### Env

`.env.local` (not committed):

```bash
OPENAI_BASE_URL=http://127.0.0.1:1416/v1
OPENAI_API_KEY=not-needed
HARNESS_MODEL=example
```

`OPENAI_BASE_URL` is the harness, **not** `https://api.openai.com/v1`.

### Server Route Handler

```ts
// app/api/chat/route.ts
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: process.env.OPENAI_BASE_URL ?? "http://127.0.0.1:1416/v1",
  apiKey: process.env.OPENAI_API_KEY ?? "not-needed",
});

export async function POST(request: Request) {
  const { messages } = await request.json();
  const completion = await client.chat.completions.create({
    model: process.env.HARNESS_MODEL ?? "example",
    messages,
  });
  return Response.json(completion);
}
```

`fetch` without the SDK:

```ts
const base = process.env.OPENAI_BASE_URL ?? "http://127.0.0.1:1416/v1";
await fetch(`${base}/chat/completions`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: process.env.HARNESS_MODEL ?? "example",
    messages: [{ role: "user", content: "hi" }],
  }),
});
```

### Run both processes

```bash
zaumzeug serve example          # :1416
npm run dev                     # Next.js :3000
```

Probes stay on the harness port (or add a Route Handler that proxies `GET /v1/models`):

```bash
curl -s http://127.0.0.1:1416/v1/models
curl -s http://127.0.0.1:1416/docs | head
```

Production: same host or sidecar; `zaumzeug serve --deploy` / `HARNESS_ROOT=deploy`. Put Traefik in front of Next.js (and optionally Hayhooks) for TLS/auth — [E8-S02](../../docs/stories/epic-stories/59-story.md).

---

## Related

- [CLI — serve](../reference/cli.md#zaumzeug-serve) — OpenAI REST, `GET /v1/models`, optional `/chat`, `/docs`
- [CLI — mcp](../reference/cli.md#zaumzeug-mcp) — Cursor / Claude Desktop
- [ACP (Zed / JetBrains)](acp.md) — `zaumzeug acp` stdio JSON-RPC; not IBM ACP/A2A; Cursor uses MCP
- [Deploy and ship](deploy.md) — production `--deploy` / `HARNESS_ROOT=deploy`
- [Architecture §9.4](../../docs/architecture/06-runtime-and-protocols.md#94-web-deployment-layouts)
