"""``zaumzeug eval`` orchestration — builtin JSONL checks or DeepEval metrics (E6-S02).

Eval is a **dev-only** path: it is never imported or invoked from ``serve`` /
production Hayhooks wiring (PRD NG3 adjacent).

``--trace`` (E6-S05) scores a captured Haystack JSONL turn without re-running
the agent — see :mod:`zaumzeug.eval.trace`.

Mode C (E6-S06): optional HTTP black-box against a running ``zaumzeug serve``
via ``POST /v1/chat/completions`` (``--base-url`` / ``eval.base_url``).
Staging and debug only — not a production gate.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import httpx
from haystack.dataclasses import ChatMessage

from zaumzeug.config import (
    AgentResolutionError,
    ConfigValidationError,
    EvalConfig,
    EvalMetricConfig,
    HarnessConfig,
    load_harness,
    load_merged_agent_models,
    load_workflow,
    resolve_serve_entry,
)
from zaumzeug.config.harness_root import harness_dir as resolve_harness_dir
from zaumzeug.doctor.project import find_project_root
from zaumzeug.eval import DeepEvalMissingError, require_deepeval
from zaumzeug.eval.trace import TraceError, load_trace_jsonl
from zaumzeug.runtime.factory import RuntimeFactoryError, build_agent_bundle
from zaumzeug.runtime.model_router import ModelRouter, ModelRouterError
from zaumzeug.runtime.preprocess import preprocess_openai_messages
from zaumzeug.runtime.workflow import build_stage_messages

__all__ = [
    "DEFAULT_EVAL_FRAMEWORK",
    "DEFAULT_EVAL_HOST",
    "DEFAULT_HAYHOOKS_PORT",
    "MISSING_EVAL_MESSAGE",
    "EvalCaseResult",
    "EvalError",
    "EvalResult",
    "builtin_match",
    "chat_completion_actual_output",
    "default_eval_base_url",
    "format_eval_result",
    "load_valset_jsonl",
    "resolve_eval_base_url",
    "resolve_eval_framework",
    "run_eval",
]

DEFAULT_EVAL_FRAMEWORK: Literal["deepeval"] = "deepeval"
DEFAULT_EVAL_HOST = "127.0.0.1"
DEFAULT_HAYHOOKS_PORT = 1416

MISSING_EVAL_MESSAGE = (
    "No eval configured. Add an `eval:` block to harness.yaml."
)

# HTTP Mode C timeouts — staging/debug against a local or remote serve.
_HTTP_EVAL_TIMEOUT = httpx.Timeout(60.0, connect=10.0)

EvalFramework = Literal["deepeval", "builtin"]
AgentRunner = Callable[[str], str]


def _serve_port(harness_config: HarnessConfig) -> int:
    if harness_config.serve and harness_config.serve.hayhooks:
        return harness_config.serve.hayhooks.port
    return DEFAULT_HAYHOOKS_PORT


def default_eval_base_url(harness_config: HarnessConfig) -> str:
    """Default Mode C base URL: localhost + ``serve.hayhooks.port`` (AC-2)."""
    return f"http://{DEFAULT_EVAL_HOST}:{_serve_port(harness_config)}"


def resolve_eval_base_url(
    *,
    cli_base_url: str | None,
    eval_config: EvalConfig,
    harness_config: HarnessConfig,
) -> str | None:
    """Resolve Mode C base URL: CLI ``--base-url`` → ``eval.base_url`` → None.

    An empty string (CLI ``--base-url`` alone, or ``eval.base_url: ""``) means
    use :func:`default_eval_base_url`. Returns ``None`` for in-process Mode A.
    """
    if cli_base_url is not None:
        raw = cli_base_url
    elif eval_config.base_url is not None:
        raw = eval_config.base_url
    else:
        return None
    stripped = raw.strip()
    if stripped:
        return stripped.rstrip("/")
    return default_eval_base_url(harness_config)


def chat_completion_actual_output(payload: Mapping[str, Any]) -> str:
    """Extract assistant text from an OpenAI-shaped chat completion body."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise EvalError(
            "Chat completions response missing non-empty `choices`",
            suggestion="Confirm the server exposes OpenAI-compatible "
            "/v1/chat/completions",
        )
    first = choices[0]
    if not isinstance(first, Mapping):
        raise EvalError(
            "Chat completions `choices[0]` is not an object",
            suggestion="Confirm the server returns OpenAI-shaped JSON",
        )
    message = first.get("message")
    if isinstance(message, Mapping):
        content = message.get("content")
        if content is not None:
            return str(content)
    text = first.get("text")
    if text is not None:
        return str(text)
    raise EvalError(
        "Chat completions response has no assistant content",
        suggestion="Confirm choices[0].message.content is present",
    )


def _http_agent_runner(*, base_url: str, model: str) -> AgentRunner:
    """Mode C: call running serve ``POST /v1/chat/completions`` (E6-S06)."""
    endpoint = f"{base_url.rstrip('/')}/v1/chat/completions"

    def _run(user_input: str) -> str:
        try:
            response = httpx.post(
                endpoint,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": user_input}],
                },
                timeout=_HTTP_EVAL_TIMEOUT,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = (exc.response.text or "")[:300]
            raise EvalError(
                f"Mode C HTTP eval failed ({exc.response.status_code}) "
                f"at {endpoint}: {body}",
                suggestion=(
                    "Confirm `zaumzeug serve` is running and --base-url matches "
                    "the serve host/port (staging/debug only)"
                ),
            ) from exc
        except httpx.HTTPError as exc:
            raise EvalError(
                f"Mode C HTTP eval could not reach {endpoint}: {exc}",
                suggestion=(
                    "Start `zaumzeug serve <harness>` first, or pass "
                    "--base-url http://127.0.0.1:<port> (staging/debug only)"
                ),
            ) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise EvalError(
                f"Mode C HTTP eval got non-JSON from {endpoint}",
                suggestion="Confirm the URL points at zaumzeug serve / Hayhooks",
            ) from exc
        if not isinstance(payload, Mapping):
            raise EvalError(
                f"Mode C HTTP eval expected a JSON object from {endpoint}",
            )
        return chat_completion_actual_output(payload)

    return _run


class EvalError(RuntimeError):
    """Eval orchestration failed with an actionable message."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        harness_name: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.harness_name = harness_name
        self.suggestion = suggestion
        super().__init__(message)


@dataclass(slots=True)
class EvalCaseResult:
    """Outcome for one valset row."""

    index: int
    input: str
    expected_output: str | None
    actual_output: str
    passed: bool
    detail: str = ""


@dataclass(slots=True)
class EvalResult:
    """Outcome of ``zaumzeug eval`` for one harness."""

    harness_name: str
    harness_dir: Path
    framework: EvalFramework
    agent_name: str
    cases: list[EvalCaseResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0

    @property
    def exit_code(self) -> int:
        return 0 if self.failed == 0 else 1


def resolve_eval_framework(
    eval_config: EvalConfig,
    *,
    framework_override: str | None = None,
) -> EvalFramework:
    """Resolve framework: CLI override → yaml → default ``deepeval`` (AC-4, AC-5)."""
    if framework_override is not None:
        normalized = framework_override.strip().lower()
        if normalized not in {"deepeval", "builtin"}:
            raise EvalError(
                f"Unknown eval framework {framework_override!r} "
                "(expected 'deepeval' or 'builtin')",
                suggestion="Use --framework builtin or --framework deepeval",
            )
        return normalized  # type: ignore[return-value]
    if eval_config.framework is not None:
        return eval_config.framework
    return DEFAULT_EVAL_FRAMEWORK


def load_valset_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL rows with ``input`` and optional ``expected_output``."""
    path = Path(path)
    if not path.is_file():
        raise EvalError(
            f"Eval valset not found: {path}",
            path=path,
            suggestion="Set eval.valset to an existing JSONL file under the harness",
        )
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EvalError(
            f"Cannot read eval valset {path}: {exc}",
            path=path,
        ) from exc

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvalError(
                f"Invalid JSONL in {path} at line {line_no}: {exc}",
                path=path,
            ) from exc
        if not isinstance(row, dict):
            raise EvalError(
                f"Invalid JSONL in {path} at line {line_no}: expected object, "
                f"got {type(row).__name__}",
                path=path,
            )
        if "input" not in row:
            raise EvalError(
                f"Invalid JSONL in {path} at line {line_no}: missing required `input`",
                path=path,
            )
        rows.append(row)

    if not rows:
        raise EvalError(
            f"Eval valset is empty: {path}",
            path=path,
            suggestion="Add at least one JSONL row with `input`",
        )
    return rows


def builtin_match(actual_output: str, expected_output: str | None) -> bool:
    """Exact or substring match on ``expected_output`` when present (Architecture §6.3)."""
    if expected_output is None:
        return True
    if actual_output == expected_output:
        return True
    return expected_output in actual_output


def format_eval_result(result: EvalResult) -> str:
    """Human-readable summary for CLI stdout."""
    lines = [
        f"Eval {result.harness_name} ({result.framework}) "
        f"agent={result.agent_name}: {result.passed} passed, {result.failed} failed",
    ]
    for case in result.cases:
        status = "PASS" if case.passed else "FAIL"
        detail = f" — {case.detail}" if case.detail else ""
        lines.append(f"  [{status}] case {case.index}: {case.input!r}{detail}")
    return "\n".join(lines)


def _resolve_valset_path(harness_dir: Path, valset_ref: str) -> Path:
    path = Path(valset_ref)
    if path.is_absolute():
        return path
    return (harness_dir / path).resolve()


def _expected_output(row: Mapping[str, Any]) -> str | None:
    if "expected_output" not in row or row["expected_output"] is None:
        return None
    return str(row["expected_output"])


def _retrieval_context(row: Mapping[str, Any]) -> list[str] | None:
    value = row.get("retrieval_context")
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [str(item) for item in value]
    return [str(value)]


def _assistant_text(result: Any) -> str:
    """Extract assistant text from a Haystack ``Agent.run`` result."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, Mapping):
        last = result.get("last_message")
        text = getattr(last, "text", None) if last is not None else None
        if text:
            return str(text)
        messages = result.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                role = getattr(message, "role", None)
                role_value = getattr(role, "value", role)
                if str(role_value) == "assistant":
                    msg_text = getattr(message, "text", None)
                    if msg_text:
                        return str(msg_text)
    return ""


def _default_agent_runner(
    *,
    project_root: Path,
    harness_dir: Path,
    harness_name: str,
    agent_name: str,
    harness_models: Path | None,
) -> AgentRunner:
    merged = load_merged_agent_models(
        project_root=project_root,
        harness_dir=harness_dir,
        harness_models_path=harness_models,
        agent_name=agent_name,
    )
    router = ModelRouter(merged, project_root=project_root)
    built = build_agent_bundle(
        harness_dir,
        harness_name=harness_name,
        agent_name=agent_name,
        router=router,
    )

    def _run(user_input: str) -> str:
        openai_messages = preprocess_openai_messages(
            built.input_rewrite_template,
            build_stage_messages(user_input),
        )
        chat_messages = [
            ChatMessage.from_openai_dict_format(message)
            for message in openai_messages
        ]
        run_result = built.agent.run(messages=chat_messages)
        return _assistant_text(run_result)

    return _run


def _build_deepeval_metric(
    metric_cfg: EvalMetricConfig,
    *,
    judge_model_id: str | None,
) -> Any:
    """Instantiate a DeepEval metric class by ``type`` name."""
    import deepeval.metrics as metrics_mod

    cls = getattr(metrics_mod, metric_cfg.type, None)
    if cls is None:
        raise EvalError(
            f"Unknown DeepEval metric type {metric_cfg.type!r}",
            suggestion=(
                "Use a class name from deepeval.metrics "
                "(e.g. AnswerRelevancyMetric, GEval, TaskCompletionMetric)"
            ),
        )
    kwargs: dict[str, Any] = {"threshold": metric_cfg.threshold}
    if judge_model_id:
        kwargs["model"] = judge_model_id
    try:
        return cls(**kwargs)
    except TypeError:
        kwargs.pop("model", None)
        return cls(threshold=metric_cfg.threshold)


def _row_actual_output(
    row: Mapping[str, Any],
    agent_runner: AgentRunner | None,
) -> str:
    """Resolve actual output: captured trace field, or live agent run."""
    if agent_runner is None:
        if "actual_output" not in row:
            raise EvalError(
                "Trace/valset row missing `actual_output` and no agent runner "
                "was provided",
                suggestion="Export traces with export_haystack_trace, or omit "
                "--trace to run the agent",
            )
        return str(row["actual_output"])
    return agent_runner(str(row["input"]))


def _run_builtin_cases(
    rows: list[dict[str, Any]],
    agent_runner: AgentRunner | None,
) -> list[EvalCaseResult]:
    cases: list[EvalCaseResult] = []
    for index, row in enumerate(rows):
        user_input = str(row["input"])
        expected = _expected_output(row)
        actual = _row_actual_output(row, agent_runner)
        passed = builtin_match(actual, expected)
        detail = ""
        if not passed:
            detail = f"expected {expected!r}, got {actual!r}"
        cases.append(
            EvalCaseResult(
                index=index,
                input=user_input,
                expected_output=expected,
                actual_output=actual,
                passed=passed,
                detail=detail,
            )
        )
    return cases


def _metric_passed(metric: Any) -> bool:
    success = getattr(metric, "is_successful", None)
    if callable(success):
        try:
            return bool(success())
        except Exception:  # noqa: BLE001
            return False
    score = getattr(metric, "score", None)
    threshold = getattr(metric, "threshold", 0.5)
    if score is None:
        return False
    try:
        return float(score) >= float(threshold)
    except (TypeError, ValueError):
        return False


def _run_deepeval_cases(
    rows: list[dict[str, Any]],
    agent_runner: AgentRunner | None,
    eval_config: EvalConfig,
) -> list[EvalCaseResult]:
    require_deepeval()
    from deepeval.test_case import LLMTestCase

    if not eval_config.metrics:
        raise EvalError(
            "eval.framework is 'deepeval' but eval.metrics is empty",
            suggestion="Add at least one metric under eval.metrics, or set "
            "eval.framework: builtin",
        )

    metrics = [
        _build_deepeval_metric(metric, judge_model_id=eval_config.judge_model_id)
        for metric in eval_config.metrics
    ]

    cases: list[EvalCaseResult] = []
    for index, row in enumerate(rows):
        user_input = str(row["input"])
        expected = _expected_output(row)
        actual = _row_actual_output(row, agent_runner)
        test_case_kwargs: dict[str, Any] = {
            "input": user_input,
            "actual_output": actual,
        }
        if expected is not None:
            test_case_kwargs["expected_output"] = expected
        retrieval = _retrieval_context(row)
        if retrieval is not None:
            test_case_kwargs["retrieval_context"] = retrieval
        test_case = LLMTestCase(**test_case_kwargs)

        passed = True
        details: list[str] = []
        for metric in metrics:
            try:
                metric.measure(test_case)
                if not _metric_passed(metric):
                    passed = False
                    reason = getattr(metric, "reason", None) or (
                        f"score={getattr(metric, 'score', None)}"
                    )
                    details.append(f"{type(metric).__name__}: {reason}")
            except Exception as exc:  # noqa: BLE001 — surface metric failures
                passed = False
                details.append(f"{type(metric).__name__}: {exc}")

        cases.append(
            EvalCaseResult(
                index=index,
                input=user_input,
                expected_output=expected,
                actual_output=actual,
                passed=passed,
                detail="; ".join(details),
            )
        )
    return cases


def _resolve_trace_path(harness_dir: Path, trace_ref: str | Path) -> Path:
    path = Path(trace_ref)
    if path.is_absolute():
        return path
    candidate = (Path.cwd() / path).resolve()
    if candidate.is_file():
        return candidate
    return (harness_dir / path).resolve()


def run_eval(
    harness_name: str,
    *,
    framework: str | None = None,
    agent_name: str | None = None,
    project_root: Path | str | None = None,
    deploy: bool = False,
    agent_runner: AgentRunner | None = None,
    trace: Path | str | None = None,
    base_url: str | None = None,
) -> EvalResult:
    """Run harness eval (builtin JSONL or DeepEval) for *harness_name*.

    *framework* overrides ``eval.framework`` for one run (CLI ``--framework``).
    Pass *agent_runner* in tests to avoid building a live Haystack agent.

    When *trace* is set (CLI ``--trace``), load that JSONL and score captured
    ``actual_output`` without re-running the agent (E6-S05).

    When *base_url* is set (CLI ``--base-url``) or ``eval.base_url`` is set,
    use Mode C: HTTP black-box against a running serve (E6-S06). Empty string
    resolves to localhost + harness port. Staging/debug only.
    """
    root = Path(project_root) if project_root is not None else find_project_root()
    harness_path = resolve_harness_dir(root, harness_name, deploy=deploy)
    harness_yaml = harness_path / "harness.yaml"
    if not harness_yaml.is_file():
        raise EvalError(
            f"Harness '{harness_name}' not found at {harness_path} (missing harness.yaml)",
            path=harness_path,
            harness_name=harness_name,
            suggestion=f"Create the harness with `zaumzeug init {harness_name}`",
        )

    try:
        harness_config = load_harness(harness_yaml)
    except ConfigValidationError as exc:
        raise EvalError(
            str(exc),
            path=exc.path,
            harness_name=harness_name,
            suggestion=f"Fix harness.yaml at {harness_yaml}",
        ) from exc

    if harness_config.eval is None:
        raise EvalError(
            MISSING_EVAL_MESSAGE,
            path=harness_yaml,
            harness_name=harness_name,
            suggestion="Add an `eval:` block with framework and valset",
        )

    eval_config = harness_config.eval
    resolved_framework = resolve_eval_framework(
        eval_config,
        framework_override=framework,
    )
    mode_c_base_url = resolve_eval_base_url(
        cli_base_url=base_url,
        eval_config=eval_config,
        harness_config=harness_config,
    )

    if mode_c_base_url is not None and trace is not None:
        raise EvalError(
            "Cannot combine Mode C (--base-url / eval.base_url) with --trace",
            harness_name=harness_name,
            suggestion="Use --trace to score a captured turn, or --base-url "
            "to black-box a running serve — not both",
        )

    # Fail fast on missing [eval] extra before loading agents / valset (AC-1).
    if resolved_framework == "deepeval":
        try:
            require_deepeval()
        except DeepEvalMissingError as exc:
            raise EvalError(
                str(exc),
                harness_name=harness_name,
                suggestion='pip install "zaumzeug[eval]"',
            ) from exc

    try:
        load_workflow(harness_path)
        entry = resolve_serve_entry(harness_path, harness_name=harness_name)
    except (ConfigValidationError, AgentResolutionError) as exc:
        raise EvalError(
            str(exc),
            harness_name=harness_name,
            suggestion=f"Fix workflow/agents under {harness_path}",
        ) from exc

    resolved_agent = (agent_name or entry.agent_name).strip()

    score_from_trace = trace is not None
    if score_from_trace:
        trace_path = _resolve_trace_path(harness_path, trace)
        try:
            rows = load_trace_jsonl(trace_path)
        except TraceError as exc:
            raise EvalError(
                str(exc),
                path=exc.path,
                harness_name=harness_name,
                suggestion=exc.suggestion,
            ) from exc
        runner: AgentRunner | None = None
    else:
        valset_path = _resolve_valset_path(harness_path, eval_config.valset)
        rows = load_valset_jsonl(valset_path)

        runner = agent_runner
        if runner is None and mode_c_base_url is not None:
            # Mode C: OpenAI ``model`` is the harness/pipeline identity.
            runner = _http_agent_runner(
                base_url=mode_c_base_url,
                model=harness_name,
            )
        elif runner is None:
            harness_models: Path | None = None
            if harness_config.models:
                harness_models = Path(harness_config.models)
            try:
                runner = _default_agent_runner(
                    project_root=root,
                    harness_dir=harness_path,
                    harness_name=harness_name,
                    agent_name=resolved_agent,
                    harness_models=harness_models,
                )
            except (
                AgentResolutionError,
                RuntimeFactoryError,
                ModelRouterError,
                ConfigValidationError,
            ) as exc:
                raise EvalError(
                    f"Harness '{harness_name}' agent '{resolved_agent}': {exc}",
                    harness_name=harness_name,
                ) from exc

    if resolved_framework == "builtin":
        cases = _run_builtin_cases(rows, runner)
    else:
        cases = _run_deepeval_cases(rows, runner, eval_config)

    passed = sum(1 for case in cases if case.passed)
    failed = len(cases) - passed
    return EvalResult(
        harness_name=harness_name,
        harness_dir=harness_path,
        framework=resolved_framework,
        agent_name=resolved_agent,
        cases=cases,
        passed=passed,
        failed=failed,
    )
