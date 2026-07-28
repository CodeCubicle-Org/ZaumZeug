# Testing harnesses and the SDK

| | |
|---|---|
| **Audience** | Harness developers · SDK contributors |
| **Last updated** | 2026-07-28 |

ZaumZeug separates **fast deterministic tests** (config, serve wiring, REST shape) from **optional quality evals** (LLM output regression). Default CI uses the **`mock`** model profile — no API keys required.

DeepEval is an **optional** package via `pip install "zaumzeug[eval]"` (**Done** E6-S01) — not part of the core or `[dev]` install. Importing `zaumzeug.eval` never requires DeepEval; calling DeepEval APIs without the extra raises an install hint. The `zaumzeug eval` CLI is available (**Done** E6-S02): builtin JSONL checks need no extra; `eval.framework: deepeval` (the default when `framework` is omitted) requires the `[eval]` extra. Optional harness `eval/` pytest files (`zaumzeug init --with-eval` or the example harness) run with `deepeval test run` (**Done** E6-S04). Captured Haystack turns export to `data/traces/` and score with `zaumzeug eval --trace` (**Done** E6-S05). Mode C black-boxes a running serve with `zaumzeug eval --base-url` (**Done** E6-S06) — staging/debug only.

For SDK design detail, see internal `docs/architecture/10-operations-and-reference.md` §13 and `docs/architecture/03-technology-stack.md` §4.5.

---

## Three layers at a glance

| Layer | You test | Typical tool | Runs in default CI? |
|---|---|---|---|
| **Unit** | Config merge, validation, export mapping | `pytest` | Yes |
| **Integration** | `zaumzeug serve`, `zaumzeug run`, REST contract | `pytest` + `httpx` + **mock** profile | Yes |
| **Eval** | Output quality on golden cases | `deepeval` / `zaumzeug eval` | Optional (`[eval]` extra) |
| **Live e2e** | Real provider smoke | `pytest` + `.env` keys | No — nightly / manual only |

**Principle:** Mock the **LLM and external HTTP** at boundaries. Test ZaumZeug logic (routing, yaml resolution, artifact loading) without paying for tokens or flaking on model creativity.

---

## Quick commands

```bash
# Preflight — no server, no LLM
zaumzeug doctor example
zaumzeug serve example --dry-run
zaumzeug compile example --dry-run

# SDK test suite (repo root; contributors)
pytest tests/unit tests/integration tests/usr-harnesses -v

# Optional harness regression (after pip install "zaumzeug[eval]")
deepeval test run usr-harnesses/example/eval/
# or
zaumzeug eval example
zaumzeug eval example --framework builtin --trace data/traces/run-001.jsonl
zaumzeug eval example --framework builtin --base-url   # Mode C vs running serve

# Live provider smoke (maintainers; costs money)
HARNESS_LIVE_LLM=1 pytest tests/e2e -v
```

Use serve `--dry-run` to check harness/workflow/runtime paths without starting Hayhooks. Use compile `--dry-run` to check Phase 2 module imports and task/reflection models without running GEPA.
---

## Mock model (default)

The **`mock`** provider in `agents-models.yaml` returns canned text from `tests/fixtures/responses/` (or the bundled copy under `src/zaumzeug/fixtures/responses/` when installed via pip). CI and local quick-start use this exclusively — no API keys.

```yaml
# agents/<name>/agents-models.yaml (example harness — Architecture §6.6)
default_model_id: mock

models:
  mock:
    provider: mock
    model: harness-fixture   # loads tests/fixtures/responses/harness-fixture.txt
```

Global defaults ship in `install/templates/config/models.example.yaml` (copied to `config/models.yaml` on scaffold).

`zaumzeug serve example` works without `.env`. Integration tests assert JSON **shape** and routing — not semantic answer quality.

Unit tests: `pytest tests/unit/runtime/test_model_router.py -v -k e3_s05`.

### Local LLM (LM Studio, optional)

For development with a local OpenAI-compatible server, use **`openai_compatible`** in `agents-models.yaml` (not in the shipped CI default):

```yaml
default_model_id: local

models:
  local:
    provider: openai_compatible
    model: your-loaded-model-id
    api_base_url: http://localhost:1234/v1
```

Set a placeholder in `.env` if needed: `OPENAI_API_KEY=lm-studio`. Install the provider package when using live routing: `pip install openai-haystack`.

Unit tests: `pytest tests/unit/runtime/test_model_router.py -v -k e3_s01`.

---

## Where tests live

### SDK contributors (repository `tests/`)

```text
tests/
├── unit/              # schemas, merge, snapshots
├── integration/       # serve on localhost, OpenAI REST contract
├── usr-harnesses/     # fixture + example harness trees
├── e2e/               # live LLM — gated by HARNESS_LIVE_LLM=1
└── fixtures/
    ├── responses/     # mock LLM canned replies
    └── cassettes/     # optional VCR recordings (Phase 2+)
```

### Harness developers (`usr-harnesses/<name>/eval/`)

```text
usr-harnesses/my-harness/
└── eval/
    ├── test_researcher.py   # DeepEval pytest cases
    └── metrics.py           # custom metrics (optional)
```

Install eval support once per dev machine:

```bash
pip install -e ".[dev,eval]"
```

Eval is **optional** — not required to deploy or serve in production.

---

## Writing SDK unit tests

Focus on **contracts and errors**, not LLM prose.

| Target | Example assertion |
|---|---|
| Config schema | Invalid yaml → field-level Pydantic error with path |
| Model merge | Harness `models.yaml` + agent `agents-models.yaml` → expected `default_model_id` |
| ModelRouter | `provider: mock` → fixtures; `openai_compatible` + `api_base_url` → local LM Studio (E3-S01) |
| Resolution | `artifact` present → serve path loads artifact, ignores `system_prompt` |
| Export (Phase 2+) | `dump_state()` snapshot matches golden file |

Naming convention (SDK repo): `test_{story_id}_ac{n}_{slug}` — e.g. `test_e2_s01_ac1_invalid_yaml_field_errors`.

Use `pytest.mark.parametrize` for edge cases (empty yaml, unknown phase keys, missing agent refs).

---

## Writing integration tests

Integration tests start a **real** Hayhooks app on an ephemeral localhost port with the **mock** profile. The shared fixture lives at `tests/integration/conftest.py::ephemeral_serve_url` (E3-S07).

```python
# See tests/integration/test_openai_contract.py
import httpx

def test_chat_completions_contract(ephemeral_serve_url):
    r = httpx.post(
        f"{ephemeral_serve_url}/v1/chat/completions",
        json={"model": "example", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert "choices" in body
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert isinstance(body["choices"][0]["message"]["content"], str)
```

Optional request field **`model_id`** selects a registry LLM (OpenAI `model` stays the harness name). Use **`respx`** to stub outbound `web_fetch` or provider HTTP without hitting the public internet.

Contract suite (E3-S07): `pytest tests/integration/test_openai_contract.py -v` — asserts OpenAI JSON shape, `model_id` override, and offline mock + stubbed fetch. Cross-OS green is covered by [E1-S07](../../docs/stories/epic-stories/24-story.md) (`.github/workflows/ci-matrix.yml`).

---

## Phase 1 security notes

Local `zaumzeug serve` is unauthenticated in Phase 1. Keep exposure narrow:

- Bind is **`127.0.0.1` only** — wide-open `0.0.0.0` is rejected.
- Put secrets in `.env` only (never YAML or deploy bundles).
- Production auth is proxy-only (Traefik ForwardAuth / bearer) in Phase 4 — see CLI security notes.

---

## Writing harness eval tests (optional)

### `zaumzeug eval` (harness.yaml)

Add an `eval:` block to `harness.yaml`, then run the CLI (E6-S02):

```yaml
eval:
  framework: builtin          # or deepeval (default when omitted)
  valset: data/val.jsonl      # JSONL: input, optional expected_output
  # deepeval only:
  # metrics:
  #   - type: AnswerRelevancyMetric
  #     threshold: 0.7
  # judge_model_id: strong
```

```bash
zaumzeug eval example --framework builtin
zaumzeug eval example                    # deepeval — needs [eval] extra
zaumzeug eval example --agent researcher
zaumzeug eval example --framework builtin --trace data/traces/run-001.jsonl
zaumzeug eval example --framework builtin --base-url
zaumzeug eval example --framework builtin --base-url http://staging:1416
```

**Builtin** loads the valset and checks exact/substring match on `expected_output` when present (no DeepEval). **DeepEval** builds `LLMTestCase` rows from agent output and runs configured metrics. Missing `eval:` exits with a clear error. See [CLI — zaumzeug eval](../reference/cli.md#zaumzeug-eval).

### Mode C — HTTP black-box (staging/debug)

Optional Mode C evals against an **already-running** `zaumzeug serve` over HTTP instead of building the agent in-process (Architecture §6.3). Same builtin / DeepEval metrics apply to the chat-completion response. Use this for staging and deployment debugging — **not** as a production gate or CI default.

```bash
# Terminal 1
zaumzeug serve example

# Terminal 2 — default URL http://127.0.0.1:<serve.hayhooks.port>
zaumzeug eval example --framework builtin --base-url

# Or point at a staging host
zaumzeug eval example --framework builtin --base-url http://staging.example:1416
```

Persist a default Mode C target in `harness.yaml`:

```yaml
eval:
  framework: builtin
  valset: data/val.jsonl
  base_url: http://127.0.0.1:1416   # or "" for localhost + harness port
```

CLI `--base-url` overrides `eval.base_url`. Do not combine Mode C with `--trace`.

### Trace → test case (Journey C)

When a production (or local) turn fails, export the Haystack run to JSONL under `usr-harnesses/<name>/data/traces/`, score it, then append the row to your valset so the failure becomes a regression case:

```text
production failure → data/traces/*.jsonl → zaumzeug eval --trace → append to valset
→ zaumzeug eval (optional) → zaumzeug compile → zaumzeug deploy → redeploy
```

**Export** (from Python after `Agent.run`):

```python
from zaumzeug.eval.trace import export_haystack_trace, append_trace_to_valset

# result = agent.run(messages=...)
path = export_haystack_trace(
    harness_dir,                    # usr-harnesses/<name>
    user_input="What broke?",
    haystack_result=result,
    expected_output="cite the failing stage",  # set the desired answer
    agent="researcher",
)
# → usr-harnesses/<name>/data/traces/trace-….jsonl
```

**Trace JSONL schema** (one object per line; valset-compatible field names):

| Field | Required | Purpose |
|---|---|---|
| `input` | Yes | User turn |
| `actual_output` | Yes | Assistant text from the Haystack run |
| `expected_output` | No | Desired answer — needed for builtin match / valset append |
| `retrieval_context` | No | RAG / context snippets (DeepEval metrics) |
| `tools_called` | No | Tool names observed on the turn (metadata) |
| `agent` | No | Agent id that produced the turn |
| `schema_version` | Auto | Currently `1` |
| `captured_at` | Auto | UTC ISO-8601 timestamp |

**Score** the captured turn without re-running the agent:

```bash
zaumzeug eval example --framework builtin --trace data/traces/run-001.jsonl
```

**Append to valset** (copies `input` + `expected_output` / `retrieval_context`; does not copy `actual_output` — set `expected_output` to the correct answer first):

```python
append_trace_to_valset(path, harness_dir / "data" / "val.jsonl")
```

Automatic production capture hooks land in Phase 4 ([E8-S03](../../docs/stories/epic-stories/60-story.md)). Until then, call `export_haystack_trace` from a failing session or a small debug script.

### DeepEval pytest scaffold

DeepEval treats LLM checks like pytest tests. Put optional files under `usr-harnesses/<name>/eval/` (Architecture §3.3) — **dev only**; the deploy packager excludes `eval/` (Architecture §10.1).

Scaffold a new harness with the template:

```bash
zaumzeug init my-harness --with-eval
pip install "zaumzeug[eval]"
deepeval test run usr-harnesses/my-harness/eval/
```

Or add the same layout by hand (the example harness already ships it):

```text
usr-harnesses/my-harness/
└── eval/
    ├── metrics.py           # custom BaseMetric subclasses (optional)
    └── test_researcher.py   # deepeval assert_test cases
```

Start with **20–50 cases from real failures** — not a thousand synthetic prompts on day one. Custom metrics live in `eval/metrics.py` and import like any local module when you run from the `eval/` directory:

```python
# eval/metrics.py — deterministic example (no LLM judge / API key)
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

class ContainsSubstringMetric(BaseMetric):
    def __init__(self, substring: str, *, threshold: float = 1.0) -> None:
        self.substring = substring
        self.threshold = threshold
        self.score = None
        self.success = None
        self.reason = None
        self.error = None

    def measure(self, test_case: LLMTestCase) -> float:
        found = self.substring.lower() in (test_case.actual_output or "").lower()
        self.score = 1.0 if found else 0.0
        self.success = self.score >= self.threshold
        self.reason = "found" if found else "missing"
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return bool(self.success)

    @property
    def __name__(self) -> str:
        return "Contains Substring"
```

```python
# eval/test_researcher.py
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from metrics import ContainsSubstringMetric

def test_researcher_stays_on_topic():
    metric = ContainsSubstringMetric("ZaumZeug")
    case = LLMTestCase(
        input="Summarize ZaumZeug workflow.yaml",
        actual_output="...",  # from zaumzeug run or captured trace
    )
    assert_test(case, [metric])
```

Run:

```bash
deepeval test run usr-harnesses/example/eval/
# or after init --with-eval:
deepeval test run usr-harnesses/my-harness/eval/
```

On Windows, if DeepEval’s progress UI fails with a UnicodeEncodeError, run with UTF-8:

```bash
# PowerShell
$env:PYTHONUTF8="1"; deepeval test run usr-harnesses/example/eval/
```

`deepeval test run` is a thin wrapper over pytest with DeepEval reporting. Use a custom non-LLM metric (like the scaffold’s `ContainsSubstringMetric`) for local smoke without API keys; add judge metrics (`GEval`, `AnswerRelevancyMetric`, …) when you want semantic scoring.

For deploy gates, set `deploy.eval_gate` in `harness.yaml` so `zaumzeug deploy` runs eval first (Architecture §6.4 / E5-S06 / E6-S03):

```yaml
# harness.yaml (dev copy; stripped from deploy bundle)
deploy:
  eval_gate: skip    # skip | warn | block (default: skip)
```

| `deploy.eval_gate` | Behavior |
|---|---|
| `skip` | Do not run eval on deploy (default). |
| `warn` | If `eval:` configured, run `zaumzeug eval`; print failures; **continue** deploy. |
| `block` | If `eval:` configured, run `zaumzeug eval`; **abort** deploy on any failure. |

CLI override: `zaumzeug deploy <name> --eval-gate block`. If `eval:` is absent, `block` / `warn` are a no-op. See [CLI — zaumzeug deploy](../reference/cli.md#zaumzeug-deploy).

---

## Environment variables

| Variable | Purpose |
|---|---|
| `HARNESS_LIVE_LLM=1` | Enable `tests/e2e/` live provider smoke (nightly / manual only — **never** set in default CI) |
| `HARNESS_LOG_LEVEL=DEBUG` | Verbose SDK + Haystack logs while debugging (equivalent to `serve`/`compile`/`eval --verbose`) |
| `PYTEST_OPENAI_API_KEY` | Re-record VCR cassettes (`pytest --record-mode=once`) |

Never commit API keys. `.env` is gitignored. Default CI runs mock only — see [CLI reference](../reference/cli.md) for `HARNESS_LIVE_LLM` and debugpy.

---

## CI expectations

Default branch CI (Win / macOS / Linux) is [`.github/workflows/ci-matrix.yml`](../../.github/workflows/ci-matrix.yml) (E1-S07):

1. OS install wrapper with `--skip-venv --verify`
   - Windows: `.\install\client-install.ps1 --skip-venv --verify`
   - macOS / Linux: `./install/client-install.sh --skip-venv --verify`
2. `zaumzeug doctor`
3. `zaumzeug serve example --dry-run`
4. Mock-model serve smoke on ephemeral port: `python install/ci_serve_smoke.py example`
5. `pytest tests/integration/test_openai_contract.py -v`
6. `pytest tests/unit tests/integration tests/usr-harnesses -v`

Eval regression and live e2e are **additional** tiers — nightly or on PRs that touch prompts/artifacts.

---

## Debugging failed tests

```bash
# Structured logs (--verbose or env var)
HARNESS_LOG_LEVEL=DEBUG zaumzeug serve example
zaumzeug serve example --verbose
zaumzeug serve example --dry-run --verbose

# IDE attach (debugpy ships in [dev])
python -m debugpy --listen 5678 -m zaumzeug.cli serve example

# Isolate Haystack vs config
zaumzeug doctor example --verbose
zaumzeug serve example --dry-run
zaumzeug compile example --dry-run
# escape hatch: hayhooks run ...  (low-level Haystack only)
```

---

## Phase roadmap

| Phase | Testing deliverables |
|---|---|
| **1** | `doctor`, mock profile, unit + integration pyramid, REST contract, cross-platform CI |
| **2** | Compile `--dry-run` (**Done** E4-S06 — `tests/integration/compile/test_compile_dry_run.py`), export golden snapshots (**Done** E4-S03a — `tests/compile/`), runtime `input_rewrite` preprocess (**Done** E4-S03b — `tests/integration/compile/test_compile_serve.py`), Pattern B adapter (**Done** E4-S04 — `tests/unit/compile/test_gepa_adapter.py`), artifact rollback / pin (**Done** E4-S07 — `tests/integration/compile/test_rollback.py`, `test_e4_s07_ac2_*`, `tests/integration/deploy/test_deploy_pin.py`), workflow diagram (**Done** E4-S08 — `tests/unit/compile/test_workflow_diagram.py`), `zaumzeug eval` (**Done** E6-S02 — `tests/unit/eval/test_runner.py`), `eval/` pytest scaffold (**Done** E6-S04 — `tests/integration/eval/test_deepeval_scaffold.py`), trace → eval case (**Done** E6-S05 — `tests/unit/eval/test_trace.py`), Mode C HTTP eval (**Done** E6-S06 — `tests/integration/eval/test_http_eval.py`) |
| **3** | MCP integration tests, tool-correctness eval |
| **4** | Production trace ratchet, `@observe` / Confident AI sync |

---

## Related guides

- [Multi-agent workflow](multi-agent-workflow.md) — `workflow.yaml` and stage routing under test
- [CLI reference](../reference/cli.md) — `--verbose`, `HARNESS_LOG_LEVEL`, `HARNESS_LIVE_LLM`, debugpy, serve/compile `--dry-run`, `doctor`, `eval` / `--trace` / `--base-url`, Phase 1 security notes
