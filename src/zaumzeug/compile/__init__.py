"""DSPy loader, GEPA runner, and export contract."""

from zaumzeug.compile.gepa_runner import (
    CompileLmPlan,
    GepaPreflightError,
    GepaRunError,
    GepaRunResult,
    StubGEPA,
    default_gepa_metric,
    gepa_budget_kwargs,
    invoke_gepa,
    model_entry_to_litellm,
    module_has_input_rewrite,
    preflight_compile_lms,
    resolve_compile_lm_ids,
    write_artifact_run,
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
    "GepaRunError",
    "GepaRunResult",
    "ModuleLoaderError",
    "StubGEPA",
    "default_gepa_metric",
    "format_compile_result",
    "gepa_budget_kwargs",
    "invoke_gepa",
    "load_dspy_module",
    "load_dspy_module_from_resolution",
    "model_entry_to_litellm",
    "module_has_input_rewrite",
    "parse_compile_module_ref",
    "preflight_compile_lms",
    "resolve_compile_lm_ids",
    "run_compile",
    "write_artifact_run",
]
