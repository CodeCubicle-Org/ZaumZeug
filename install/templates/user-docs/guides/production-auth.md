# Production auth (Traefik proxy-only)

| | |
|---|---|
| **Audience** | Ops / platform |
| **Last updated** | 2026-08-21 |

Hayhooks (`zaumzeug serve` / `zaumzeug mcp`) has **no built-in auth in v1**. There is no `serve.auth` key. Production protection lives at the **edge**: terminate TLS and check credentials **before** traffic reaches the harness process.

**Reference pattern: Traefik.** Nginx and Caddy are documented below as the same proxy-only idea.

```text
Internet  →  Traefik :443  (TLS + auth middleware)
                 │
                 ▼
         127.0.0.1:1416   zaumzeug serve   REST /v1  ·  /chat  ·  /docs
         127.0.0.1:1417   zaumzeug mcp     /mcp
```

Keep serve/mcp bound to **localhost** (or a Docker internal network). Do not publish 1416/1417 on the public internet.

Credentials live in **Traefik host env** (systemd `EnvironmentFile`, Docker secret, or a ForwardAuth sidecar). Never put API keys, bearer tokens, or htpasswd hashes in `harness.yaml`, Traefik snippets inside `deploy/<name>/`, or git.

Each deploy bundle ships optional snippets under `traefik/` (static + dynamic YAML). Copy them to the Traefik host and fill host-local values there.

---

## Path routing

Same OpenAI REST, MCP, and Chainlit surfaces as local serve. Traefik matches **path prefixes** and forwards to the matching local port.

| Public path | Backend | Process | Notes |
|---|---|---|---|
| `POST /v1/chat/completions` | `http://127.0.0.1:1416/v1/chat/completions` | `zaumzeug serve` | OpenAI Chat Completions |
| `GET /v1/models` | `http://127.0.0.1:1416/v1/models` | `zaumzeug serve` | Model id = harness name |
| `GET /docs` | `http://127.0.0.1:1416/docs` | `zaumzeug serve` | FastAPI Swagger (protect it too) |
| `GET /chat` | `http://127.0.0.1:1416/chat` | `zaumzeug serve` | Chainlit — only if `serve.hayhooks.chainlit: true` |
| `POST /mcp` | `http://127.0.0.1:1417/mcp` | `zaumzeug mcp` | Streamable HTTP MCP |
| `GET /status` | `http://127.0.0.1:1417/status` | `zaumzeug mcp` | MCP health |

Ports come from `serve.hayhooks.port` (default **1416**) and `serve.hayhooks.mcp_port` (default **1417**). Replace `harness.example.com` with your public hostname.

Clients still set OpenAI `baseURL` at **your** origin (`https://harness.example.com/v1`), not `https://api.openai.com/v1`. See [Web deployment](web-deployment.md).

---

## Traefik static config (TLS)

File provider + HTTP→HTTPS redirect + Let's Encrypt. Run this **on the Traefik host**, not inside the harness YAML.

```yaml
# /etc/traefik/traefik.yml  (static — Traefik v3)
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true
  websecure:
    address: ":443"

providers:
  file:
    directory: /etc/traefik/dynamic
    watch: true

certificatesResolvers:
  le:
    acme:
      # Set the contact email on the Traefik host — not in the deploy bundle.
      email: ops@example.com
      storage: /var/lib/traefik/acme.json
      httpChallenge:
        entryPoint: web

api:
  dashboard: false
```

`ops@example.com` is a placeholder. Replace it on the host. ACME storage (`acme.json`) stays on the Traefik host and is never packaged by `zaumzeug deploy`.

The same static file ships as `deploy/<name>/traefik/traefik.yml`.

---

## Traefik dynamic config (routers + auth)

Two services (REST/Chainlit vs MCP), one public host, Headers middleware for HSTS, ForwardAuth for bearer/API-key or OAuth.

```yaml
# /etc/traefik/dynamic/harness.yml  (dynamic — Traefik v3)
http:
  middlewares:
    harness-secure-headers:
      headers:
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        stsPreload: true
        forceSTSHeader: true
        frameDeny: true
        contentTypeNosniff: true
        browserXssFilter: true
        referrerPolicy: "strict-origin-when-cross-origin"
        customRequestHeaders:
          X-Forwarded-Proto: "https"
        # Do not put Authorization or API keys in this block.
        # Hayhooks does not read them, and deploy YAML must stay secret-free.

    harness-forwardauth:
      forwardAuth:
        # Sidecar / oauth2-proxy on the Traefik host. It reads HARNESS_API_KEY
        # (or OIDC client secret) from host env — never from this file.
        address: "http://127.0.0.1:4181"
        trustForwardHeader: true
        authRequestHeaders:
          - "Authorization"
          - "X-Api-Key"

  routers:
    harness-rest:
      # HeadersRegexp requires a Bearer prefix; ForwardAuth checks the value.
      rule: >-
        Host(`harness.example.com`) && PathPrefix(`/v1`)
        && HeadersRegexp(`Authorization`, `^Bearer .+`)
      entryPoints:
        - websecure
      middlewares:
        - harness-secure-headers
        - harness-forwardauth
      service: hayhooks-rest
      tls:
        certResolver: le

    harness-docs:
      rule: "Host(`harness.example.com`) && PathPrefix(`/docs`)"
      entryPoints:
        - websecure
      middlewares:
        - harness-secure-headers
        - harness-forwardauth
      service: hayhooks-rest
      tls:
        certResolver: le

    harness-chat:
      rule: "Host(`harness.example.com`) && PathPrefix(`/chat`)"
      entryPoints:
        - websecure
      middlewares:
        - harness-secure-headers
        - harness-forwardauth
      service: hayhooks-rest
      tls:
        certResolver: le

    harness-mcp:
      rule: "Host(`harness.example.com`) && PathPrefix(`/mcp`)"
      entryPoints:
        - websecure
      middlewares:
        - harness-secure-headers
        - harness-forwardauth
      service: hayhooks-mcp
      tls:
        certResolver: le

  services:
    hayhooks-rest:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:1416"
    hayhooks-mcp:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:1417"
```

The same dynamic file ships as `deploy/<name>/traefik/dynamic.yml`.

### Headers middleware vs ForwardAuth

| Piece | What it does here |
|---|---|
| **Headers middleware** | HSTS / clickjacking / sniffing headers, plus `X-Forwarded-Proto`. OSS Traefik does **not** compare `Authorization` values in this middleware — do not paste bearer tokens into `customRequestHeaders`. |
| **Router `HeadersRegexp`** | Rejects requests that lack `Authorization: Bearer …` (shape only). |
| **ForwardAuth** | Delegates the real check to a host-local service ([Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)). 2xx → proxy to Hayhooks; 4xx → client never reaches 1416/1417. |

Point ForwardAuth at [oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy/) (OIDC / Google / GitHub) or a tiny checker that compares `Authorization: Bearer …` to `HARNESS_API_KEY` from the **host** environment. Example checker (ops-owned, not part of ZaumZeug):

```python
# Run on the Traefik host only. Reads HARNESS_API_KEY from env.
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

EXPECTED = os.environ["HARNESS_API_KEY"]  # set in systemd/Docker — not in yaml


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        auth = self.headers.get("Authorization", "")
        ok = auth == f"Bearer {EXPECTED}"
        self.send_response(200 if ok else 401)
        self.end_headers()

    do_POST = do_GET


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 4181), Handler).serve_forever()
```

Start harness processes **behind** Traefik:

```bash
zaumzeug serve <name> --deploy    # 127.0.0.1:1416
zaumzeug mcp <name> --deploy      # 127.0.0.1:1417
```

Or `HARNESS_ROOT=deploy` in systemd / compose. See [Deploy and ship](deploy.md).

---

## Nginx / Caddy (same principle)

Optional alternatives. Same rules: TLS + auth at the proxy, Hayhooks unauthenticated on localhost, secrets only in proxy/host env.

### Nginx

```nginx
# auth_request calls a host-local verifier (same role as Traefik ForwardAuth).
# Put the verifier's credentials in the host env, not in this file.

location = /_auth {
    internal;
    proxy_pass http://127.0.0.1:4181;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header Authorization $http_authorization;
}

location /v1/ {
    auth_request /_auth;
    proxy_pass http://127.0.0.1:1416/v1/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Authorization $http_authorization;
    proxy_buffering off;
}

location /chat/ {
    auth_request /_auth;
    proxy_pass http://127.0.0.1:1416/chat/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

location /mcp {
    auth_request /_auth;
    proxy_pass http://127.0.0.1:1417/mcp;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Authorization $http_authorization;
}
```

Terminate TLS on the same `server { listen 443 ssl; … }` block. `ssl_certificate` / `ssl_certificate_key` paths stay on the Nginx host.

### Caddy

```caddyfile
harness.example.com {
    # Certificates and ForwardAuth secrets stay on the Caddy host.
    reverse_proxy /v1/* 127.0.0.1:1416
    reverse_proxy /chat* 127.0.0.1:1416
    reverse_proxy /docs* 127.0.0.1:1416
    reverse_proxy /mcp* 127.0.0.1:1417

    forward_auth 127.0.0.1:4181 {
        uri /
        copy_headers Authorization
    }
}
```

---

## What not to do

| Don't | Why |
|---|---|
| Add `serve.auth` to `harness.yaml` | Not a v1 schema field; auth is proxy-only |
| Publish `0.0.0.0:1416` without a proxy | Serve enforces localhost bind; do not work around it |
| Put bearer tokens in Traefik/Nginx YAML in git or `deploy/` | AC: credentials only on the target host env |
| Rely on Hayhooks to reject anonymous clients | It will not — that is the proxy's job |

---

## Related

- Bundle ops sheet: `deploy/<name>/README.deploy.md` (links here; ships `traefik/` snippets)
- [Deploy and ship](deploy.md) — copy → `target_install` → `.env` → `serve --deploy`
- [Web deployment](web-deployment.md) — Chainlit / Open WebUI / SPA / Next.js behind this proxy
- [CLI — serve](../reference/cli.md#zaumzeug-serve) · [CLI — mcp](../reference/cli.md#zaumzeug-mcp)
- [Architecture §14 — Security](../../docs/architecture/10-operations-and-reference.md#14-security-phase-1-stance)
- [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/) · [Traefik Headers](https://doc.traefik.io/traefik/middlewares/http/headers/)
