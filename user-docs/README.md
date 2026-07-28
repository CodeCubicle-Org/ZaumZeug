# ZaumZeug — User documentation

End-user guides for building and running multi-agent harnesses. For SDK design and epics, see the internal `docs/` folder in the repository.

| Section | Audience | Contents |
|---|---|---|
| [Getting started](getting-started/) | New developers | Install, project layout, [first harness](getting-started/first-harness.md) |
| [Guides](guides/) | Day-to-day use | Workflow, agents, pipelines, compile, deploy |
| [Reference](reference/) | Lookup | CLI commands (`reference/cli.md`), YAML fields *(expanded as features ship)* |

## Getting started

| Guide | Description |
|---|---|
| [Installation](getting-started/installation.md) | Prerequisites, install commands, disk, extras, updates, troubleshooting |
| [Project setup](getting-started/project-setup.md) | Layout and `zaumzeug init` for new harnesses |
| [Your first harness](getting-started/first-harness.md) | Run the shipped `example` research agent (mock, no API keys) |

## Guides

| Guide | Description |
|---|---|
| [Multi-agent workflow](guides/multi-agent-workflow.md) | `workflow.yaml`, agent vs pipeline stages, control flow inside agents |
| [Compile and export](guides/compile.md) | GEPA offline compile; Haystack artifact export; workflow diagram; optional runtime `input_rewrite`; pin/rollback to immutable `artifacts/<run_id>/` |
| [Testing](guides/testing.md) | Unit, integration, eval layers; mock profile; optional `[eval]` / DeepEval (E6-S01); CI tiers |

## Quick links

- **`zaumzeug init <name>`** — scaffold a new harness under `usr-harnesses/`
- **`zaumzeug serve <harness>`** — interactive chat with the workflow **entry** agent
- **`zaumzeug run <harness>`** — run serial workflow stages in order
- **`zaumzeug compile <harness>`** — run GEPA per agent (Phase 2, Pattern A); writes immutable `artifacts/<run_id>/` + `current` with Haystack export (`artifact-manifest.json`, prompts); regenerates `docs/workflow-diagram.md` (or use `--workflow-diagram-only`); use `--dry-run` to validate modules/registry without GEPA or LLM calls; pin/rollback to a prior run without re-GEPA — see [Compile and export — Rollback](guides/compile.md#rollback-to-a-pinned-run); optional `input_rewrite` is applied at serve/run time; Pattern B (`optimize_anything`) is available via `optimize_haystack_artifact` (E4-S04); live task/reflection models need API keys in `.env` (example uses mock/stub offline). See [Compile and export](guides/compile.md).
