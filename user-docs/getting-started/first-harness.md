# Your first harness

| | |
|---|---|
| **Audience** | New developers |
| **Last updated** | 2026-07-20 |

This walkthrough uses the shipped **`example`** harness — a config-only general research agent with one workflow stage and the mock model profile. You can chat locally without API keys.

For how `workflow.yaml`, agent stages, and pipelines fit together, see [Multi-agent workflow](../guides/multi-agent-workflow.md).

---

## What you get

```text
usr-harnesses/example/
├── harness.yaml                 # name, serve port, optional models.yaml
├── models.yaml                  # optional harness-wide aliases
├── workflow.yaml                # entry + one stage: researcher
└── agents/
    └── researcher/
        ├── agent.yaml           # system prompt + builtin web_fetch
        ├── agents-models.yaml   # default_model_id: mock
        └── prompts/
            └── system.md
```

| Piece | Role |
|---|---|
| **`agents/researcher/`** | Single research role (prompts, tools, models) |
| **`workflow.yaml`** | One serial stage; `entry: researcher` for `zaumzeug serve` |
| **`default_model_id: mock`** | CI and first-run without `.env` or live keys |
| **`web_fetch`** | Builtin tool for fetching page content |

There is **no RAG** in this example (deferred to a later phase).

---

## Run it

From the project root (after install / editable SDK setup):

```bash
zaumzeug doctor example
zaumzeug serve example
```

Then open an OpenAI-compatible client against `http://127.0.0.1:1416` (port from `serve.hayhooks.port`). The chat model id is the harness name: `example`.

`zaumzeug serve example` works **without** a `.env` file while the entry agent stays on the mock profile.

---

## Switch to a live model (optional)

1. Add provider keys to `.env` (never commit secrets).
2. In `agents/researcher/agents-models.yaml`, set `default_model_id` to a live registry entry (or uncomment a local `openai_compatible` profile).
3. Re-run `zaumzeug doctor example`, then `zaumzeug serve example`.

Global defaults can live in `config/models.yaml`; harness and agent files deep-merge on top.

---

## Next steps

- Add stages or agents — see [Multi-agent workflow](../guides/multi-agent-workflow.md).
- Testing and the mock profile — see [Testing](../guides/testing.md).
- CLI flags — see [CLI reference](../reference/cli.md).
