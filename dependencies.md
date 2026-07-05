# External tools and libraries

**Related:** [README](README.md) · [Architecture §4 — Technology stack](docs/architecture/03-technology-stack.md)

ZaumZeug integrates these projects. Versions are pinned by the `zaumzeug` package — users install provider integrations only as needed.

## Core runtime

| Project | Package | Role |
|---|---|---|
| [Haystack](https://github.com/deepset-ai/haystack) | `haystack-ai` | Agent loop, pipelines, RAG, tools |
| [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks) | `hayhooks` | REST/MCP serve, OpenAI-compatible API |
| [LiteLLM](https://github.com/BerriAI/litellm) | `litellm` | Unified model API for GEPA task/reflection LMs |
| [Pydantic](https://docs.pydantic.dev/latest/) | `pydantic` | Config validation and schemas |
| [PyYAML](https://pyyaml.org/) | `pyyaml` | Harness and model YAML loading |

## Compile-time (dev extra)

| Project | Package | Role |
|---|---|---|
| [DSPy](https://dspy.ai/) | `dspy-ai` | Signatures, modules, ReAct — compile/eval only |
| [GEPA](https://github.com/gepa-ai/gepa) | `gepa` | Offline prompt and module optimization |

## Optional evaluation

| Project | Package | Role |
|---|---|---|
| [DeepEval](https://github.com/confident-ai/deepeval) | `deepeval` | Dev regression, agentic/RAG metrics, tracing |

## LLM provider integrations (install per `models.yaml`)

| Project | Package |
|---|---|
| [OpenAI Haystack](https://github.com/deepset-ai/haystack/tree/main/integrations/openai) | `openai-haystack` |
| [Anthropic Haystack](https://github.com/deepset-ai/haystack/tree/main/integrations/anthropic) | `anthropic-haystack` |
| [OpenRouter Haystack](https://github.com/deepset-ai/haystack/tree/main/integrations/openrouter) | `openrouter-haystack` |

## Protocols and client surfaces

| Standard / tool | Role |
|---|---|
| [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat) | REST contract for `/v1/chat/completions` |
| [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) | IDE and tool integration (`zaumzeug mcp`) |
| [Agent Client Protocol (ACP)](https://agentclientprotocol.com/) | Zed and compatible editor clients |

## Development and testing

| Project | Package | Role |
|---|---|---|
| [pytest](https://docs.pytest.org/) | `pytest` | Test runner and fixtures |
| [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) | `pytest-asyncio` | Async serve and workflow tests |
| [HTTPX](https://www.python-httpx.org/) | `httpx` | HTTP client for integration tests |
| [respx](https://lundberg.github.io/respx/) | `respx` | Mock outbound HTTP in tests |
| [debugpy](https://github.com/microsoft/debugpy) | `debugpy` | IDE attach for local `zaumzeug serve` |
| [syrupy](https://github.com/syrupy-project/syrupy) *(optional)* | `syrupy` | Golden snapshots for compile artifacts |
| [pytest-recording](https://github.com/kiwicom/pytest-recording) *(optional)* | `pytest-recording` | VCR cassettes for provider HTTP |

## Deployment and operations (Phase 3+)

| Project | Role |
|---|---|
| [Docker](https://docs.docker.com/) | Optional containerized production deploy |
| [Traefik](https://doc.traefik.io/traefik/) | Reference reverse proxy — TLS and auth at the edge |
| [Chainlit](https://chainlit.io/) *(via `hayhooks[chainlit]`)* | Embedded chat UI for harnesses |
| [Open WebUI](https://github.com/open-webui/open-webui) | Optional two-container pattern with Hayhooks |

## Adjacent ecosystem (not bundled)

These are documented reference options for sandboxing, gateways, tracing, and durable workflows — not core SDK dependencies:

E2B · Docker Sandboxes · Daytona · Temporal · OpenTelemetry · [OpenRouter](https://openrouter.ai/) · AWS MCP Gateway · Kong · Cloudflare · ContextForge · Promptfoo · Ragas

Full dependency groups and version policy: [Architecture §4](docs/architecture/03-technology-stack.md).
