"""Shared SDK constants for config and runtime."""

# YAML key gating (compile/…). Kept at 1 so remaining Phase 2+ field hints
# stay intact while later epics unblock specific keys. Do not bump for catalog
# tools — use ``BUILTIN_CATALOG_PHASE`` instead (E7-S07 / E8-S01).
CURRENT_SDK_PHASE = 1

# Builtin tool ids available via ``tools.builtin`` (Architecture §6.5). Phase 3
# ships ``calculator`` and ``read_file``; Phase 4 adds ``search_docs`` (E8-S01).
BUILTIN_CATALOG_PHASE = 4
