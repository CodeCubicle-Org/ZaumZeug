# Compile and export

Offline GEPA optimization writes Haystack-ready artifacts. DSPy and GEPA never run on the request path.

## What GEPA optimizes

GEPA optimizes the **template** (predictor instructions / clarify-rewrite text), **not** end-user chat messages.

At serve time the runtime loads fixed exported files from `artifacts/<run_id>/` (or `artifacts/current`) and applies that text only. There is no live GEPA call per user message.

| Export | Path | Role |
|---|---|---|
| System prompt | `prompts/system.md` | Haystack `Agent` system prompt |
| Input rewrite *(optional)* | `prompts/input_rewrite.md` | Fixed preprocess template before the agent loop |
| Agent contract | `agent.json` | Tool descriptions + pipeline Jinja field templates |
| Manifest | `artifact-manifest.json` | Paths, module hash, run metadata |

Modules without a clarify/rewrite predictor omit `input_rewrite` — that is normal.

## Run compile

```bash
zaumzeug compile <harness> [--agent NAME]
```

Each run writes immutable `agents/<name>/artifacts/<run_id>/` and updates `artifacts/current`. The canonical manifest name is **`artifact-manifest.json`** (not the deploy bundle’s `manifest.json`). During migration, a legacy `manifest.json` inside an artifact folder is still accepted when resolving.

Live task/reflection models need API keys in `.env`. The shipped `example` harness uses `provider: mock` and a stub GEPA path for offline compile.

## Runtime input rewrite

When an artifact manifest lists `input_rewrite`, serve and `zaumzeug run` apply that **fixed** template to user messages before the agent loop (Jinja `{{ user_input }}`, `str.format`, or plain instruction text prepended). There is still no live GEPA call per message.

## Next

- Point `agent.artifact` at `artifacts/current` for serve — E4-S05
- [CLI reference](../reference/cli.md#zaumzeug-compile)
