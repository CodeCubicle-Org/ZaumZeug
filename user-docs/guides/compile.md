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
| Manifest | `artifact-manifest.json` | Paths, `module_hash`, `source_hash`, run metadata |

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
zaumzeug compile <harness> [--agent NAME] [--dry-run]
```

Use `--dry-run` to validate Phase 2 compile config, resolve `compile.module` imports, and print task/reflection model ids **without** running GEPA or writing artifacts (mirrors `zaumzeug serve --dry-run`).

Each full run writes immutable `agents/<name>/artifacts/<run_id>/` and updates `artifacts/current`. The canonical manifest name is **`artifact-manifest.json`** (not the deploy bundle’s `manifest.json`). During migration, a legacy `manifest.json` inside an artifact folder is still accepted when resolving.

Live task/reflection models need API keys in `.env`. The shipped `example` harness uses `provider: mock` and a stub GEPA path for offline compile.

## Serve after compile

After a successful compile, point the agent at the exported artifact so serve ships what GEPA optimized:

```yaml
# agents/<name>/agent.yaml
agent:
  artifact: artifacts/current
  # system_prompt is ignored when a valid artifact-manifest.json is present
  system_prompt: prompts/system.md
```

Resolution priority (Architecture §5.2): **artifact** → hand-edited `system_prompt` → error.

```bash
zaumzeug compile example --agent researcher
# ensure agent.artifact: artifacts/current
zaumzeug doctor example   # warns if compile.module source changed since last compile
zaumzeug serve example
```

At serve/run time:

- `compile.module` is **not** imported (DSPy stays offline).
- The agent system prompt comes from `artifacts/.../prompts/system.md`.
- Optional `input_rewrite` from the manifest is applied as a fixed preprocess before the agent loop.
- `zaumzeug doctor` warns (exit 0) when the current `compile.module` `.py` hash no longer matches `source_hash` in the artifact manifest — re-run compile.

## Rollback to a pinned run

Compile never overwrites an existing `artifacts/<run_id>/` folder — only `artifacts/current` moves forward. To recover from a bad compile **without** re-running GEPA:

1. List runs under `agents/<name>/artifacts/` (each `<run_id>/` is immutable).
2. Pin serve to a known-good run in `agent.yaml` (do **not** hand-edit exported prompts — [Architecture §15](../../docs/architecture/10-operations-and-reference.md#15-anti-patterns)):

```yaml
# agents/<name>/agent.yaml
agent:
  artifact: artifacts/20260728T100001Z   # known-good run_id
```

3. Or retarget the pointer only: replace `artifacts/current` so it again points at that `<run_id>/` (symlink or copy), and keep `agent.artifact: artifacts/current`.
4. Run `zaumzeug doctor <harness>` — it validates the pin has a readable `artifact-manifest.json` and **warns** when the pin differs from `artifacts/current`.
5. `zaumzeug serve <harness>` loads the pinned run.

Deploy bundles pin the same way via `deploy/<name>/manifest.json` → `artifact_run_id` (per-agent map). Writing that field is `zaumzeug deploy` ([E5-S01](../../docs/stories/epic-stories/41-story.md)); `zaumzeug doctor --deploy` already validates the pinned run.

## Runtime input rewrite

When an artifact manifest lists `input_rewrite`, serve and `zaumzeug run` apply that **fixed** template to user messages before the agent loop (Jinja `{{ user_input }}`, `str.format`, or plain instruction text prepended). There is still no live GEPA call per message.

See also [CLI reference](../reference/cli.md#zaumzeug-compile).
