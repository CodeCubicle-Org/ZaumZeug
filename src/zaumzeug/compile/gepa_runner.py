"""GEPA compile preflight (E4-S02a) and runner hook (E4-S02b).

E4-S02a validates registry + ``.env`` for task/reflection LM ids and refuses
to invoke GEPA when preflight fails. Full ``dspy.GEPA`` execution is E4-S02b.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zaumzeug.config.models import AgentModelsConfig, ModelEntryConfig
from zaumzeug.config.resolver import CompileResolution
from zaumzeug.config.schemas import CompileConfig

__all__ = [
    "CompileLmPlan",
    "GepaPreflightError",
    "preflight_compile_lms",
    "resolve_compile_lm_ids",
]

# Provider → env vars required for live compile LMs (mirrors doctor checks).
_PROVIDER_ENV_KEYS: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "openai_compatible": (),  # localhost optional
    "azure": ("AZURE_API_KEY", "AZURE_OPENAI_API_KEY"),
    "cohere": ("COHERE_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}


class GepaPreflightError(ValueError):
    """Compile LM preflight failed before any GEPA invocation."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        harness_name: str | None = None,
        agent_name: str | None = None,
        model_id: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.harness_name = harness_name
        self.agent_name = agent_name
        self.model_id = model_id
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CompileLmPlan:
    """Resolved task and reflection model ids for a compile run."""

    task_model_id: str
    reflection_model_id: str
    task_entry: ModelEntryConfig
    reflection_entry: ModelEntryConfig


def resolve_compile_lm_ids(
    compile_config: CompileConfig,
    *,
    registry: AgentModelsConfig,
    default_model_id: str | None = None,
) -> tuple[str, str]:
    """Resolve task/reflection model ids (defaults → agent/registry default)."""
    fallback = default_model_id or registry.default_model_id
    task_id = compile_config.task_model_id or fallback
    reflection_id = compile_config.reflection_model_id or task_id
    return task_id, reflection_id


def preflight_compile_lms(
    resolution: CompileResolution,
    *,
    registry: AgentModelsConfig,
    project_root: Path | str,
    environ: dict[str, str] | None = None,
) -> CompileLmPlan:
    """Validate task/reflection LM ids against the merged registry and ``.env``.

    Does not import or invoke DSPy/GEPA.
    """
    project_root = Path(project_root)
    compile_config = resolution.compile_config
    task_id, reflection_id = resolve_compile_lm_ids(
        compile_config,
        registry=registry,
        default_model_id=resolution.default_model_id,
    )

    task_entry = _require_registry_entry(
        resolution,
        registry=registry,
        model_id=task_id,
        role="task_model_id",
    )
    reflection_entry = _require_registry_entry(
        resolution,
        registry=registry,
        model_id=reflection_id,
        role="reflection_model_id",
    )

    dotenv = _parse_dotenv(project_root / ".env")
    env = environ if environ is not None else dict(os.environ)

    for model_id, entry, role in (
        (task_id, task_entry, "task_model_id"),
        (reflection_id, reflection_entry, "reflection_model_id"),
    ):
        _require_env_for_provider(
            resolution,
            model_id=model_id,
            entry=entry,
            role=role,
            dotenv=dotenv,
            environ=env,
            project_root=project_root,
        )

    return CompileLmPlan(
        task_model_id=task_id,
        reflection_model_id=reflection_id,
        task_entry=task_entry,
        reflection_entry=reflection_entry,
    )


def _require_registry_entry(
    resolution: CompileResolution,
    *,
    registry: AgentModelsConfig,
    model_id: str,
    role: str,
) -> ModelEntryConfig:
    entry = registry.models.get(model_id)
    if entry is None:
        known = ", ".join(sorted(registry.models)) or "(none)"
        raise GepaPreflightError(
            (
                f"Harness '{resolution.harness_name}' agent '{resolution.agent_name}': "
                f"compile.{role}={model_id!r} is not in the merged model registry. "
                f"Known model ids: {known}."
            ),
            path=resolution.agent_yaml_path,
            harness_name=resolution.harness_name,
            agent_name=resolution.agent_name,
            model_id=model_id,
            suggestion=(
                f"Add {model_id!r} to agents/{resolution.agent_name}/agents-models.yaml "
                f"(or fix compile.{role} in {resolution.agent_yaml_path})"
            ),
        )
    return entry


def _require_env_for_provider(
    resolution: CompileResolution,
    *,
    model_id: str,
    entry: ModelEntryConfig,
    role: str,
    dotenv: dict[str, str],
    environ: dict[str, str],
    project_root: Path,
) -> None:
    provider = entry.provider
    if provider == "mock":
        return

    required = _PROVIDER_ENV_KEYS.get(provider)
    if required is None:
        # Unknown provider: require a conventional API key name.
        required = (f"{provider.upper()}_API_KEY",)
    if not required:
        return

    missing = [name for name in required if not _env_lookup(name, environ, dotenv)]
    if not missing:
        return

    dotenv_path = project_root / ".env"
    raise GepaPreflightError(
        (
            f"Harness '{resolution.harness_name}' agent '{resolution.agent_name}': "
            f"compile.{role}={model_id!r} uses provider {provider!r} but API key(s) "
            f"missing: {', '.join(missing)}. Set them in {dotenv_path} or the environment "
            "before running GEPA."
        ),
        path=dotenv_path,
        harness_name=resolution.harness_name,
        agent_name=resolution.agent_name,
        model_id=model_id,
        suggestion=(
            f"Add {', '.join(missing)} to {dotenv_path} "
            f"(or use provider: mock for offline compile preflight)"
        ),
    )


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].strip()
        if "=" not in stripped:
            continue
        key, _, raw = stripped.partition("=")
        key = key.strip()
        value = raw.strip().strip("'\"")
        if key:
            values[key] = value
    return values


def _env_lookup(name: str, environ: dict[str, str], dotenv: dict[str, str]) -> str | None:
    if name in environ and environ[name]:
        return environ[name]
    if name in dotenv and dotenv[name]:
        return dotenv[name]
    return None


def invoke_gepa(*_args: Any, **_kwargs: Any) -> None:
    """Placeholder for E4-S02b — must not be called from E4-S02a preflight path."""
    raise RuntimeError(
        "GEPA runner is not implemented yet (E4-S02b). "
        "Compile preflight completed without invoking GEPA."
    )
