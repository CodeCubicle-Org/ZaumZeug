"""DeepEval production ``@observe`` (Mode B) — opt-in Confident AI sync (E8-S06).

Wraps Haystack ``Agent.run`` with DeepEval ``@observe`` when
``eval.confident_ai.enabled: true``. Default is **off** (PRD NG2) — production
serve never pulls DeepEval unless the harness explicitly opts in and the
``[eval]`` extra is installed on that host.

Requires ``pip install "zaumzeug[eval]"`` and ``deepeval login`` (or
``CONFIDENT_API_KEY``) when enabled. Observe failures never fail the user request.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from zaumzeug.eval import is_deepeval_available, require_deepeval
from zaumzeug.eval.ratchet import user_input_from_run_args
from zaumzeug.logging import get_logger

__all__ = [
    "CONFIDENT_API_KEY_ENV",
    "ProductionObserveHook",
    "confident_ai_credentials_present",
    "install_production_observe_hook",
    "observe_enabled",
]

CONFIDENT_API_KEY_ENV = "CONFIDENT_API_KEY"
_HOOK_MARKER = "_zaumzeug_production_observe_hook"

_logger = get_logger("eval.observe")


def observe_enabled(eval_config: Any | None = None) -> bool:
    """Return True when production DeepEval ``@observe`` should run.

    Gate is ``eval.confident_ai.enabled`` only. Default is off (opt-in).
    """
    if eval_config is None:
        return False
    confident = getattr(eval_config, "confident_ai", None)
    if confident is None:
        return False
    return bool(getattr(confident, "enabled", False))


def confident_ai_credentials_present(
    *,
    env: Mapping[str, str] | None = None,
    dotenv: Mapping[str, str] | None = None,
    project_root: Path | str | None = None,
) -> bool:
    """Return True when a Confident AI API key is available without printing it.

    Checks ``CONFIDENT_API_KEY`` in the process env, optional ``.env`` map /
    project ``.env``, and DeepEval's stored login key when the ``[eval]`` extra
    is installed. Never returns or logs the key value.
    """
    environ = env if env is not None else os.environ
    if str(environ.get(CONFIDENT_API_KEY_ENV, "")).strip():
        return True
    merged_dotenv = dict(dotenv or {})
    if project_root is not None:
        merged_dotenv.update(_read_dotenv_keys(Path(project_root) / ".env"))
    if str(merged_dotenv.get(CONFIDENT_API_KEY_ENV, "")).strip():
        return True
    if not is_deepeval_available():
        return False
    return _deepeval_stored_key_present()


def _read_dotenv_keys(path: Path) -> dict[str, str]:
    """Minimal ``KEY=VALUE`` parser for credential presence checks."""
    if not path.is_file():
        return {}
    result: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key:
                result[key] = value
    except OSError:
        return {}
    return result


def _deepeval_stored_key_present() -> bool:
    """True when ``deepeval login`` has stored a key (value never returned)."""
    try:
        from deepeval.key_handler import KEY_FILE_HANDLER, KeyValues
    except ImportError:
        return False
    try:
        # Prefer Confident AI key; fall back to generic API_KEY if present.
        for attr in ("CONFIDENT_API_KEY", "API_KEY"):
            key_enum = getattr(KeyValues, attr, None)
            if key_enum is None:
                continue
            raw = KEY_FILE_HANDLER.fetch_data(key_enum)
            if raw is not None and str(raw).strip():
                return True
    except Exception:  # noqa: BLE001 — treat any read failure as missing
        return False
    return False


def _assistant_text(result: Any) -> str:
    if not isinstance(result, Mapping):
        return ""
    last = result.get("last_message")
    text = getattr(last, "text", None) if last is not None else None
    if text:
        return str(text)
    if isinstance(last, Mapping):
        content = last.get("content") or last.get("text")
        if content:
            return str(content)
    return ""


def _load_observe_api() -> tuple[Callable[..., Any], Callable[..., Any], Any]:
    """Import DeepEval observe helpers (lazy; requires ``[eval]`` extra)."""
    require_deepeval()
    from deepeval.test_case import LLMTestCase
    from deepeval.tracing import observe, update_current_span

    return observe, update_current_span, LLMTestCase


class ProductionObserveHook:
    """Wrap ``Agent.run`` with DeepEval ``@observe`` for Confident AI sync."""

    def __init__(self, *, agent: str | None = None) -> None:
        self.agent = agent
        self.observe_errors: list[str] = []
        self.installed = False

    def install(self, agent: Any) -> Any:
        """Wrap ``agent.run`` once with ``@observe``. Returns *agent*."""
        original = getattr(agent, "run", None)
        if original is None or not callable(original):
            raise TypeError(
                "Cannot install production observe hook: agent has no callable run()"
            )
        if getattr(original, _HOOK_MARKER, False) is self:
            return agent

        observe, update_current_span, LLMTestCase = _load_observe_api()
        hook = self
        span_name = hook.agent or "zaumzeug.agent.run"

        @observe(name=span_name)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            result = original(*args, **kwargs)
            hook._update_span_quietly(
                update_current_span,
                LLMTestCase,
                result,
                *args,
                **kwargs,
            )
            return result

        setattr(wrapped, _HOOK_MARKER, self)
        agent.run = wrapped
        self.installed = True
        return agent

    def _update_span_quietly(
        self,
        update_current_span: Callable[..., Any],
        LLMTestCase: Any,
        result: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        try:
            user_input = user_input_from_run_args(*args, **kwargs)
            actual = _assistant_text(result)
            update_current_span(
                test_case=LLMTestCase(
                    input=user_input,
                    actual_output=actual,
                )
            )
        except Exception as exc:  # noqa: BLE001 — never fail the live request
            message = f"DeepEval observe span update failed: {exc}"
            self.observe_errors.append(message)
            _logger.warning(message)


def install_production_observe_hook(
    agent: Any,
    *,
    agent_name: str | None = None,
) -> ProductionObserveHook:
    """Install a :class:`ProductionObserveHook` on *agent* and return the hook."""
    hook = ProductionObserveHook(agent=agent_name)
    hook.install(agent)
    return hook
