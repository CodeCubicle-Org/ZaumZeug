"""Optional Hayhooks Chainlit extra (E7-S04).

Core ``zaumzeug`` / ``hayhooks`` installs do not include Chainlit. Enable the
embedded UI with ``serve.hayhooks.chainlit: true`` after
``pip install "hayhooks[chainlit]"``.
"""

from __future__ import annotations

CHAINLIT_INSTALL_HINT = 'pip install "hayhooks[chainlit]"'

CHAINLIT_MISSING_MESSAGE = (
    "Error: serve.hayhooks.chainlit is true but Chainlit is not installed.\n"
    f"Install with: {CHAINLIT_INSTALL_HINT}\n"
    "Then restart `zaumzeug serve` — the GUI is at /chat on the same port as REST."
)


class ChainlitMissingError(ImportError):
    """Raised when Chainlit UI is requested but ``hayhooks[chainlit]`` is missing."""

    def __init__(self, message: str = CHAINLIT_MISSING_MESSAGE) -> None:
        super().__init__(message)
        self.suggestion = CHAINLIT_INSTALL_HINT


def is_chainlit_available() -> bool:
    """Return True when Hayhooks can mount the embedded Chainlit UI."""
    try:
        from hayhooks.server.utils.chainlit_utils import is_chainlit_available as _check
    except ImportError:
        try:
            import chainlit  # noqa: F401
        except ImportError:
            return False
        return True
    return bool(_check())


def require_chainlit() -> None:
    """Raise :class:`ChainlitMissingError` when the optional extra is missing."""
    if not is_chainlit_available():
        raise ChainlitMissingError()
