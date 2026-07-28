# Epic backlog — index and implementation order

| | |
|---|---|
| **Document** | Stories index |
| **File** | `docs/stories/00-README.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 (E6-S03 / E5-S06 done) |
| **Status** | Active |

---

## File numbering vs PRD epic IDs

File numbers follow **technical build order**, not PRD epic ID order. Each file header lists both **Build order** and **Epic ID**.

| Build order | File | Epic ID | Phase | PRD epic |
|---|---|---|---|---|
| 1 | [01-epic.md](01-epic.md) | **E2** | 1 | Configuration and validation |
| 2 | [02-epic.md](02-epic.md) | **E3** | 1 | Runtime and local serve |
| 3 | [03-epic.md](03-epic.md) | **E1** | 1 | Onboarding and project setup |
| 4 | [04-epic.md](04-epic.md) | **E4** | 2 | Compile and GEPA pipeline |
| 5 | [05-epic.md](05-epic.md) | **E6** | 2 | Evaluation and quality (optional) |
| 6 | [06-epic.md](06-epic.md) | **E5** | 2 | Deploy packaging |
| 7 | [07-epic.md](07-epic.md) | **E7** | 3 | Tools, MCP, and ACP |
| 8 | [08-epic.md](08-epic.md) | **E8** | 4 | RAG and production hardening |

**Why E1 is build order 3:** Install, CI (`--verify`), and `zaumzeug serve example` require config (E2), runtime (E3), and example harness templates (E3) to exist first.

**Why E6 precedes E5:** `deploy.eval_gate` (E5.6) calls `zaumzeug eval` (E6.2). Core eval must exist before deploy eval gate; other deploy stories (E5.1–E5.5, E5.7–E5.9) can start after E4.

---

## Implementation progress

| Story | Status | Date |
|---|---|---|
| [E2-S00](epic-stories/01-story.md) — SDK package skeleton and CLI foundation | Done | 2026-07-08 |
| [E2-S01](epic-stories/02-story.md) — Pydantic config schemas | Done | 2026-07-08 |
| [E2-S02](epic-stories/03-story.md) — `models.yaml` merge | Done | 2026-07-08 |
| [E2-S03](epic-stories/04-story.md) — Runtime agent resolution rules | Done | 2026-07-08 |
| [E2-S04a](epic-stories/05.1-story.md) — `zaumzeug doctor` (core checks) | Done | 2026-07-08 |
| [E2-S04b](epic-stories/05.2-story.md) — `zaumzeug doctor` (phase-aware warnings) | Done | 2026-07-08 |
| [E2-S04c](epic-stories/05.3-story.md) — `zaumzeug doctor --deploy` mode | Done | 2026-07-08 |
| [E2-S05](epic-stories/06-story.md) — `zaumzeug serve --dry-run` | Done | 2026-07-08 |
| [E2-S06](epic-stories/07-story.md) — Structured logging | Done | 2026-07-08 |
| [E2-S07](epic-stories/08-story.md) — `workflow.yaml` schema (serial) | Done | 2026-07-08 |
| [E3-S05](epic-stories/09-story.md) — Mock model profile | Done | 2026-07-08 |
| [E3-S01](epic-stories/10-story.md) — ModelRouter | Done | 2026-07-08 |
| [E3-S03](epic-stories/11-story.md) — Builtin tool: `web_fetch` | Done | 2026-07-08 |
| [E3-S00](epic-stories/12-story.md) — Runtime factory (Haystack Agent builder) | Done | 2026-07-20 |
| [E3-S02](epic-stories/13-story.md) — `zaumzeug serve` (dev mode) | Done | 2026-07-20 |
| [E3-S04](epic-stories/14-story.md) — Example harness (general research agent) | Done | 2026-07-20 |
| [E3-S06](epic-stories/15-story.md) — Phase 1 test infrastructure and security baseline | Done | 2026-07-20 |
| [E3-S07](epic-stories/16-story.md) — OpenAI REST contract tests | Done | 2026-07-21 |
| [E3-S08](epic-stories/17-story.md) — `zaumzeug run` (serial workflow) | Done | 2026-07-21 |
| [E1-S01](epic-stories/18-story.md) — Cross-platform install script | Done | 2026-07-21 |
| [E1-S02](epic-stories/19-story.md) — Install shell wrappers | Done | 2026-07-22 |
| [E1-S03](epic-stories/20-story.md) — Project scaffolding on install | Done | 2026-07-22 |
| [E1-S04](epic-stories/21-story.md) — `zaumzeug init` command | Done | 2026-07-22 |
| [E1-S05](epic-stories/22-story.md) — User documentation skeleton | Done | 2026-07-22 |
| [E1-S06](epic-stories/23-story.md) — Root README / CONTRIBUTING.md | Done | 2026-07-22 |
| [E1-S07](epic-stories/24-story.md) — Cross-platform CI matrix | Done | 2026-07-22 |
| [E1-S08](epic-stories/25-story.md) — `zaumzeug install-project` (PyPI) | Deferred | 2026-07-22 (decision; implement with publish) |
| [E4-S01](epic-stories/26-story.md) — DSPy module loader | Done | 2026-07-28 |
| [E4-S02a](epic-stories/27.1-story.md) — Compile CLI and Phase 2 schema | Done | 2026-07-28 |
| [E4-S02b](epic-stories/27.2-story.md) — GEPA runner and artifacts | Done | 2026-07-28 |
| [E4-S03a](epic-stories/28.1-story.md) — Export contract and manifest | Done | 2026-07-28 |
| [E4-S03b](epic-stories/28.2-story.md) — Runtime `input_rewrite` preprocess | Done | 2026-07-28 |
| [E4-S04](epic-stories/29-story.md) — Haystack GEPA evaluator wrapper (Pattern B) | Done | 2026-07-28 |
| [E4-S05](epic-stories/30-story.md) — Post-compile serve uses artifact | Done | 2026-07-28 |
| [E4-S06](epic-stories/31-story.md) — `--dry-run` on compile | Done | 2026-07-28 |
| [E4-S07](epic-stories/32-story.md) — Rollback to pinned artifact run | Done | 2026-07-28 |
| [E4-S08](epic-stories/33-story.md) — Workflow diagram at compile | Done | 2026-07-28 |
| [E6-S01](epic-stories/34-story.md) — Optional `[eval]` extra | Done | 2026-07-28 |
| [E6-S02](epic-stories/35-story.md) — `zaumzeug eval` command | Done | 2026-07-28 |
| [E6-S03](epic-stories/36-story.md) — Eval gate on deploy | Done | 2026-07-28 |
| [E5-S06](epic-stories/46-story.md) — Deploy eval gate | Done | 2026-07-28 |

Phase 1 implementation: package skeleton, `harness.yaml` validation, three-tier `models.yaml` merge, runtime agent resolution, `zaumzeug doctor` (E2-S00–S04c), serve dry-run (E2-S05), structured logging (E2-S06), workflow schema (E2-S07), mock model profile (E3-S05), config-driven ModelRouter (E3-S01), builtin `web_fetch` tool (E3-S03), runtime factory (E3-S00), `zaumzeug serve` Hayhooks runner (E3-S02), the reference `example` research harness (E3-S04), Phase 1 test infra (E3-S06), OpenAI REST contract tests (E3-S07), serial `zaumzeug run` (E3-S08), `install/client_install.py` (E1-S01), install shell wrappers (E1-S02), project scaffolding on install (E1-S03), `zaumzeug init` (E1-S04), user-docs skeleton (E1-S05), new-contributor guide `CONTRIBUTING.md` (E1-S06), and three-OS CI matrix (E1-S07) are done. [E1-S08](epic-stories/25-story.md) (`zaumzeug install-project`) is **deferred** until PyPI package publish (open #3 resolved 2026-07-22). Phase 2: [E4-S01](epic-stories/26-story.md)–[E4-S08](epic-stories/33-story.md) done; [E6-S01](epic-stories/34-story.md)–[E6-S03](epic-stories/36-story.md) done ([E5-S06](epic-stories/46-story.md) shipped early with E6-S03). Next build: [E6-S04](epic-stories/37-story.md) (`eval/` pytest scaffold).

---

## Phase 1 build graph

```text
E2-S00  Package skeleton + pyproject.toml + CLI stub ✅
   ↓
E2-S01  Pydantic config schemas ✅
E2-S02  models.yaml merge ✅
E2-S03  Runtime agent resolution rules ✅
E2-S04a  zaumzeug doctor (core checks) ✅
E2-S04b  zaumzeug doctor (phase-aware warnings) ✅
E2-S04c  zaumzeug doctor --deploy ✅
E2-S05  zaumzeug serve --dry-run ✅
E2-S06  structured logging ✅
E2-S07  workflow.yaml schema ✅
E3-S05  Mock model profile ✅
E3-S01  ModelRouter ✅
E3-S03  web_fetch ✅
E3-S00  Runtime factory (Agent builder) ✅
E3-S02  zaumzeug serve ✅
   ↓
E3-S04  Example harness templates ✅
E3-S06  Test infra + Phase 1 security (localhost) ✅
E3-S07  OpenAI REST contract tests ✅
E3-S08  zaumzeug run (serial workflow) ✅
   ↓
E1-S01  Cross-platform install script ✅
E1-S02  Install shell wrappers ✅
E1-S03  Project scaffolding on install (copies E3 templates) ✅
E1-S04  zaumzeug init ✅
E1-S05  User docs skeleton ✅
E1-S06  Root README / CONTRIBUTING.md ✅
E1-S07  CI matrix (last — validates full stack) ✅
E1-S08  Future: zaumzeug install-project (deferred — with PyPI publish)
```

## Phase 2 build graph (E4 start)

```text
E4-S01  DSPy module loader ✅ (2026-07-28)
   ↓
E4-S02a  Compile CLI + Phase 2 schema ✅ (2026-07-28)
E4-S02b  GEPA runner + artifacts ✅ (2026-07-28)
   ↓
E4-S03a  Export contract + manifest ✅ (2026-07-28)
E4-S03b  Runtime input_rewrite preprocess ✅ (2026-07-28)
E4-S04  Haystack GEPA evaluator / Pattern B ✅ (2026-07-28)
E4-S05  Post-compile serve uses artifact ✅ (2026-07-28)
E4-S06  compile --dry-run ✅ (2026-07-28)
E4-S07  Artifact rollback ✅ (2026-07-28)
E4-S08  Workflow diagram at compile ✅ (2026-07-28)
   ↓
E6-S01  Optional [eval] extra ✅ (2026-07-28)
E6-S02  zaumzeug eval command ✅ (2026-07-28)
E6-S03  Eval gate on deploy ✅ (2026-07-28) — shared E5-S06 ✅
```

## Validation summary (2026-07-05, re-checked)

Cross-checked against [PRD §8](../prd.md#8-functional-requirements-epics) and [Architecture §11](../architecture/09-sdk-module-map.md#11-sdk-modules-to-build).

| Check | Result |
|---|---|
| All PRD features E1.1–E8.6 covered | ✅ One or more stories per feature |
| Epics in correct delivery phases (1→4) | ✅ File phases match [PRD §10](../prd.md#10-delivery-phases-milestones) |
| Build order (E2→E3→E1→E4→E6→E5→E7→E8) | ✅ Dependencies coherent; E6 before E5 for eval gate |
| Within-epic story order documented | ✅ Each epic file lists implementation order |
| Architecture §-prefixed anchors | ✅ Restored `## N.` headings in topic files; fixed Pattern A/B, §5.5, MCP/ACP slugs |
| E6-S02 ↔ E5-S06 cross-links | ✅ Fixed `#e6-s02-zaumzeug-eval-command` anchor |
| Internal story cross-links | ✅ Normalized to GitHub heading slugs (no `eN-sNN--` double-hyphen form) |
| Testing tech stack + playbook | ✅ [§4.5](../architecture/03-technology-stack.md#45-test-dependencies), [§13.6](../architecture/10-operations-and-reference.md#136-testing-playbook), [testing guide](../user-docs/guides/testing.md) |
| Story verification + AC traceability | ✅ [Story verification](#story-verification-required); AC-# labels in all stories |

### Gaps closed in this review

| Gap | Resolution |
|---|---|
| No SDK skeleton / `pyproject.toml` story | Added **E2-S00** in [01-epic.md](01-epic.md) |
| No runtime Agent factory | Added **E3-S00** in [02-epic.md](02-epic.md) |
| No test fixture harness / localhost security | Added **E3-S06** |
| PRD E3 story seed (OpenAI contract) | **Done** (E3-S07, 2026-07-21) — contract suite + HTTP `model_id`; cross-OS green closed by [E1-S07](epic-stories/24-story.md) (2026-07-22) |
| PRD E4 story seed (artifact rollback) | Added **E4-S07** |
| E5 before E6 broke eval gate dependency | Swapped files: **05=E6**, **06=E5** |
| E1 before E2/E3 broke CI/doctor/serve | Moved E1 to **03-epic.md** |
| GEPA scope open | **Resolved:** Phase 2 CLI = Pattern A; optional input rewrite at compile; Pattern B (E4-S04) shipped 2026-07-28 as adapter + schema |
| Serial multi-agent workflow (no E9) | **E2-S07** `workflow.yaml`; **E3-S08** `zaumzeug run`; folded into E2/E3/E4/E5 |
| Workflow diagram at compile | **Done** (E4-S08, 2026-07-28) — Mermaid `docs/workflow-diagram.md` on every `zaumzeug compile`; `--workflow-diagram-only` |
| User guide: workflow + pipelines | [user-docs/guides/multi-agent-workflow.md](../user-docs/guides/multi-agent-workflow.md) |
| Architecture split broke §N anchors | Restored `## N.` on H2 headings in `docs/architecture/` topic files; corrected Pattern/MCP slugs in stories |
| Story `#anchor` slugs drifted from headings | Normalized 27 cross-links to GitHub auto-slugs derived from `## E*-S* — …` titles |
| Testing tech stack + playbook | [§4.5](../architecture/03-technology-stack.md#45-test-dependencies), [§13.6](../architecture/10-operations-and-reference.md#136-testing-playbook), [user-docs/guides/testing.md](../user-docs/guides/testing.md) |

### Still deferred (not missing stories)

| Item | Affected stories | Notes |
|---|---|---|
| `zaumzeug install-project` + PyPI publish | [E1-S08](epic-stories/25-story.md) | Open #3 **resolved** (2026-07-22): dual path; implement with package publish |
| A2A defer | E8-S04 | PRD open #5 |

**Resolved:** **`install/` vs `install-project` (open #3)** — both coexist; clone+`install/` for Phase 1–4 v1; CLI deferred until PyPI publish — [E1-S08](epic-stories/25-story.md). **Production auth (Phase 4)** — Traefik proxy-only; no in-process SDK auth in v1 — [E8-S02](08-epic.md#e8-s02-production-auth). Product name **ZaumZeug** (PyPI `zaumzeug`, CLI `zaumzeug`) — [Architecture §3.2](../architecture/02-repository-and-layout.md#32-package-naming). **GEPA Phase 2 = Pattern A** (`dspy.GEPA` default CLI); **optional input rewrite/clarify templates** at compile time (E4-S03); **post-compile serve prefers artifact** ([E4-S05](epic-stories/30-story.md), 2026-07-28); **`optimize_anything` / Pattern B** shipped early as adapter + schema ([E4-S04](epic-stories/29-story.md), 2026-07-28) — CLI remains Pattern A. **Hayhooks self-hosted** — `zaumzeug serve|mcp` on target host (Docker via E8-S05); Haystack Enterprise Platform not in v1 scope — [Architecture §8.2](../architecture/06-runtime-and-protocols.md#82-harness-vs-raw-hayhooks).

---

## Story template (all epics)

Each story includes:

1. **Metadata** — Feature ID, persona, priority, prerequisites
2. **User story** — As a … I want … so that …
3. **References** — PRD, Architecture, external docs
4. **Acceptance criteria** — checkboxes labeled **AC-1**, **AC-2**, … (stable IDs for traceability)
5. **Implementation tasks (build)** — feature/code work only; no tests in this section
6. **Verification (after build)** — AC → test mapping; run only after build tasks complete
7. **Definition of done** — includes `pytest` green for this story’s test paths

---

## Story verification (required)

Every story follows **build first, verify second**. A story is **not done** until verification passes.

### Workflow

1. Complete all **Implementation tasks (build)**.
2. Add or extend **Verification** tests that prove each acceptance criterion.
3. Run `pytest` for the paths listed in Verification; fix failures before closing the story.
4. Wire new tests into CI when the story’s phase has a matrix (Phase 1 → [E1-S07](03-epic.md#e1-s07-cross-platform-ci-matrix); Phase 2+ → deploy/serve smoke stories as noted).

### AC traceability rules

| Rule | Detail |
|---|---|
| **AC labels** | Number acceptance criteria **AC-1**, **AC-2**, … within each story (e.g. E2-S01 AC-3). |
| **Test naming** | Prefer `test_{story_id_lower}_ac{n}_{slug}` — e.g. `test_e2_s01_ac1_invalid_yaml_field_errors` in `tests/unit/config/test_schemas.py`. |
| **Coverage** | Every **AC** maps to ≥1 automated test **or** an explicit **manual** row with rationale (docs-only, CI orchestration, or deferred blocker). |
| **Verification table** | Each story’s Verification section lists `AC-n → test path::test_name` (or **manual:** checklist). |
| **Cross-story tests** | If one test covers multiple stories, list the AC in each story and note the shared test once. |
| **Story anchors** | Cross-links use `#eN-sNN-slug-from-heading` (GitHub auto-slug of the `## E*-S* — …` title). Do not invent descriptive slugs or `eN-sNN--` double-hyphen forms. |
| **Feature ID** | Story metadata **Feature** (e.g. E2.1) appears in test module docstring or a `# Story: E2-S01 / E2.1` comment at top of test file. |

### Manual-only exceptions (allowed when documented)

- **Pure documentation** stories (e.g. E1-S06, E7-S08, E8-S02): Verification uses a **manual** checklist mapped to ACs; no pytest required unless link/content assertions are added later. (E1-S05 added path/content tests in `tests/unit/docs/`.)
- **CI orchestration** (E1-S07): Verification is the workflow itself; individual ACs trace to workflow steps/jobs.
- **Deferred** stories (E1-S08 until PyPI publish, E8-S04): Verification section omitted until implementation starts; template still applies when implemented.

### Example Verification block

```markdown
### Verification (after build)

| AC | Test |
|---|---|
| AC-1 | `tests/unit/config/test_schemas.py::test_e2_s01_ac1_invalid_yaml_field_errors` |
| AC-2 | `tests/unit/config/test_schemas.py::test_e2_s01_ac2_phase1_minimal_valid` |
| AC-3 | `tests/unit/config/test_schemas.py::test_e2_s01_ac3_unknown_key_phase_hint` |
| AC-4 | `tests/unit/config/test_schemas.py::test_e2_s01_ac4_error_includes_path_and_field` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/config/test_schemas.py -v` passes
```

---

## Related documents

- [Epic stories (individual files)](epic-stories/00-README.md) — one story per file; split stories use decimal suffixes (e.g. `05.1-story.md`)
- [Implementation resources index](epic-stories/00-implementation-resources.md) — library docs and code sketches by technology
- [PRD](../prd.md) — requirements and acceptance criteria source of truth
- [Architecture](../architecture.md) — hub; topic files in [architecture/](../architecture/00-README.md); testing: [§4.5](../architecture/03-technology-stack.md#45-test-dependencies), [§13.6](../architecture/10-operations-and-reference.md#136-testing-playbook)
- [user-docs/guides/testing.md](../user-docs/guides/testing.md) — end-user testing guide (install template)
- [cloudflare-harness.md](../cloudflare-harness.md) — **illustrative example only** (not in ZaumZeug scope)
- [Ideation](../ideation-stage.md) — full YAML examples until `user-docs/reference/` exists
