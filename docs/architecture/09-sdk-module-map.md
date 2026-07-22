# SDK module map

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 11. SDK modules to build

Maps to [PRD epics](../prd.md#8-functional-requirements-epics). Implementation layout:

| # | Component | Module | Epic | Status (2026-07-22) |
|---|---|---|---|---|
| 1 | CLI | `cli.py` | E1–E7 | **Partial** (E2-S00, E2-S05, E2-S06, E3-S02, E3-S08, E1-S04) — `init`, `doctor`, `serve` (Hayhooks + `--dry-run`), `run` (serial workflow), `--verbose` on serve/compile/run; other subcommands stub |
| 1a | Logging | `logging.py` | E2 | **Done** (E2-S06) — `configure_logging()`, `log_request()`, secret redaction, `HARNESS_LOG_LEVEL` |
| 1b | Doctor | `doctor/` | E2 | **Done** (E2-S04a–S04c) — preflight checks, phase-aware warnings, `--deploy`, `--verbose`, `--json` |
| 1c | Scaffold / init | `scaffold/` | E1 | **Done** (E1-S04, 2026-07-22) — `init_harness()`, name validation, copy from `install/templates/harness/`; CLI `zaumzeug init <name> [--force]` |
| 2 | Config loader + Pydantic schemas | `config/` | E2 | **Done** (E2-S01–S03, S04c, S07) — `harness.yaml`, `workflow.yaml`, `models.yaml` merge, agent resolver, harness root resolution |
| 3 | ModelRouter | `runtime/model_router.py` | E3 | **Done** (E3-S01, 2026-07-08) — config-driven router; Phase 1 providers: `mock`, `openrouter`, `openai_compatible`; lazy cache per provider+endpoint; phase-gated native cloud providers; HTTP `model_id` override via serve (E3-S07) |
| 4 | Runtime factory + builtin tools | `runtime/factory.py`, `runtime/tools/` | E3, E7 | **Done** (E3-S00, 2026-07-20) — `build_agent()` builds single Haystack `Agent` via ModelRouter + `resolve_agent_serve()` + builtin catalog (`web_fetch`); no DSPy/GEPA on this path |
| 5 | Serve / Hayhooks wrapper | `serve/` | E3, E7 | **Partial** (E2-S05, E3-S02, E3-S06, E3-S07, 2026-07-21) — `validate_serve()`, `--dry-run`, `runner.py` (`prepare_serve` / `run_serve`) builds entry agent via factory and starts Hayhooks on **enforced** localhost; OpenAI contract + request `model_id` → ModelRouter; MCP/ACP pending E7 |
| 6 | DSPy module loader | `compile/` | E4 | Planned |
| 7 | Export contract | `compile/export.py` | E4 | Planned |
| 8 | Workflow diagram generator | `compile/workflow_diagram.py` | E4 | Planned |
| 9 | Serial workflow runner | `runtime/workflow.py` | E3 | **Done** (E3-S08, 2026-07-21) — `run_workflow()` serial stages, stage-scoped ModelRouter, `--from`, prior-output context; pipeline stages Phase-1 stub |
| 10 | Haystack GEPA evaluator | `compile/gepa_adapter.py` *(Phase 4+ — Pattern B)* | E4.4 / E8 | Deferred |
| 11 | Deploy packager | `deploy/packager.py` | E5 | Planned |
| 12 | DeepEval runner (optional) | `eval/` | E6 | Planned |
| 13 | ACP adapter | `serve/acp.py` | E7 | Planned |
| 14 | Integrations (Haystack, DSPy, GEPA, LiteLLM) | `integrations/` | E3, E4 | **Partial** (E3-S01, E3-S05) — `integrations/mock.py`, `integrations/haystack.py` (`PROVIDERS`, `build_chat_generator`); DSPy/GEPA pending E4 |
| 15 | Client + target install | `install/client_install.py`, `install/target_install.py` | E1, E5 | **Partial** (E1-S01–S03, 2026-07-22) — `client_install.py` + thin wrappers + project scaffolding (`usr-harnesses/example/`, `config/models.yaml`, `.env.example`, `.cursor/mcp.json.example`, `.gitignore`); per-harness `zaumzeug init` → row 1c; `target_install` → E5; live `--cursor-mcp` → E7-S03 |

---
