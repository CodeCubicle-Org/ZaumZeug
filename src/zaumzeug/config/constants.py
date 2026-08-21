"""Shared SDK constants for config and runtime."""

# YAML key gating (compile/a2a/expose/…). Kept at 1 so Phase 2/4 field hints stay intact
# while later epics unblock specific keys. Do not bump for catalog tools — use
# ``BUILTIN_CATALOG_PHASE`` instead (E7-S07).
CURRENT_SDK_PHASE = 1

# Builtin tool ids available via ``tools.builtin`` (Architecture §6.5). Phase 3
# ships ``calculator`` and ``read_file``; ``search_docs`` stays Phase 4 (E8).
BUILTIN_CATALOG_PHASE = 3
