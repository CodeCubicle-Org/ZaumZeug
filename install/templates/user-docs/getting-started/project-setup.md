# Project setup

| | |
|---|---|
| **Audience** | Harness developers |
| **Last updated** | 2026-08-21 |

After [installation](installation.md), use this guide to add harnesses beyond the shipped `example` and to understand the project layout.

---

## Layout at a glance

```text
<project>/
├── usr-harnesses/
│   ├── example/          # shipped by install (unless --no-example)
│   └── <your-name>/      # created with zaumzeug init
├── config/
│   └── models.yaml       # global model defaults
├── .env.example
└── user-docs/
```

Each harness folder holds `harness.yaml`, `workflow.yaml`, optional `models.yaml`, and one or more `agents/<role>/` directories. See [Your first harness](first-harness.md) for the `example` tree.

---

## Add a harness with `zaumzeug init`

From the project root (where `usr-harnesses/` lives):

```bash
zaumzeug init my-agent
zaumzeug init my-agent --with-eval   # optional DeepEval pytest under eval/
```

This creates `usr-harnesses/my-agent/` from the Phase 1 template:

| Piece | Role |
|---|---|
| **`harness.yaml`** | Name, `serve.hayhooks.port`, optional `models: models.yaml` |
| **`workflow.yaml`** | Single `agent` stage as `entry` |
| **`agents/agent/`** | Runtime via `system_prompt`, mock `agents-models.yaml` |
| **`models.yaml`** | Optional harness-wide aliases (comments by default) |
| **`eval/`** *(with `--with-eval`)* | Optional DeepEval `metrics.py` + `test_*.py` (dev-only; not shipped in deploy) |
| **`data/traces/`** | Captured Haystack turns (JSONL) for `zaumzeug eval --trace` — see [Testing — Journey C](../guides/testing.md#trace--test-case-journey-c) |

The harness name must be a single safe path segment (letters, digits, `_`, `-`; no `..` or separators). If the folder already exists, init fails unless you pass `--force` (overwrites the folder).

```bash
zaumzeug init my-agent --force
```

### Next steps

```bash
zaumzeug doctor my-agent
zaumzeug serve my-agent
# optional (needs pip install "zaumzeug[eval]"):
# deepeval test run usr-harnesses/my-agent/eval/
# Mode C staging/debug — black-box a running serve:
# zaumzeug eval my-agent --framework builtin --base-url
```

Edit `agents/agent/prompts/system.md`, tools, and models as needed. For a fuller research-oriented layout (including a sample `eval/`), copy patterns from `usr-harnesses/example/` or start from [Your first harness](first-harness.md). See [Testing — DeepEval pytest scaffold](../guides/testing.md#deepeval-pytest-scaffold) and [Mode C](../guides/testing.md#mode-c--http-black-box-stagingdebug).

---

## Related

- [CLI reference](../reference/cli.md) — `init`, `doctor`, `serve`, `run`
- [Multi-agent workflow](../guides/multi-agent-workflow.md) — `workflow.yaml` and stages
- [Custom tools](../guides/custom-tools.md) — `tools.custom` Python modules under `agents/<name>/tools/`
- [Cursor MCP setup](../guides/cursor-mcp.md) — `.cursor/mcp.json` → `http://localhost:{mcp_port}/mcp`
- [Installation](installation.md) — first-time project scaffold
