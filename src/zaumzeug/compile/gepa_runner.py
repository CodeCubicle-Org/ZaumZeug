"""GEPA compile preflight (E4-S02a) and runner + artifacts (E4-S02b).

Preflight validates registry + ``.env`` for task/reflection LM ids.
``invoke_gepa`` runs ``dspy.GEPA`` (or a CI stub) and writes immutable
``artifacts/<run_id>/`` plus ``artifacts/current``. Haystack export
(``artifact-manifest.json``, prompts) is applied in ``write_artifact_run``
via ``compile/export.py`` (E4-S03a).
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from zaumzeug.config.models import AgentModelsConfig, ModelEntryConfig
from zaumzeug.config.resolver import CompileResolution
from zaumzeug.config.schemas import CompileConfig

__all__ = [
    "CompileLmPlan",
    "GepaPreflightError",
    "GepaRunError",
    "GepaRunResult",
    "default_gepa_metric",
    "gepa_budget_kwargs",
    "invoke_gepa",
    "model_entry_to_litellm",
    "module_has_input_rewrite",
    "preflight_compile_lms",
    "resolve_compile_lm_ids",
    "write_artifact_run",
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

# Registry provider → LiteLLM model-string prefix (Architecture §7).
_PROVIDER_LITELLM_PREFIX: dict[str, str] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "openrouter": "openrouter",
    "openai_compatible": "openai",
    "azure": "azure",
    "cohere": "cohere",
    "gemini": "gemini",
    "google": "gemini",
    "mock": "openai",
}

_INPUT_REWRITE_HINTS = frozenset(
    {
        "input_rewrite",
        "clarify",
        "rewrite",
        "clarify_rewrite",
        "input_clarify",
    }
)


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


class GepaRunError(RuntimeError):
    """GEPA optimization or artifact write failed."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        harness_name: str | None = None,
        agent_name: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.harness_name = harness_name
        self.agent_name = agent_name
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CompileLmPlan:
    """Resolved task and reflection model ids for a compile run."""

    task_model_id: str
    reflection_model_id: str
    task_entry: ModelEntryConfig
    reflection_entry: ModelEntryConfig

    @property
    def task_litellm(self) -> str:
        return model_entry_to_litellm(self.task_entry)

    @property
    def reflection_litellm(self) -> str:
        return model_entry_to_litellm(self.reflection_entry)

    @property
    def uses_mock_provider(self) -> bool:
        return self.task_entry.provider == "mock" or self.reflection_entry.provider == "mock"


@dataclass(slots=True)
class GepaRunResult:
    """Outcome of one agent GEPA compile (artifacts written)."""

    run_id: str
    artifact_dir: Path
    current_dir: Path
    optimized_module: Any
    gepa_kwargs: dict[str, Any]
    task_litellm: str
    reflection_litellm: str
    has_input_rewrite: bool
    stubbed: bool
    metric_feedback_shape: bool = True
    extras: dict[str, Any] = field(default_factory=dict)


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


def model_entry_to_litellm(entry: ModelEntryConfig) -> str:
    """Map a registry entry to a LiteLLM ``provider/model`` string for ``dspy.LM``."""
    prefix = _PROVIDER_LITELLM_PREFIX.get(entry.provider, entry.provider)
    model = entry.model.strip()
    if "/" in model and model.split("/", 1)[0] == prefix:
        return model
    return f"{prefix}/{model}"


def gepa_budget_kwargs(compile_config: CompileConfig) -> dict[str, Any]:
    """Build ``dspy.GEPA`` budget kwargs from ``CompileConfig`` (exactly one mode)."""
    if compile_config.auto is not None:
        return {"auto": compile_config.auto}
    if compile_config.max_metric_calls is not None:
        return {"max_metric_calls": compile_config.max_metric_calls}
    if compile_config.max_full_evals is not None:
        return {"max_full_evals": compile_config.max_full_evals}
    return {"auto": "light"}


def module_has_input_rewrite(module: Any) -> bool:
    """True when the DSPy module exposes a clarify/rewrite predictor (optional AC-4)."""
    named = getattr(module, "named_predictors", None)
    if not callable(named):
        return False
    for name, _pred in named():
        lowered = str(name).lower()
        if lowered in _INPUT_REWRITE_HINTS or "rewrite" in lowered or "clarify" in lowered:
            return True
    return False


def default_gepa_metric(
    example: Any,
    pred: Any,
    trace: Any = None,
    pred_name: str | None = None,
    pred_trace: Any = None,
) -> Any:
    """GEPA metric returning textual feedback (``dspy.Prediction(score=..., feedback=...)``)."""
    import dspy

    expected = _example_field(example, "answer") or _example_field(example, "expected") or ""
    answer = getattr(pred, "answer", None)
    if answer is None and isinstance(pred, dict):
        answer = pred.get("answer", "")
    answer_text = "" if answer is None else str(answer)
    expected_text = str(expected)

    if expected_text and expected_text in answer_text:
        score = 1.0
        feedback = "Good."
    elif expected_text:
        score = 0.0
        feedback = f"Include expected keyword in answer: {expected_text!r}."
    else:
        score = 1.0 if answer_text.strip() else 0.0
        feedback = "Good." if score >= 1.0 else "Provide a non-empty answer."

    return dspy.Prediction(score=score, feedback=feedback)


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


def invoke_gepa(
    *,
    module: Any,
    resolution: CompileResolution,
    lm_plan: CompileLmPlan,
    agent_dir: Path | str,
    metric: Callable[..., Any] | None = None,
    trainset: list[Any] | None = None,
    valset: list[Any] | None = None,
    gepa_cls: Any | None = None,
    run_id: str | None = None,
    stub: bool | None = None,
) -> GepaRunResult:
    """Run ``dspy.GEPA`` for one agent and write ``artifacts/<run_id>/`` + ``current``.

    When *stub* is true (default for ``provider: mock``), a no-network stub optimizer
    is used so CI can exercise the path without API keys.
    """
    agent_dir = Path(agent_dir)
    compile_config = resolution.compile_config
    use_stub = lm_plan.uses_mock_provider if stub is None else stub
    budget = gepa_budget_kwargs(compile_config)
    metric_fn = metric or default_gepa_metric
    has_rewrite = module_has_input_rewrite(module)

    loaded_train = trainset
    loaded_val = valset
    if loaded_train is None:
        loaded_train = _load_examples(agent_dir, compile_config.trainset)
    if loaded_val is None:
        loaded_val = _load_examples(agent_dir, compile_config.valset)
    if not loaded_train:
        loaded_train = _default_trainset()
    if loaded_val is None:
        loaded_val = list(loaded_train)

    try:
        import dspy
    except ImportError as exc:
        raise GepaRunError(
            "DSPy is required for compile (pip install -e \".[dev]\" or pip install dspy-ai)",
            harness_name=resolution.harness_name,
            agent_name=resolution.agent_name,
            suggestion='pip install -e ".[dev]"',
        ) from exc

    optimizer_cls = gepa_cls
    if optimizer_cls is None and use_stub:
        optimizer_cls = StubGEPA
    if optimizer_cls is None:
        optimizer_cls = dspy.GEPA

    task_lm = None
    reflection_lm = None
    if not use_stub:
        task_lm = _build_dspy_lm(lm_plan.task_entry, litellm_model=lm_plan.task_litellm)
        reflection_lm = _build_dspy_lm(
            lm_plan.reflection_entry,
            litellm_model=lm_plan.reflection_litellm,
        )

    gepa_init_kwargs: dict[str, Any] = {
        "metric": metric_fn,
        **budget,
    }
    if reflection_lm is not None:
        gepa_init_kwargs["reflection_lm"] = reflection_lm

    try:
        optimizer = optimizer_cls(**gepa_init_kwargs)
        if task_lm is not None:
            with dspy.context(lm=task_lm):
                optimized = optimizer.compile(
                    module,
                    trainset=loaded_train,
                    valset=loaded_val,
                )
        else:
            optimized = optimizer.compile(
                module,
                trainset=loaded_train,
                valset=loaded_val,
            )
    except GepaRunError:
        raise
    except Exception as exc:
        raise GepaRunError(
            (
                f"Harness '{resolution.harness_name}' agent '{resolution.agent_name}': "
                f"GEPA failed: {exc}"
            ),
            path=agent_dir,
            harness_name=resolution.harness_name,
            agent_name=resolution.agent_name,
            suggestion=(
                "Check compile.trainset/valset, task/reflection API keys in .env, "
                "and GEPA budget (auto / max_metric_calls)"
            ),
        ) from exc

    rid = run_id or generate_run_id()
    artifact_dir, current_dir = write_artifact_run(
        agent_dir,
        run_id=rid,
        payload={
            "run_id": rid,
            "harness_name": resolution.harness_name,
            "agent_name": resolution.agent_name,
            "module_ref": resolution.compile_module,
            "task_model_id": lm_plan.task_model_id,
            "reflection_model_id": lm_plan.reflection_model_id,
            "task_litellm": lm_plan.task_litellm,
            "reflection_litellm": lm_plan.reflection_litellm,
            "gepa_budget": budget,
            "has_input_rewrite": has_rewrite,
            "stubbed": use_stub,
            "optimizer": compile_config.optimizer,
        },
        optimized_module=optimized,
    )

    return GepaRunResult(
        run_id=rid,
        artifact_dir=artifact_dir,
        current_dir=current_dir,
        optimized_module=optimized,
        gepa_kwargs=gepa_init_kwargs,
        task_litellm=lm_plan.task_litellm,
        reflection_litellm=lm_plan.reflection_litellm,
        has_input_rewrite=has_rewrite,
        stubbed=use_stub,
    )


def generate_run_id(*, now: datetime | None = None) -> str:
    """Immutable UTC run id, e.g. ``20260728T095317Z``."""
    stamp = now or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    else:
        stamp = stamp.astimezone(timezone.utc)
    return stamp.strftime("%Y%m%dT%H%M%SZ")


def write_artifact_run(
    agent_dir: Path | str,
    *,
    run_id: str,
    payload: dict[str, Any],
    optimized_module: Any | None = None,
) -> tuple[Path, Path]:
    """Write ``artifacts/<run_id>/`` and update ``artifacts/current`` (symlink or copy)."""
    agent_dir = Path(agent_dir)
    artifacts_root = agent_dir / "artifacts"
    run_dir = artifacts_root / run_id
    if run_dir.exists():
        raise GepaRunError(
            f"Artifact run_id {run_id!r} already exists at {run_dir} (immutable)",
            path=run_dir,
            suggestion="Re-run compile to allocate a new run_id, or remove the stale folder",
        )

    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "gepa-run.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if optimized_module is not None:
        state = _safe_dump_state(optimized_module)
        if state is not None:
            (run_dir / "module_state.json").write_text(
                json.dumps(state, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
        # Haystack export (E4-S03a) before updating ``current`` so copy fallback includes it.
        from zaumzeug.compile.export import ExportError, export_optimized_module

        try:
            export_optimized_module(
                run_dir,
                optimized_module,
                run_id=run_id,
                module_ref=payload.get("module_ref"),
                harness_name=payload.get("harness_name"),
                agent_name=payload.get("agent_name"),
                gepa_metadata={
                    "stubbed": payload.get("stubbed"),
                    "has_input_rewrite": payload.get("has_input_rewrite"),
                    "gepa_budget": payload.get("gepa_budget"),
                    "optimizer": payload.get("optimizer"),
                },
            )
        except ExportError as exc:
            raise GepaRunError(
                f"Haystack export failed for run_id {run_id!r}: {exc}",
                path=exc.path or run_dir,
                harness_name=payload.get("harness_name"),
                agent_name=payload.get("agent_name"),
                suggestion=exc.suggestion
                or "Inspect dump_state() / compile.module and retry compile",
            ) from exc

    current = _update_artifacts_current(artifacts_root, run_id=run_id, run_dir=run_dir)
    return run_dir, current


class StubGEPA:
    """No-network GEPA stand-in for CI / ``provider: mock`` (E4-S02b)."""

    def __init__(self, metric: Callable[..., Any], **kwargs: Any) -> None:
        self.metric = metric
        self.kwargs = kwargs

    def compile(
        self,
        student: Any,
        *,
        trainset: list[Any],
        valset: list[Any] | None = None,
    ) -> Any:
        # Exercise metric feedback shape once so stub still validates AC-3 wiring.
        if trainset:
            example = trainset[0]
            try:
                pred = student(**_example_as_kwargs(example))
            except Exception:
                pred = _stub_prediction_from_example(example)
            _ = self.metric(example, pred)
        return student


def _update_artifacts_current(artifacts_root: Path, *, run_id: str, run_dir: Path) -> Path:
    current = artifacts_root / "current"
    if current.is_symlink() or current.exists():
        if current.is_symlink() or current.is_file():
            current.unlink()
        else:
            shutil.rmtree(current)

    try:
        os.symlink(run_id, current, target_is_directory=True)
        return current
    except OSError:
        shutil.copytree(run_dir, current)
        return current


def _build_dspy_lm(entry: ModelEntryConfig, *, litellm_model: str) -> Any:
    import dspy

    kwargs: dict[str, Any] = {}
    if entry.api_base_url:
        kwargs["api_base"] = entry.api_base_url
    if entry.generation_kwargs:
        kwargs.update(entry.generation_kwargs)
    return dspy.LM(litellm_model, **kwargs)


def _safe_dump_state(module: Any) -> dict[str, Any] | None:
    dump = getattr(module, "dump_state", None)
    if not callable(dump):
        return None
    try:
        state = dump()
    except Exception:
        return None
    return state if isinstance(state, dict) else {"state": state}


def _load_examples(agent_dir: Path, relative: str | None) -> list[Any] | None:
    if not relative:
        return None
    path = (agent_dir / relative).resolve()
    try:
        path.relative_to(agent_dir.resolve())
    except ValueError as exc:
        raise GepaRunError(
            f"Dataset path escapes agent folder: {relative!r}",
            path=path,
            suggestion="Keep trainset/valset under the agent directory",
        ) from exc
    if not path.is_file():
        raise GepaRunError(
            f"Compile dataset not found: {path}",
            path=path,
            suggestion=f"Create {relative} under the agent folder or fix compile.trainset/valset",
        )
    return _read_jsonl_examples(path)


def _read_jsonl_examples(path: Path) -> list[Any]:
    import dspy

    examples: list[Any] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise GepaRunError(
                f"Invalid JSONL in {path} at line {line_no}: {exc}",
                path=path,
            ) from exc
        if not isinstance(row, dict):
            raise GepaRunError(
                f"JSONL row must be an object at {path}:{line_no}",
                path=path,
            )
        ex = dspy.Example(**row)
        inputs = [k for k in row if k != "answer"]
        if inputs:
            ex = ex.with_inputs(*inputs)
        elif "question" in row:
            ex = ex.with_inputs("question")
        examples.append(ex)
    return examples


def _default_trainset() -> list[Any]:
    import dspy

    return [
        dspy.Example(question="What is ZaumZeug?", answer="harness").with_inputs("question"),
        dspy.Example(question="Name the runtime library.", answer="Haystack").with_inputs(
            "question"
        ),
    ]


def _example_field(example: Any, name: str) -> Any:
    if hasattr(example, name):
        return getattr(example, name)
    if isinstance(example, dict):
        return example.get(name)
    get = getattr(example, "get", None)
    if callable(get):
        return get(name)
    return None


def _example_as_kwargs(example: Any) -> dict[str, Any]:
    if hasattr(example, "inputs") and callable(example.inputs):
        try:
            return dict(example.inputs())
        except Exception:
            pass
    if isinstance(example, dict):
        return {k: v for k, v in example.items() if k != "answer"}
    question = _example_field(example, "question")
    if question is not None:
        return {"question": question}
    return {}


def _stub_prediction_from_example(example: Any) -> Any:
    import dspy

    answer = _example_field(example, "answer") or "expected"
    return dspy.Prediction(answer=str(answer))


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
