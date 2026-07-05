# SDK module map

**Part of:** [Architecture index](../architecture.md) · [PRD](../prd.md)

---

## 11. SDK modules to build

Maps to [PRD epics](../prd.md#8-functional-requirements-epics). Implementation layout:

| # | Component | Module | Epic |
|---|---|---|---|
| 1 | CLI | `cli.py` | E1–E7 |
| 2 | Config loader + Pydantic schemas | `config/` | E2 |
| 3 | ModelRouter | `runtime/model_router.py` | E3 |
| 4 | Runtime factory + builtin tools | `runtime/`, `runtime/tools.py` | E3, E7 |
| 5 | Serve / Hayhooks wrapper | `serve/` | E3, E7 |
| 6 | DSPy module loader | `compile/` | E4 |
| 7 | Export contract | `compile/export.py` | E4 |
| 8 | Workflow diagram generator | `compile/workflow_diagram.py` | E4 |
| 9 | Serial workflow runner | `runtime/workflow.py` | E3 |
| 10 | Haystack GEPA evaluator | `compile/gepa_adapter.py` *(Phase 4+ — Pattern B)* | E4.4 / E8 |
| 11 | Deploy packager | `deploy/packager.py` | E5 |
| 12 | DeepEval runner (optional) | `eval/` | E6 |
| 13 | ACP adapter | `serve/acp.py` | E7 |
| 14 | Integrations (Haystack, DSPy, GEPA, LiteLLM) | `integrations/` | E3, E4 |
| 15 | Client + target install | `install/client_install.py`, `install/target_install.py` | E1, E5 |

---
