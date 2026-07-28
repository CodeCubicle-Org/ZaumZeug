# Testing harnesses and the SDK

| | |
|---|---|
| **Audience** | Harness developers · SDK contributors |
| **Last updated** | 2026-07-22 |

ZaumZeug separates **fast deterministic tests** (config, serve wiring, REST shape) from **optional quality evals** (LLM output regression). Default CI uses the **`mock`** model profile — no API keys required.

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

# SDK test suite (repo root; contributors)
pytest tests/unit tests/integration tests/usr-harnesses -v

# Optional harness regression (after pip install "zaumzeug[eval]")
deepeval test run usr-harnesses/example/eval/
# or
zaumzeug eval example

# Live provider smoke (maintainers; costs money)
HARNESS_LIVE_LLM=1 pytest tests/e2e -v
```

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

DeepEval treats LLM checks like pytest tests. Start with **20–50 cases from real failures** — not a thousand synthetic prompts on day one.

```python
import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

def test_researcher_stays_on_topic():
    metric = GEval(
        name="Relevance",
        criteria="Answer must address the user question without unrelated topics.",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.INPUT],
        threshold=0.7,
    )
    case = LLMTestCase(
        input="Summarize ZaumZeug workflow.yaml",
        actual_output="...",  # from zaumzeug run or captured trace
    )
    assert_test(case, [metric])
```

Run:

```bash
deepeval test run usr-harnesses/my-harness/eval/
```

For deploy gates, set `deploy.eval_gate` in `harness.yaml` (`skip` | `warn` | `block`) — see compile/deploy guides (Phase 2).

---

## Environment variables

| Variable | Purpose |
|---|---|
| `HARNESS_LIVE_LLM=1` | Enable `tests/e2e/` live provider smoke (nightly / manual only — **never** set in default CI) |
| `HARNESS_LOG_LEVEL=DEBUG` | Verbose SDK + Haystack logs while debugging (equivalent to `serve`/`compile --verbose`) |
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
# escape hatch: hayhooks run ...  (low-level Haystack only)
```

---

## Phase roadmap

| Phase | Testing deliverables |
|---|---|
| **1** | `doctor`, mock profile, unit + integration pyramid, REST contract, cross-platform CI |
| **2** | Compile `--dry-run`, export golden snapshots (**Done** E4-S03a — `tests/compile/`), runtime `input_rewrite` preprocess (**Done** E4-S03b — `tests/integration/compile/test_compile_serve.py`), trace → eval case, optional `zaumzeug eval` |
| **3** | MCP integration tests, tool-correctness eval |
| **4** | Production trace ratchet, `@observe` / Confident AI sync |

---

## Related guides

- [Multi-agent workflow](multi-agent-workflow.md) — `workflow.yaml` and stage routing under test
- [CLI reference](../reference/cli.md) — `--verbose`, `HARNESS_LOG_LEVEL`, `HARNESS_LIVE_LLM`, debugpy, `--dry-run`, `doctor`, `eval` flags, Phase 1 security notes
