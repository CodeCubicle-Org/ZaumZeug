"""Builtin ``web_fetch`` tool — HTTPS GET with SSRF guard (E3-S03)."""

from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

import httpx
from haystack import component
from haystack.tools import ComponentTool

FETCH_TIMEOUT_S = 30.0
MAX_RESPONSE_BYTES = 1_048_576


class WebFetchError(ValueError):
    """Raised when a URL cannot be fetched safely."""


def _resolve_host_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return ipaddress.ip_address(socket.gethostbyname(host))


def is_public_host(host: str) -> bool:
    """Return True when *host* resolves to a non-private, routable address."""
    ip = _resolve_host_ip(host)
    return not (ip.is_private or ip.is_loopback or ip.is_link_local)


def validate_fetch_url(url: str) -> None:
    """Reject non-HTTPS URLs and hosts that fail the SSRF guard."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise WebFetchError(f"web_fetch supports HTTPS only (got scheme {parsed.scheme!r})")
    if not parsed.hostname:
        raise WebFetchError(f"web_fetch requires a hostname in URL {url!r}")
    if not is_public_host(parsed.hostname):
        raise WebFetchError(
            f"web_fetch blocked private or link-local host {parsed.hostname!r}"
        )


def _validate_request_url(request: httpx.Request) -> None:
    validate_fetch_url(str(request.url))


def fetch_url(
    url: str,
    *,
    timeout: float = FETCH_TIMEOUT_S,
    max_bytes: int = MAX_RESPONSE_BYTES,
    client: httpx.Client | None = None,
) -> str:
    """Fetch *url* over HTTPS and return decoded response text."""
    validate_fetch_url(url)

    owns_client = client is None
    http = client or httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        event_hooks={"request": [_validate_request_url]},
    )
    chunks: list[bytes] = []
    encoding = "utf-8"
    try:
        with http.stream("GET", url) as response:
            response.raise_for_status()
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise WebFetchError(
                        f"web_fetch response exceeds {max_bytes} byte cap for {url!r}"
                    )
                chunks.append(chunk)
            encoding = response.encoding or "utf-8"
    finally:
        if owns_client:
            http.close()

    body = b"".join(chunks)
    return body.decode(encoding, errors="replace")


@component
class WebFetch:
    """Haystack component that fetches HTTPS URL content for agent context."""

    def __init__(
        self,
        *,
        timeout: float = FETCH_TIMEOUT_S,
        max_bytes: int = MAX_RESPONSE_BYTES,
        client: httpx.Client | None = None,
    ) -> None:
        self._timeout = timeout
        self._max_bytes = max_bytes
        self._client = client

    @component.output_types(content=str)
    def run(self, url: str) -> dict[str, str]:
        content = fetch_url(
            url,
            timeout=self._timeout,
            max_bytes=self._max_bytes,
            client=self._client,
        )
        return {"content": content}


def web_fetch_tool(
    *,
    timeout: float = FETCH_TIMEOUT_S,
    max_bytes: int = MAX_RESPONSE_BYTES,
    client: httpx.Client | None = None,
) -> ComponentTool:
    """Return a Haystack ``ComponentTool`` for the builtin ``web_fetch`` id."""
    return ComponentTool(
        component=WebFetch(timeout=timeout, max_bytes=max_bytes, client=client),
        name="web_fetch",
        description=(
            "Fetch the text content of an HTTPS URL for research and reference. "
            "Only public HTTPS endpoints are allowed."
        ),
    )


def build_web_fetch_tool(**kwargs: Any) -> ComponentTool:
    """Catalog factory entry for ``web_fetch``."""
    return web_fetch_tool(**kwargs)
