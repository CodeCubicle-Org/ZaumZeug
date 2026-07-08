# ZaumZeug — User documentation

End-user guides for building and running multi-agent harnesses. For SDK design and epics, see the internal `docs/` folder in the repository.

| Section | Audience | Contents |
|---|---|---|
| [Getting started](getting-started/) | New developers | Install, project layout, first harness *(skeleton — expanded at install)* |
| [Guides](guides/) | Day-to-day use | Workflow, agents, pipelines, compile, deploy |
| [Reference](reference/) | Lookup | CLI commands (`reference/cli.md`), YAML fields *(expanded as features ship)* |

## Guides

| Guide | Description |
|---|---|
| [Multi-agent workflow](guides/multi-agent-workflow.md) | `workflow.yaml`, agent vs pipeline stages, control flow inside agents |
| [Testing](guides/testing.md) | Unit, integration, eval layers; mock profile; CI tiers |

## Quick links

- **`zaumzeug serve <harness>`** — interactive chat with the workflow **entry** agent
- **`zaumzeug run <harness>`** — run serial workflow stages in order
- **`zaumzeug compile <harness>`** — optimize agents (Phase 2+) and regenerate `docs/workflow-diagram.md`
