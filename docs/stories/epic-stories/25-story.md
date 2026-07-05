# E1-S08 — Future: `zaumzeug install-project` (blocked)

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/25-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-05 |
| **Story ID** | E1-S08 |
| **Epic** | [E1 — Onboarding and Project Setup](../03-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 3 of 8 |
| **Story sequence** | 25 of 63 (global build order) |
| **Source** | Extracted from [`03-epic.md`](../03-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E1](../../prd.md#epic-e1--onboarding-and-project-setup-phase-1) · [Architecture](../../architecture.md) |

---

## E1-S08 — Future: `zaumzeug install-project` (blocked)

| Field | Value |
|---|---|
| **Feature** | E1 future (open #3) |
| **Persona** | PyPI consumer |
| **Priority** | Deferred |

### User story

As a **PyPI consumer**, I want to scaffold harness folders in an arbitrary project cwd, so that I do not need a full SDK repo clone.

### References

- [PRD open decision #4](../../prd.md#12-open-decisions-blockers-for-some-stories)
- [PRD §9 — Future commands](../../prd.md#9-cli-surface-epic-mapping)

### Blocker

- [ ] Resolve `install/` vs `zaumzeug install-project` for PyPI consumers before implementation

### Implementation tasks (when unblocked)

- [ ] Reuse `client_install.py` logic without editable repo install
- [ ] Scaffold `usr-harnesses/`, `user-docs/`, `.env` in consumer cwd

### Verification (when unblocked)

Apply [Story verification](../00-README.md#story-verification-required) with AC labels and `tests/unit/install/test_install_project.py` mapping when story is split from blocker.

---
