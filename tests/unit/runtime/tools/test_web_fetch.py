# Story: E3-S03 / E3.3
"""E3-S03 — Builtin tool: ``web_fetch``."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
import respx

from zaumzeug.runtime.tools.catalog import (
    available_builtin_tool_ids,
    create_builtin_tool,
)
from zaumzeug.runtime.tools.web_fetch import (
    FETCH_TIMEOUT_S,
    MAX_RESPONSE_BYTES,
    WebFetch,
    WebFetchError,
    fetch_url,
    is_public_host,
    validate_fetch_url,
)


def test_e3_s03_ac1_catalog_lists_web_fetch_phase1() -> None:
    """AC-1: Phase 1 SDK catalog ships ``web_fetch``."""
    tool_ids = available_builtin_tool_ids(phase=1)
    assert "web_fetch" in tool_ids

    tool = create_builtin_tool("web_fetch")
    assert tool.name == "web_fetch"


def test_e3_s03_ac2_https_only_timeout_and_size_cap() -> None:
    """AC-2: HTTPS only, 30s timeout, and 1 MB response cap."""
    assert FETCH_TIMEOUT_S == 30.0
    assert MAX_RESPONSE_BYTES == 1_048_576

    with pytest.raises(WebFetchError, match="HTTPS only"):
        validate_fetch_url("http://example.com/page")

    with patch("zaumzeug.runtime.tools.web_fetch.is_public_host", return_value=True):
        with respx.mock:
            route = respx.get("https://example.com/page").mock(
                return_value=httpx.Response(200, text="hello")
            )
            assert fetch_url("https://example.com/page") == "hello"
            assert route.calls[0].request.url == httpx.URL("https://example.com/page")

    oversized = b"x" * (MAX_RESPONSE_BYTES + 1)
    with patch("zaumzeug.runtime.tools.web_fetch.is_public_host", return_value=True):
        with respx.mock:
            respx.get("https://example.com/large").mock(
                return_value=httpx.Response(200, content=oversized)
            )
            with pytest.raises(WebFetchError, match="byte cap"):
                fetch_url("https://example.com/large")

    captured: dict[str, float] = {}

    with patch("zaumzeug.runtime.tools.web_fetch.is_public_host", return_value=True):
        with patch("zaumzeug.runtime.tools.web_fetch.httpx.Client") as client_cls:
            client = client_cls.return_value.__enter__.return_value
            stream_ctx = client.stream.return_value.__enter__.return_value
            stream_ctx.iter_bytes.return_value = [b"ok"]
            stream_ctx.raise_for_status.return_value = None
            stream_ctx.encoding = "utf-8"
            client_cls.side_effect = lambda **kwargs: _TimeoutClient(kwargs, captured)

            fetch_url("https://example.com/timed")

    assert captured["timeout"] == FETCH_TIMEOUT_S


class _TimeoutClient:
    def __init__(self, kwargs: dict, captured: dict[str, float]) -> None:
        if "timeout" in kwargs:
            captured["timeout"] = float(kwargs["timeout"])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def stream(self, *args, **kwargs):
        return _Stream()

    def close(self) -> None:
        return None


class _Stream:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    @property
    def encoding(self) -> str:
        return "utf-8"

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self):
        return iter([b"ok"])


def test_e3_s03_ac3_ssrf_blocks_private_ips() -> None:
    """AC-3: SSRF guard blocks private and link-local hosts."""
    assert is_public_host("example.com") is True

    with patch(
        "zaumzeug.runtime.tools.web_fetch.socket.gethostbyname",
        return_value="127.0.0.1",
    ):
        assert is_public_host("evil.example") is False
        with pytest.raises(WebFetchError, match="blocked private"):
            validate_fetch_url("https://evil.example/secret")

    with pytest.raises(WebFetchError, match="blocked private"):
        validate_fetch_url("https://127.0.0.1/local")

    with pytest.raises(WebFetchError, match="blocked private"):
        validate_fetch_url("https://10.0.0.5/internal")

    component = WebFetch()
    with pytest.raises(WebFetchError, match="blocked private"):
        component.run(url="https://192.168.1.1/status")
