# E1-S08 — Future: `zaumzeug install-project` (deferred)

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/25-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-22 |
| **Story ID** | E1-S08 |
| **Status** | Deferred (decision resolved; implement with PyPI publish) |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 (decision) / post–v1 publish (implementation) |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 25 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) |

---

## E1-S08 — Future: `zaumzeug install-project` (deferred)

| Field | Value |
|---|---|
| **Feature** | E1 future (was open #3) |
| **Persona** | PyPI consumer |
| **Priority** | Deferred |
| **Status** | Deferred (2026-07-22) — open #3 resolved; CLI + wheel packaging postponed until PyPI package creation/publishing |
| **Prerequisites** | [E1-S03](20-story.md) scaffolding · published `zaumzeug` wheel that includes scaffold templates |

### User story

As a **PyPI consumer**, I want to scaffold harness folders in an arbitrary project cwd, so that I do not need a full SDK repo clone.

### References

- [PRD §12 — Resolved open #3](../../prd.md#12-open-decisions-blockers-for-some-stories)
- [PRD §9 — Future commands](../../prd.md#9-cli-surface-epic-mapping)
- [Architecture §3.4](../../architecture/02-repository-and-layout.md#34-install-scripts-dev-vs-target)

### Decision (resolved 2026-07-22)

| Path | Audience | Behavior |
|---|---|---|
| `install/client_install.py` (+ wrappers) | SDK repo clone / Phase 1 | Create `.venv`, editable `[dev]` install, scaffold from `install/templates/` |
| `zaumzeug install-project` | PyPI consumer (after publish) | Scaffold only into cwd — reuse scaffold logic **without** editable repo install; templates must ship in the wheel |

**Supported today:** clone + `install/client_install.py`. Do **not** implement `install-project` or PyPI publish as part of Phase 1–4 v1 clone workflows.

- [x] Resolve `install/` vs `zaumzeug install-project` for PyPI consumers before implementation

### Implementation tasks (when unblocked — with PyPI publish)

- [ ] Bundle scaffold templates in the published wheel (so discovery works without a repo checkout)
- [ ] Reuse `client_install.py` / `scaffold_project` logic without editable repo install
- [ ] Add `zaumzeug install-project` CLI — scaffold `usr-harnesses/`, `user-docs/`, `.env` in consumer cwd
- [ ] Document PyPI consumer path in `user-docs/getting-started/installation.md`

### Verification (when unblocked)

Apply [Story verification](../00-README.md#story-verification-required) with AC labels and `tests/unit/install/test_install_project.py` mapping when implementation starts.

### Definition of done

- [ ] Open #3 recorded as resolved in [PRD §12](../../prd.md#12-open-decisions-blockers-for-some-stories) ✅ (2026-07-22)
- [ ] `zaumzeug install-project` implemented and tested against a wheel that includes templates
- [ ] PyPI consumer install path documented in user-docs
