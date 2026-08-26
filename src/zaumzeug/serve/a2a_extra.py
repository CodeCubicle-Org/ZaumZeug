"""Optional Hayhooks A2A extra (E8-S04).

Core ``zaumzeug`` / ``hayhooks`` installs do not include the A2A SDK. Enable
agent-card hosting with ``serve.a2a: true`` (or ``serve.a2a.enabled: true``)
after ``pip install "hayhooks[a2a]"``, then run ``zaumzeug a2a <name>``.
"""

from __future__ import annotations

A2A_INSTALL_HINT = 'pip install "hayhooks[a2a]"'

A2A_MISSING_MESSAGE = (
    "Error: serve.a2a is enabled but Hayhooks A2A support is not installed.\n"
    f"Install with: {A2A_INSTALL_HINT}\n"
    "Then restart `zaumzeug a2a` — the agent card is at "
    "/{harness}/.well-known/agent-card.json on the A2A port (default 1418)."
)


class A2aMissingError(ImportError):
    """Raised when A2A hosting is requested but ``hayhooks[a2a]`` is missing."""

    def __init__(self, message: str = A2A_MISSING_MESSAGE) -> None:
        super().__init__(message)
        self.suggestion = A2A_INSTALL_HINT


def is_a2a_available() -> bool:
    """Return True when Hayhooks can build the A2A Starlette app."""
    try:
        from hayhooks.server.utils.a2a_utils import a2a_import
    except ImportError:
        return False
    try:
        a2a_import.check()
    except Exception:
        return False
    return True


def require_a2a() -> None:
    """Raise :class:`A2aMissingError` when the optional extra is missing."""
    if not is_a2a_available():
        raise A2aMissingError()
