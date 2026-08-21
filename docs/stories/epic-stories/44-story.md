# E5-S04 — `HARNESS_ROOT=deploy` environment override

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/44-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-28 |
| **Story ID** | E5-S04 |
| **Status** | Done |
| **Epic** | [E5 — Deploy Packaging](../06-epic.md) |
| **Phase** | 2 |
| **Epic build order** | 6 of 8 |
| **Story sequence** | 44 of 63 (global build order) |
| **Source** | Extracted from [`06-epic.md`](../06-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E5](../../prd.md#epic-e5--deploy-packaging-phase-2) · [Architecture](../../architecture.md) |

---

## E5-S04 — `HARNESS_ROOT=deploy` environment override

| Field | Value |
|---|---|
| **Feature** | E5.4 |
| **Persona** | Ops / platform |
| **Priority** | P1 |
| **Prerequisites** | [E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy) ✅ (2026-07-28) |

### User story

As **ops**, I want `HARNESS_ROOT=deploy`, so that serve/mcp/acp default to production roots in container or systemd environments.

### References

- [PRD E5.4](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §2.5 — Env over convention](../../architecture/01-overview-and-principles.md#25-cross-platform-portability)


### Implementation resources

**Internal spec**

- [Architecture §2.5 — env over convention](../../architecture/01-overview-and-principles.md#25-cross-platform-portability)
- [Architecture §8.1 — source roots](../../architecture/06-runtime-and-protocols.md#81-source-roots)

```bash
HARNESS_ROOT=deploy zaumzeug serve my-harness
```

**Code**

- `src/zaumzeug/config/harness_root.py` — `is_deploy_mode()`, `resolve_harness_path()`, `PROTOCOL_ROOT_COMMANDS`
- `src/zaumzeug/serve/validate.py` / `serve/runner.py` — env-aware deploy root (no hardcoded `usr-harnesses`)
- `src/zaumzeug/cli.py` — mcp/acp stubs honour `HARNESS_ROOT` / `--deploy`

### Acceptance criteria

- [x] **AC-1** `HARNESS_ROOT=deploy` forces deploy root for serve, mcp, acp
- [x] **AC-2** Default dev root remains `usr-harnesses/`
- [x] **AC-3** Documented in deploy README and CLI reference

### Implementation tasks (build)

- [x] Centralize root resolution in config loader (`config/harness_root.py` → `resolve_harness_path`)

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S04 / E5.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/deploy/test_harness_root.py::test_e5_s04_ac1_env_forces_deploy_root` |
| AC-2 | `tests/unit/deploy/test_harness_root.py::test_e5_s04_ac2_default_usr_harnesses` |
| AC-3 | **manual:** README.deploy.md and CLI reference document env var |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/deploy/test_harness_root.py -v` passes (2 passed, 0 skipped)

### Definition of done

- [x] No hardcoded `usr-harnesses` in serve runner when env set
- [x] Verification checklist complete; all ACs traced to tests

### Implementation notes (2026-07-28)

- Canonical API: `resolve_harness_path()` combines `--deploy` + `HARNESS_ROOT=deploy`; serve/doctor/run use it; mcp/acp stubs resolve the same root.
- Serve banner uses `harness_root_segment()` (no literal `"usr-harnesses"`).
- Docs: `install/templates/deploy/README.deploy.md`, `user-docs/reference/cli.md` (+ install template mirror).
- Later: [E7-S05](54-story.md) replaced the `zaumzeug acp` stub with Agent Client Protocol stdio JSON-RPC (`serve/acp.py`, 2026-08-21). Root resolution is unchanged.

---
