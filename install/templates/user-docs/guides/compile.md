# Compile and export

Offline GEPA optimization writes Haystack-ready artifacts. DSPy and GEPA never run on the request path.

## Patterns

| Pattern | Optimizer | When to use |
|---|---|---|
| **A (default)** | `dspy.GEPA` | DSPy module → export → Haystack prompts/artifacts. This is what `zaumzeug compile` runs. |
| **B** | `optimize_anything` | Optimize Haystack-native text (system prompt, pipeline YAML, tool descriptions) **without** a DSPy module. Use `zaumzeug.compile.gepa_adapter.optimize_haystack_artifact`. |

### Pattern A — What GEPA optimizes

GEPA optimizes the **template** (predictor instructions / clarify-rewrite text), **not** end-user chat messages.

At serve time the runtime loads fixed exported files from `artifacts/<run_id>/` (or `artifacts/current`) and applies that text only. There is no live GEPA call per user message.

| Export | Path | Role |
|---|---|---|
| System prompt | `prompts/system.md` | Haystack `Agent` system prompt |
| Input rewrite *(optional)* | `prompts/input_rewrite.md` | Fixed preprocess template before the agent loop |
| Agent contract | `agent.json` | Tool descriptions + pipeline Jinja field templates |
| Manifest | `artifact-manifest.json` | Paths, module hash, run metadata |

Modules without a clarify/rewrite predictor omit `input_rewrite` — that is normal.

### Pattern B — `optimize_anything` (Haystack evaluator)

Seed a text artifact, run Haystack `Agent.run` / `Pipeline.run` as the evaluator (score + textual feedback / ASI), then evolve the artifact. Modes:

| `compile.mode` | Datasets | Intent |
|---|---|---|
| `single-task` | optional single example; **no** `valset` | Improve one artifact on one problem |
| `multi-task` | `trainset` required; **no** `valset` | Cross-task search |
| `generalization` | `trainset` **and** `valset` | Train/val split — preferred for production |

Example `agent.yaml` fragment:

```yaml
compile:
  optimizer: optimize_anything
  mode: generalization
  seed_artifact: prompts/system.md
  trainset: data/train.jsonl
  valset: data/val.jsonl
  auto: light
```

Programmatic entry point (CLI still Pattern A-only):

```python
from zaumzeug.compile import optimize_haystack_artifact

result = optimize_haystack_artifact(
    seed_candidate=open("prompts/system.md", encoding="utf-8").read(),
    run_agent=my_haystack_runner,  # (candidate, example) -> Agent.run / Pipeline.run result
    mode="generalization",
    dataset=train_rows,
    valset=val_rows,
)
```

## Run compile (Pattern A)

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
