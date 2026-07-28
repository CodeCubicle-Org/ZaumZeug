# Your first harness

| | |
|---|---|
| **Audience** | New developers |
| **Last updated** | 2026-07-28 |

This walkthrough uses the shipped **`example`** harness — a general research agent with one workflow stage and the mock model profile. You can chat locally without API keys. Phase 2 also ships a compile seed (`compile.module` + train/val data) so `zaumzeug compile example` works offline via stub GEPA.

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
        ├── agent.yaml           # system prompt + builtin web_fetch + compile
        ├── agents-models.yaml   # default_model_id: mock
        ├── prompts/
        │   └── system.md
        ├── modules/
        │   └── researcher.py    # DSPy Module for zaumzeug compile
        └── data/
            ├── train.jsonl
            └── val.jsonl
```

| Piece | Role |
|---|---|
| **`agents/researcher/`** | Single research role (prompts, tools, models, compile) |
| **`workflow.yaml`** | One serial stage; `entry: researcher` for `zaumzeug serve` |
| **`default_model_id: mock`** | CI and first-run without `.env` or live keys |
| **`web_fetch`** | Builtin tool for fetching page content |
| **`compile:`** | Phase 2 GEPA seed — mock uses stub optimizer offline |

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

Optional Phase 2 compile (offline with mock → stub GEPA; live models need API keys):

```bash
zaumzeug compile example --dry-run --agent researcher   # validate module + models, no GEPA
zaumzeug compile example --agent researcher
```

Writes `agents/researcher/artifacts/<run_id>/` (including `artifact-manifest.json`, `prompts/system.md`, `agent.json`) and updates `artifacts/current`. To serve the compiled prompts, set `agent.artifact: artifacts/current` in `agent.yaml` (hand-edited `system_prompt` is then ignored). To recover from a bad compile without re-running GEPA, pin `agent.artifact` to a prior immutable `artifacts/<run_id>/` — see [Compile and export — Rollback](../guides/compile.md#rollback-to-a-pinned-run). GEPA optimizes the **template**, not end-user chat; optional `input_rewrite` is applied at serve/run — see [Compile and export](../guides/compile.md).

---

## Switch to a live model (optional)

1. Add provider keys to `.env` (never commit secrets).
2. In `agents/researcher/agents-models.yaml`, set `default_model_id` to a live registry entry (or uncomment a local `openai_compatible` profile).
3. Re-run `zaumzeug doctor example`, then `zaumzeug serve example`.

Global defaults can live in `config/models.yaml`; harness and agent files deep-merge on top.

---

## Next steps

- Scaffold another harness — see [Project setup](project-setup.md) (`zaumzeug init <name>`).
- Add stages or agents — see [Multi-agent workflow](../guides/multi-agent-workflow.md).
- Testing and the mock profile — see [Testing](../guides/testing.md).
- CLI flags — see [CLI reference](../reference/cli.md) (`compile`, `serve`, `run`, …).
