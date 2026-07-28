"""Optional DeepEval bridge (requires ``pip install "zaumzeug[eval]"``).

Importing this package must not require ``deepeval``. Call
:func:`require_deepeval` only on paths that need DeepEval (E6-S01).
The ``zaumzeug eval`` CLI lives in :mod:`zaumzeug.eval.runner` (E6-S02).
Trace export / ``--trace`` scoring lives in :mod:`zaumzeug.eval.trace` (E6-S05).
"""

from __future__ import annotations

from types import ModuleType

DEEPEVAL_INSTALL_HINT = 'pip install "zaumzeug[eval]"'

DEEPEVAL_MISSING_MESSAGE = (
    "Error: eval.framework is 'deepeval' but deepeval is not installed.\n"
    f"Install with: {DEEPEVAL_INSTALL_HINT}\n"
    "Or set eval.framework: builtin for JSONL checks without DeepEval."
)


class DeepEvalMissingError(ImportError):
    """Raised when DeepEval is required but the ``[eval]`` extra is missing."""

    def __init__(self, message: str = DEEPEVAL_MISSING_MESSAGE) -> None:
        super().__init__(message)
        self.suggestion = DEEPEVAL_INSTALL_HINT


def is_deepeval_available() -> bool:
    """Return True when the optional ``deepeval`` package can be imported."""
    try:
        import deepeval  # noqa: F401
    except ImportError:
        return False
    return True


def require_deepeval() -> ModuleType:
    """Import ``deepeval`` or raise a friendly ``[eval]`` install hint."""
    try:
        import deepeval
    except ImportError as exc:
        raise DeepEvalMissingError() from exc
    return deepeval


__all__ = [
    "DEEPEVAL_INSTALL_HINT",
    "DEEPEVAL_MISSING_MESSAGE",
    "DeepEvalMissingError",
    "is_deepeval_available",
    "require_deepeval",
]
