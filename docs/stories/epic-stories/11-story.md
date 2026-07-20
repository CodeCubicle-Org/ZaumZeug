# E3-S03 — Builtin tool: `web_fetch`

| | |
|---|---|
| **Document** | User story |
| **File** | `docs/stories/epic-stories/11-story.md` |
| **Created** | 2026-07-04 |
| **Last modified** | 2026-07-08 |
| **Story ID** | E3-S03 |
| **Status** | Done |
| **Epic** | [E3 — Runtime and Local Serve](../02-epic.md) |
| **Phase** | 1 |
| **Epic build order** | 2 of 8 |
| **Story sequence** | 11 of 63 (global build order) |
| **Source** | Extracted from [`02-epic.md`](../02-epic.md) |
| **Related** | [Stories index](../00-README.md) · [Epic E3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1) · [Architecture](../../architecture.md) |

---

## E3-S03 — Builtin tool: `web_fetch`

| Field | Value |
|---|---|
| **Feature** | E3.3 |
| **Persona** | Harness developer |
| **Priority** | P1 |
| **Prerequisites** | [E2-S01](02-story.md#e2-s01-pydantic-config-schemas) |
| **Status** | Done (2026-07-08) |

### User story

As a **harness developer**, I want a built-in `web_fetch` tool, so that my research agent can retrieve URL content without custom Python.

### References

- [PRD E3.3](../../prd.md#epic-e3--runtime-and-local-serve-phase-1)
- [Architecture §6.5](../../architecture/05-configuration.md#65-builtin-tools-catalog)


### Implementation resources

**Libraries & docs**

- [httpx — HTTP client](https://www.python-httpx.org/) (outbound fetch; runtime dependency)
- [respx — mock httpx in tests](https://lundberg.github.io/respx/)
- [Haystack `@component` tools](https://docs.haystack.deepset.ai/docs/custom-components)
- [Architecture §6.5 — `web_fetch` limits](../../architecture/05-configuration.md#65-builtin-tools-catalog)

**Code sketch — SSRF guard**

```python
import ipaddress, socket
def is_public_host(host: str) -> bool:
    ip = ipaddress.ip_address(socket.gethostbyname(host))
    return not (ip.is_private or ip.is_loopback or ip.is_link_local)
```

### Acceptance criteria

- [x] **AC-1** Phase 1 ships `web_fetch` in SDK tool catalog
- [x] **AC-2** HTTPS only; 30s timeout; 1 MB response cap
- [x] **AC-3** Blocks private/link-local IPs (SSRF guard)
- [x] **AC-4** Referenced via `tools.builtin: [web_fetch]` in yaml
- [x] **AC-5** Unknown builtin ID fails validation with list of available IDs for current phase

### Implementation tasks (build)

- [x] Implement `src/zaumzeug/runtime/tools/web_fetch.py`
- [x] Register in `src/zaumzeug/runtime/tools/catalog.py` (phase-aware catalog)
- [x] Validate `tools.builtin` in `AgentConfig` / `load_agent_config()` (`src/zaumzeug/config/schemas.py`, `loader.py`)
- [x] Wire catalog into minimal `build_agent()` in `src/zaumzeug/runtime/factory.py` *(full E3-S00 factory in [12-story.md](12-story.md))*

### Verification (after build)

Per [Story verification](../00-README.md#story-verification-required). Test file header: `# Story: E3-S03 / E3.3`.

| AC | Test |
|---|---|
| AC-1 | `tests/unit/runtime/tools/test_web_fetch.py::test_e3_s03_ac1_catalog_lists_web_fetch_phase1` |
| AC-2 | `tests/unit/runtime/tools/test_web_fetch.py::test_e3_s03_ac2_https_only_timeout_and_size_cap` |
| AC-3 | `tests/unit/runtime/tools/test_web_fetch.py::test_e3_s03_ac3_ssrf_blocks_private_ips` |
| AC-4 | `tests/integration/test_runtime_factory.py::test_e3_s03_ac4_yaml_builtin_reference` |
| AC-5 | `tests/unit/config/test_schemas.py::test_e3_s03_ac5_unknown_builtin_id_fails_with_list` |

- [x] Every AC row above has a passing test or documented manual exception
- [x] `pytest tests/unit/runtime/tools/test_web_fetch.py -v` passes

### Definition of done

- [x] Catalog loader wired into runtime factory (`build_builtin_tools()` / `build_agent()` in `runtime/factory.py`; serve runner uses factory in E3-S02, 2026-07-20)
- [x] Verification checklist complete; all ACs traced to tests

---
