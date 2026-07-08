<p align="center">
  <img src="imgs/zaumzeug-harness-sdk.jpg" alt="ZaumZeug — harness SDK for multi-agent AI workflows" width="100%">
</p>

# ZaumZeug

**A harness SDK and factory for configurable multi-agent AI workflows.**

ZaumZeug helps developers scaffold, configure, compile, and deploy **multi-agent harnesses** — not a single chatbot relabeled as an agent, but a **workflow** plus a **collection of named agents**, each with its own model and tool configuration. You edit YAML, add Python only where custom logic is needed, and ship a production-ready bundle to any host without touching Haystack, DSPy, or GEPA internals.

> **Status:** Phase 1 implementation in progress. Package skeleton, `harness.yaml` validation, three-tier `models.yaml` merge, runtime agent resolution (E2-S00–S03), and `zaumzeug doctor` including phase-aware warnings (E2-S04a–S04b) and deploy-bundle validation (E2-S04c) are done; next: serve dry-run and workflow schema (E2-S05–S07). Track progress in [docs/stories/](docs/stories/00-README.md).

**Formula:** `Harness = Workflow + Agents + Machinery`

---

## Why ZaumZeug?

ZaumZeug is not trying to be the most flexible agent orchestrator or the deepest provider SDK. It is a **factory for turning YAML-defined multi-agent workflows into compile-optimized, mock-testable, deployable production harnesses** — Haystack runtime, GEPA-guided improvement loops, and enforced dev/deploy boundaries.

Building on Haystack, DSPy, and GEPA today means wiring compile-time optimization and runtime serving yourself — and it's easy to mix them incorrectly. ZaumZeug provides a single SDK with enforced golden rules, a CLI workflow, and a clear boundary between development and production.

| Problem | ZaumZeug approach |
|---|---|
| Complex Haystack + DSPy + GEPA integration | One SDK with compile/runtime separation built in |
| Unclear dev vs production artifacts | `usr-harnesses/` for development, `deploy/` for shipping |
| Model provider lock-in | Per-agent `agents-models.yaml` + stage-scoped model routing |
| Different clients need different protocols | One Haystack core, multiple serve surfaces (REST, MCP, ACP) |

### How ZaumZeug is different

- **Factory, not one-off framework** — scaffold → configure → compile → deploy → serve; the unit of shipping is `deploy/<name>/`, not your dev repo
- **Compile ≠ runtime, enforced** — DSPy/GEPA offline; Haystack `Agent` on the hot path; never both loops in one request
- **Workflow stages, not one mega-agent** — serial stages (parallel later), each running one agent loop, chained by `workflow.yaml`
- **Guides + sensors** — GEPA-optimized prompts (guides) and metric feedback (sensors) baked into the lifecycle
- **Mock-first dev** — `zaumzeug doctor`, dry-run, and mock model profile for zero-API-key local dev and CI

### What we do better

| Area | ZaumZeug advantage |
|---|---|
| Compile → ship loop | DSPy/GEPA offline, Haystack online — enforced separation |
| Production packaging | Explicit `deploy/` bundle; GEPA never on production servers |
| Config-first multi-agent | YAML workflow + per-agent `agents-models.yaml` |
| Ops clarity | Dev vs deploy is a product rule, not a team convention |

### What others do better today

| Framework | Their strength | ZaumZeug gap (for now) |
|---|---|---|
| [LangGraph](https://langchain.com/langgraph) | Stateful graphs, checkpointing, human-in-the-loop, branching | Serial workflows only in Phase 1 |
| [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) / Claude Agent SDK | Provider-native tracing, guardrails, sandbox execution | Sandbox deferred; less provider magic |
| [CrewAI](https://www.crewai.com/) | Role-based crews, rapid prototyping, large community | Less persona ergonomics; more deploy discipline |
| [Strands Compose](https://github.com/strands-compose/sdk-python) / AgentCore | YAML multi-agent, swarm/graph modes, managed hosting | Fewer orchestration modes until Phase 3+ |
| [Raw Haystack](https://haystack.deepset.ai/) | RAG pipelines, retrieval integrations | ZaumZeug wraps Haystack — use raw Haystack for RAG-only |
| [Pydantic AI](https://ai.pydantic.dev/) | Typed structured outputs, test models | Pydantic for config, not agent programming model |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | Personal agent with memory, skills, messaging, cron | Factory for domain harnesses — not a personal assistant |

> **Honest caveat:** LangGraph, OpenAI SDK, CrewAI, Strands, and Hermes have shipping code and large ecosystems. ZaumZeug is early Phase 1 — comparisons above reflect architectural intent as the SDK lands story by story.

Full analysis: [Competitive landscape](docs/competitive-landscape.md)

---

## Core concepts

**Harness** — A named project containing a workflow definition, one or more agents, and the machinery to compile and serve them.

**Workflow** — A serial (or later, parallel) pipeline of stages. Each stage is either an **agent** (LLM-driven) or a **pipeline** (deterministic Haystack components).

**Agents** — Named, independently configured LLM agents. Each agent has its own `agents-models.yaml` for model selection and tool bindings.

**Compile vs runtime** — DSPy and GEPA run at compile time to optimize prompts and modules. Haystack runs at runtime to serve requests. ZaumZeug enforces this separation so production servers never run optimization workloads.

**Dev vs deploy** — You author and experiment in `usr-harnesses/<name>/`. `zaumzeug deploy` produces a self-contained `deploy/<name>/` bundle ready for any target host.

---

## Creating a harness

Rough steps to go from zero to a working harness:

1. **Install** — run `install/client_install.py` (or `pip install -e ".[dev]"` once the SDK ships).
2. **Scaffold** — `zaumzeug init <name>` creates `usr-harnesses/<name>/` with `harness.yaml`, `workflow.yaml`, and starter agents.
3. **Define the workflow** — edit `workflow.yaml`: set the `entry` agent and ordered `stages` (agent or pipeline steps).
4. **Configure agents** — under `agents/<name>/`, set prompts and tools in `agent.yaml` and pick models in `agents-models.yaml`.
5. **Add code only if needed** — custom tools, pipelines, or DSPy modules when YAML is not enough.
6. **Validate** — `zaumzeug doctor <name>` checks config, model refs, and environment before you run anything.

See [Multi-agent workflow](user-docs/guides/multi-agent-workflow.md) for file layout and YAML examples.

---

## Development workflow

Once scaffolded, you iterate in `usr-harnesses/<name>/`:

1. **Edit** — change workflow, agent prompts, tools, or models in YAML; touch Python only for custom logic.
2. **Validate** — `zaumzeug doctor <name>` after each meaningful change.
3. **Run locally** — `zaumzeug run <name>` executes all workflow stages in order; `zaumzeug serve <name>` opens interactive chat with the entry agent.
4. **Compile** *(Phase 2+)* — `zaumzeug compile <name>` runs DSPy/GEPA offline and writes optimized artifacts under each agent.
5. **Test** — `pytest` for SDK contributors; harness developers can add optional `eval/` tests with DeepEval. Default dev uses the **mock** model profile — no API keys required.
6. **Deploy** — `zaumzeug deploy <name>` packages `usr-harnesses/<name>/` into `deploy/<name>/` for production. Ops validates with `zaumzeug doctor <name> --deploy`, then runs `zaumzeug serve --deploy` on the target host.

Never edit `deploy/` by hand — it is regenerated on each deploy. See [Testing](user-docs/guides/testing.md) for mock vs live test tiers.

---

## Technology stack

| Layer | Library | Role |
|---|---|---|
| Runtime | [Haystack](https://github.com/deepset-ai/haystack) + Hayhooks | Agent loop, tools, RAG, REST/MCP serve |
| Specification | [DSPy](https://dspy.ai/) | Signatures and modules (compile-time only) |
| Optimization | [GEPA](https://github.com/gepa-ai/gepa) | Offline prompt and module optimization |
| Evaluation | [DeepEval](https://github.com/confident-ai/deepeval) *(optional)* | Dev regression and quality metrics |

Model routing is configuration-driven via `models.yaml` — swap providers without changing agent code. See [dependencies.md](dependencies.md) for the full list of external tools and libraries.

---

## CLI

**Implemented (Phase 1):**

```bash
zaumzeug doctor [harness]     # Preflight env + config (scan all harnesses if name omitted)
zaumzeug doctor --deploy      # Validate production bundle under deploy/ (or HARNESS_ROOT=deploy)
zaumzeug doctor --verbose     # Include passing checks
zaumzeug doctor --json        # Machine-readable report (exit 1 on fail; warns are non-blocking)
```

Doctor warns (non-blocking) when: `eval` is present in Phase 1, MCP tools are configured but `uv` is missing, or `workflow.yaml` is newer than `docs/workflow-diagram.md`. In `--deploy` mode, doctor validates `manifest.json`, pinned artifact runs, and reuses core config/runtime checks against the deploy bundle (dev-only warnings are skipped).

**Planned:**

```bash
zaumzeug init <harness>       # Scaffold a new harness
zaumzeug compile <harness>    # Run DSPy/GEPA optimization
zaumzeug run <harness>        # Execute workflow stages locally
zaumzeug serve <harness>      # Interactive chat with the entry agent
zaumzeug deploy <harness>     # Package usr-harnesses/ → deploy/
zaumzeug mcp <harness>        # Serve via Model Context Protocol
```

---

## Repository layout

```text
├── docs/                  # PRD, architecture, epic stories (planning)
├── user-docs/             # End-user guides (getting started, workflow, testing)
├── install/               # Client and target install scripts + templates
├── scripts/               # Doc maintenance utilities
├── src/zaumzeug/          # SDK source (`cli`, `config`, `doctor`, `runtime`, …)
├── usr-harnesses/         # Developer workspace for harness authoring
└── deploy/                # Production bundles (generated by zaumzeug deploy)
```

---

## Documentation

| Document | Description |
|---|---|
| [Product Requirements (PRD)](docs/prd.md) | Goals, personas, epics, acceptance criteria, phases |
| [Architecture](docs/architecture.md) | Technical design — stack, data flows, config, deploy |
| [Epic stories](docs/stories/00-README.md) | Implementation backlog broken into epics and stories |
| [User guides](user-docs/README.md) | How to build and run harnesses (expanded as features ship) |
| [Dependencies](dependencies.md) | External tools, libraries, and protocols |
| [Competitive landscape](docs/competitive-landscape.md) | How ZaumZeug compares to other harness SDKs |

---

## Who is this for?

- **Harness developers** — Scaffold a harness, configure models and tools, compile, deploy
- **SDK maintainers** — Extend the framework, examples, CI, and docs
- **Ops / platform** — Run `deploy/<name>/` on a server with `.env` and `zaumzeug serve --deploy`
- **Client integrators** — Call a harness via REST, MCP, or ACP from an app or IDE

---

## Contributing

Issues and discussions are welcome. See [docs/stories/](docs/stories/00-README.md) for the implementation roadmap and current progress.

---

## License

[GNU General Public License v3.0](LICENSE)
