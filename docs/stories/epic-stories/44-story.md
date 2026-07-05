# E5-S04 — `HARNESS_ROOT=deploy` environment override

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/44-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E5-S04 |
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
| **Prerequisites** | [E5-S03](43-story.md#e5-s03-zaumzeug-serve-deploy) |

### User story

As **ops**, I want `HARNESS_ROOT=deploy`, so that serve/mcp/acp default to production roots in container or systemd environments.

### References

- [PRD E5.4](../../prd.md#epic-e5--deploy-packaging-phase-2)
- [Architecture §2.5 — Env over convention](../../architecture/01-overview-and-principles.md#25-cross-platform-portability)


### Implementation resources

**Internal spec**

- [Architecture §2.5 — env over convention](../../architecture/01-overview-and-principles.md#25-cross-platform-portability)

```bash
HARNESS_ROOT=deploy zaumzeug serve my-harness --deploy
```

### Acceptance criteria

- [ ] **AC-1** `HARNESS_ROOT=deploy` forces deploy root for serve, mcp, acp
- [ ] **AC-2** Default dev root remains `usr-harnesses/`
- [ ] **AC-3** Documented in deploy README and CLI reference

### Implementation tasks (build)

- [ ] Centralize root resolution in config loader

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E5-S04 / E5.4`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/deploy/test_harness_root.py::test_e5_s04_ac1_env_forces_deploy_root` |
| AC-2 | `tests/unit/deploy/test_harness_root.py::test_e5_s04_ac2_default_usr_harnesses` |
| AC-3 | **manual:** README.deploy.md and CLI reference document env var |

- [ ] Every AC row above has a passing test or documented manual exception
- [ ] `pytest tests/unit/deploy/test_harness_root.py -v` passes

### Definition of done

- [ ] No hardcoded `usr-harnesses` in serve runner when env set
- [ ] Verification checklist complete; all ACs traced to tests

---
