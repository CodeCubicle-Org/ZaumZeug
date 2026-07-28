"""DSPy loader, GEPA preflight/runner, and export contract."""

from zaumzeug.compile.gepa_runner import (
    CompileLmPlan,
    GepaPreflightError,
    preflight_compile_lms,
    resolve_compile_lm_ids,
)
from zaumzeug.compile.module_loader import (
    ModuleLoaderError,
    load_dspy_module,
    load_dspy_module_from_resolution,
    parse_compile_module_ref,
)
from zaumzeug.compile.runner import (
    CompileAgentResult,
    CompileError,
    CompileResult,
    format_compile_result,
    run_compile,
)

__all__ = [
    "CompileAgentResult",
    "CompileError",
    "CompileLmPlan",
    "CompileResult",
    "GepaPreflightError",
    "ModuleLoaderError",
    "format_compile_result",
    "load_dspy_module",
    "load_dspy_module_from_resolution",
    "parse_compile_module_ref",
    "preflight_compile_lms",
    "resolve_compile_lm_ids",
    "run_compile",
]
