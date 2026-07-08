# SDK module map

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 11. SDK modules to build

Maps to [PRD epics](../prd.md#8-functional-requirements-epics). Implementation layout:

| # | Component | Module | Epic | Status (2026-07-08) |
|---|---|---|---|---|
| 1 | CLI | `cli.py` | E1–E7 | **Partial** (E2-S00) — `doctor` implemented; other subcommands stub |
| 1b | Doctor | `doctor/` | E2 | **Done** (E2-S04a–S04c) — preflight checks, phase-aware warnings, `--deploy`, `--verbose`, `--json` |
| 2 | Config loader + Pydantic schemas | `config/` | E2 | **Partial** (E2-S01–S03, S04c) — `harness.yaml`, `models.yaml` merge, agent resolver, harness root resolution |
| 3 | ModelRouter | `runtime/model_router.py` | E3 | Planned |
| 4 | Runtime factory + builtin tools | `runtime/`, `runtime/tools.py` | E3, E7 | Planned |
| 5 | Serve / Hayhooks wrapper | `serve/` | E3, E7 | Planned |
| 6 | DSPy module loader | `compile/` | E4 | Planned |
| 7 | Export contract | `compile/export.py` | E4 | Planned |
| 8 | Workflow diagram generator | `compile/workflow_diagram.py` | E4 | Planned |
| 9 | Serial workflow runner | `runtime/workflow.py` | E3 | Planned |
| 10 | Haystack GEPA evaluator | `compile/gepa_adapter.py` *(Phase 4+ — Pattern B)* | E4.4 / E8 | Deferred |
| 11 | Deploy packager | `deploy/packager.py` | E5 | Planned |
| 12 | DeepEval runner (optional) | `eval/` | E6 | Planned |
| 13 | ACP adapter | `serve/acp.py` | E7 | Planned |
| 14 | Integrations (Haystack, DSPy, GEPA, LiteLLM) | `integrations/` | E3, E4 | Planned |
| 15 | Client + target install | `install/client_install.py`, `install/target_install.py` | E1, E5 | Planned |

---
