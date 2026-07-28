# External tools and libraries

**Related:** [README](README.md) · [Architecture §4 — Technology stack](docs/architecture/03-technology-stack.md)

ZaumZeug integrates these projects. Versions are pinned by the `zaumzeug` package — users install provider integrations only as needed.

## Python version and local install

| | |
|---|---|
| **Declared** | `requires-python = ">=3.11"` in `pyproject.toml` |
| **Recommended for contributors** | **Python 3.11–3.13** (CPython wheels available for core deps) |
| **Last verified** | 2026-07-20 — Windows + Python 3.13.5 for E3-S00 factory tests |

### Known incompatibility (2026-07-20)

`pip install -e ".[dev]"` (or a full install of the declared core deps) can fail on **very new CPython** when a dependency must **build from source** instead of using a prebuilt wheel.

| Symptom | Cause |
|---|---|
| `metadata-generation-failed` on **`litellm`** | `litellm` (or a build dep such as `pydantic-core`) tries to compile native code |
| Message about **Rust / Cargo not installed or not on PATH** | Source build needs a working Rust toolchain; transient `puccinialin` installs may report `cargo` present then fail PATH checks |

**Observed on:** Python **3.14** (Windows). **Worked on:** Python **3.13.5** with prebuilt wheels for `pydantic` / `haystack-ai` / test stack.

**Phase 1 note:** SDK runtime code under `src/zaumzeug/` does **not** import `litellm` yet (LiteLLM is listed for GEPA / compile-time LM wiring in Phase 2). A full `pip install -e ".[dev]"` still resolves `litellm` because it is declared in core `dependencies`.

### Workaround for Phase 1 runtime / unit tests

If a full editable install fails on an unsupported Python, use a **3.11–3.13** venv, or install the packages Phase 1 tests actually need and the editable package without pulling `litellm`:

```powershell
# Prefer an interpreter that has wheels (example: 3.13 on Windows)
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install pydantic haystack-ai httpx pyyaml pytest pytest-asyncio respx
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" --no-deps
# Optional when you need the Hayhooks CLI surface:
.\.venv\Scripts\python.exe -m pip install hayhooks
```

Then run story tests as usual, e.g.:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_runtime_factory.py tests/unit/runtime/test_factory_imports.py -v
```

**Follow-ups (not done yet):** pin or relax `litellm` once Phase 2 needs it; consider moving it to a compile/dev extra so Phase 1 installs stay lean.

**CI Python version (E1-S07, 2026-07-22):** [`.github/workflows/ci-matrix.yml`](.github/workflows/ci-matrix.yml) pins **Python 3.11** on `windows-latest`, `ubuntu-latest`, and `macos-latest` (`actions/setup-python@v5` + pip cache). Local contrib may use 3.11–3.13; CI remains on 3.11 for the Phase 1 smoke matrix.

## Core runtime

| Project | Package | Role |
|---|---|---|
| [Haystack](https://github.com/deepset-ai/haystack) | `haystack-ai` | Agent loop, pipelines, RAG, tools |
| [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks) | `hayhooks` | REST/MCP serve, OpenAI-compatible API |
| [LiteLLM](https://github.com/BerriAI/litellm) | `litellm` | Unified model API for GEPA task/reflection LMs *(Phase 2+; see [Python version notes](#python-version-and-local-install))* |
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
| [DeepEval](https://github.com/confident-ai/deepeval) | `deepeval` via `pip install "zaumzeug[eval]"` | Dev regression, agentic/RAG metrics, tracing — **not** in core/`[dev]` (**Done** E6-S01, 2026-07-28); `zaumzeug.eval.require_deepeval()` install hint when missing; `zaumzeug eval` CLI (**Done** E6-S02, 2026-07-28) — builtin JSONL or DeepEval via `eval/runner.py` |

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
