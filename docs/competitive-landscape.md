# Competitive landscape

**Related:** [README](../README.md) · [PRD](prd.md) · [Architecture](architecture.md)

**Last updated:** 2026-07-05

ZaumZeug is not trying to be the most flexible agent orchestrator or the deepest provider SDK. It is a **factory for turning YAML-defined multi-agent workflows into compile-optimized, mock-testable, deployable production harnesses** — Haystack runtime, GEPA-guided improvement loops, and enforced dev/deploy boundaries.

The agent-harness space in 2026 splits into three buckets:

| Bucket | Examples | ZaumZeug relationship |
|---|---|---|
| **Product harnesses** | Claude Code, Codex, Cursor agent mode, [Hermes Agent](https://github.com/NousResearch/hermes-agent) | End-user agents with the loop baked in — not SDKs for building your own |
| **Framework harness SDKs** | LangGraph, OpenAI Agents SDK, CrewAI, Strands, Pydantic AI | ZaumZeug competes here as a factory + lifecycle SDK |
| **Declarative multi-agent config** | Strands Compose, AWS AgentCore harness, mcp-agent | Closest architectural peers — YAML-first multi-agent systems |

---

## What makes ZaumZeug different

### Factory, not framework soup

Most SDKs help you write **one agent system in code**. ZaumZeug scaffolds a harness folder, configures YAML, optionally adds Python, then **compile → deploy → serve**. The unit of shipping is `deploy/<name>/`, not your dev repo.

### Enforced compile-time vs runtime split

| Layer | ZaumZeug choice |
|---|---|
| Compile | DSPy + GEPA (offline prompt/module optimization) |
| Runtime | Haystack `Agent` (hot path only) |
| Forbidden | DSPy `ReAct` + Haystack `Agent` in the same request |

[DSPy/GEPA](https://dspy.ai/api/optimizers/GEPA/overview/) is widely used as an optimization toolchain, but teams usually wire production runtime themselves and often mix compile and serve paths. ZaumZeug treats that as an architectural violation — enforced in CLI, packaging, and golden rules.

### Dev workspace vs production bundle

`usr-harnesses/<name>/` (author, compile, experiment) → `zaumzeug deploy` → `deploy/<name>/` (runtime-only, generated). GEPA never runs on production servers. Most frameworks deploy your Python repo and leave packaging discipline to you.

### Multi-agent as workflow stages

A harness is **serial workflow stages** (parallel fan-out later), each running **one agent loop**, chained by `workflow.yaml`. This aligns with industry findings that subagents and context isolation often outperform monolithic agents ([LangChain multi-agent architecture guide](https://blog.langchain.com/choosing-the-right-multi-agent-architecture/)).

Haystack supports coordinator/specialist via agents-as-tools ([Haystack multi-agent docs](https://docs.haystack.deepset.ai/docs/multi-agent-systems)). ZaumZeug adds first-class workflow orchestration, per-agent model files, and deploy packaging on top.

### Guides + sensors, formalized

- **Guides** — DSPy/GEPA-optimized prompts and templates (feedforward)
- **Sensors** — GEPA metrics with textual feedback + optional DeepEval (feedback)

This mirrors emerging harness-engineering practice ([awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering)) but bakes it into the product model.

### One runtime, many client protocols

REST (OpenAI-compatible), MCP, and ACP from one Haystack/Hayhooks core — without rewriting orchestration per client.

### Mock-first, fail-fast developer experience

`zaumzeug doctor`, dry-run, mock model profile, optional DeepEval — zero-API-key local dev and CI by default.

---

## What ZaumZeug does better

| Area | ZaumZeug advantage |
|---|---|
| **Compile → ship loop** | DSPy/GEPA offline, Haystack online — enforced separation |
| **Production packaging** | Explicit `deploy/` bundle; no GEPA on servers |
| **Config-first multi-agent** | YAML workflow + per-agent `agents-models.yaml` |
| **Model agnosticism** | Per-agent model routing via config, not code |
| **Ops clarity** | Dev vs deploy is a product rule, not a convention |
| **Testing ergonomics** | Mock LM, doctor, optional eval tiers built in |
| **Cross-platform dev** | Windows, macOS, Linux install story (planned) |

---

## What others do better today

### LangGraph — complex orchestration

**Better at:** Stateful graphs, checkpointing, human-in-the-loop, branching/cycles, durable execution, time-travel debugging ([Haystack vs LangGraph](https://agentsindex.ai/compare/haystack-vs-langgraph)).

**ZaumZeug gap:** Phase 1 is serial workflows only; no checkpoint/resume story yet.

### OpenAI Agents SDK / Claude Agent SDK — provider-native depth

**Better at:** Minimal boilerplate, native tracing, guardrails, sandbox execution (Docker/E2B/Modal), voice/realtime, deep MCP integration ([2026 framework comparison](https://open-techstack.com/blog/langgraph-vs-openai-agents-sdk-vs-pydanticai-2026/)).

**ZaumZeug gap:** Sandbox/isolated execution deferred to Phase 4+. Less provider-native magic.

### CrewAI — fastest team-of-agents prototyping

**Better at:** Role-based crews, conversational collaboration, large community, rapid demos ([2026 framework landscape](https://www.morphllm.com/ai-agent-framework)).

**ZaumZeug gap:** Less persona/role ergonomics; more focused on workflow stages + deploy artifacts.

### Strands + Strands Compose + AgentCore — closest YAML competitor

**Better at:** Shipping YAML-first multi-agent ([Strands Compose](https://github.com/strands-compose/sdk-python)), rich orchestration modes (delegate, swarm, graph, nested), MCP lifecycle, AWS-hosted runtime with microVM isolation ([AgentCore harness](https://dev.to/aws/what-is-an-agent-harness-a-hands-on-guide-with-agentcore-harness-1h33)), config → code escape hatch.

**ZaumZeug gap:** Strands Compose has more orchestration topology today. AgentCore has managed hosting + sandbox. ZaumZeug wins on Haystack+RAG depth, DSPy/GEPA compile lane, and deploy bundle discipline.

### Raw Haystack — RAG and pipeline power

**Better at:** Document pipelines, hybrid retrieval, broad integrations ([Haystack vs LangGraph](https://rightaichoice.com/compare/haystack-vs-langgraph)).

**ZaumZeug gap:** ZaumZeug uses Haystack; it does not replace it. Pure RAG without compile/deploy factory is simpler with raw Haystack.

### Pydantic AI — type safety and test discipline

**Better at:** Typed structured outputs, `TestModel`/`FunctionModel`, Pydantic-native validation ([agents-lib comparison](https://agents-lib.com/compare/pydanticai-vs-openai-agents-sdk)).

**ZaumZeug gap:** Pydantic is used for config validation, not as the primary agent programming model.

### Hermes Agent — personal, self-improving agent product

[Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research is a **shipping personal agent** (“the agent that grows with you”) — not a factory for building domain harnesses. Both projects use “harness” language, but mean different things: Hermes is the loop infrastructure for **one adaptive assistant**; ZaumZeug is a **factory for many deployable multi-agent workflows**.

| Dimension | Hermes Agent | ZaumZeug |
|---|---|---|
| **Unit of work** | One Hermes instance per install | Many named harnesses in `usr-harnesses/` |
| **Multi-agent model** | Subagents for parallel delegation inside one session | Explicit `workflow.yaml` with named agent stages |
| **Configuration** | CLI config, skills, personalities, toolsets | YAML-first: `harness.yaml`, `workflow.yaml`, per-agent configs |
| **Runtime stack** | Custom Hermes loop (Python + gateway + TUI) | Haystack `Agent` + Hayhooks |
| **Optimization / learning** | Skills, memory, Honcho user modeling, trajectory compression | DSPy + GEPA offline compile → baked artifacts |
| **Deploy artifact** | Hermes install on VPS/cloud/serverless | Generated `deploy/<name>/` bundle |
| **Client surfaces** | TUI, Telegram, Discord, Slack, WhatsApp, Signal, MCP | REST (OpenAI-compatible), MCP, ACP |
| **Status** | Shipping (v0.18+, large community) | Phase 0→1 planning |

**Hermes does better:**

- **Personal assistant completeness** — full TUI, messaging gateway across six platforms, voice memo transcription, cross-platform conversation continuity
- **Runtime self-improvement** — agent-curated memory, autonomous skill creation, [agentskills.io](https://agentskills.io) skills, [Honcho](https://github.com/plastic-labs/honcho) user modeling, FTS5 session search
- **Operational agent features** — built-in cron with platform delivery, 40+ tools, six terminal backends (local, Docker, SSH, Singularity, Modal, Daytona), command approval and container isolation
- **Research orientation** — batch trajectory generation and compression for training tool-calling models
- **Ecosystem polish** — one-line install (Linux/macOS/Windows/Termux), `hermes doctor`, Nous Portal subscription, OpenClaw migration, Skills Hub

**ZaumZeug does better (or aims to):**

- **Multi-harness factory** — scaffold independent harness projects, not one monolithic assistant
- **GEPA compile lane** — offline prompt evolution from traces + textual feedback, exported into deploy artifacts (not just runtime skill learning)
- **Production bundle discipline** — `usr-harnesses/` vs `deploy/` with GEPA excluded from production servers
- **Integration-first serve** — REST/MCP/ACP endpoints for apps and IDEs, not a personal chat product
- **Haystack/RAG pipeline stages** — deterministic pipeline steps in workflows (Phase 4+)
- **Mock-first harness CI** — mock model profile, doctor, dry-run built for factory testing without API keys

**When to pick which:**

- **Hermes** — you want a personal AI with memory, skills, cron, and multi-platform chat; something working today with minimal setup
- **ZaumZeug** — you want to build domain-specific multi-agent workflows (research pipeline, review chain, RAG service) with offline optimization and a clear ops deploy path

They are not direct substitutes. Hermes as a dev assistant while building ZaumZeug harnesses for production services is a plausible combination.

**ZaumZeug gap:** Hermes wins on every practical personal-agent dimension today. ZaumZeug should not compete on memory, messaging, or skills — only on factory + compile + deploy fit for B2B multi-agent workflow products.

### Ecosystem maturity

LangGraph + LangSmith, OpenAI tracing, CrewAI community, AWS Strands docs, Hermes Agent — all have shipping code and battle stories. ZaumZeug is still Phase 0→1 planning. That is the largest practical gap today.

---

## Strategic implications

**Double down on (unique):**

- Compile/runtime golden rules
- `deploy/` as the unit of shipping
- GEPA feedback → recompile → redeploy loop
- Mock-first + doctor + per-agent model config
- Haystack RAG/pipeline stages in workflows (Phase 4+)

**Do not try to out-LangGraph LangGraph:**

- Checkpointing, graph visual debugger, complex branching — defer or integrate later

**Do not try to out-Hermes Hermes:**

- Personal memory, skills hub, messaging gateway, cron — out of scope; ZaumZeug targets harness developers and ops, not end-user personal agents

**Watch Strands Compose:**

- Nearest YAML multi-agent competitor; ZaumZeug wins on DSPy/GEPA compile lane + Haystack production stack until Phase 3+ orchestration modes ship

**Credibility gap to close:**

- Ship Phase 1 (`init`, `doctor`, `serve`, mock example) — until then, comparisons are architectural intent, not proven advantage

---

## References

- [Haystack multi-agent systems](https://docs.haystack.deepset.ai/docs/multi-agent-systems)
- [Haystack vs LangGraph](https://agentsindex.ai/compare/haystack-vs-langgraph)
- [LangGraph selection framework](https://tanujgarg.com/blog/langgraph-agent-framework-selection-cto-framework)
- [OpenAI vs PydanticAI (2026)](https://open-techstack.com/blog/langgraph-vs-openai-agents-sdk-vs-pydanticai-2026/)
- [8 agent SDKs compared (2026)](https://www.morphllm.com/ai-agent-framework)
- [The anatomy of an agent harness](https://dev.to/aniruddhaadak/the-anatomy-of-an-agent-harness-1n1j)
- [awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering)
- [DSPy GEPA overview](https://dspy.ai/api/optimizers/GEPA/overview/)
- [Strands Compose](https://github.com/strands-compose/sdk-python)
- [AgentCore harness guide](https://dev.to/aws/what-is-an-agent-harness-a-hands-on-guide-with-agentcore-harness-1h33)
- [Optimizing GEPA for production (Decagon)](https://decagon.ai/blog/optimizing-gepa-for-production)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) · [Hermes docs](https://hermes-agent.nousresearch.com/docs)
