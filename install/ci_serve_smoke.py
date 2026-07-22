#!/usr/bin/env python3
"""CI mock-serve smoke (E1-S07 / E1.7).

Starts ``zaumzeug serve <harness>`` via the CLI on an ephemeral localhost port,
probes ``GET /v1/models``, then terminates the process. No live API keys.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

DEFAULT_HARNESS = "example"
DEFAULT_TIMEOUT_S = 60.0
POLL_INTERVAL_S = 0.5


def free_localhost_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def discover_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ci_serve_smoke.py",
        description=(
            "Start zaumzeug serve on an ephemeral localhost port, "
            "probe GET /v1/models, then stop the server (mock CI smoke)."
        ),
    )
    parser.add_argument(
        "harness_name",
        nargs="?",
        default=DEFAULT_HARNESS,
        help=f"harness under usr-harnesses/ (default: {DEFAULT_HARNESS})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        metavar="SECONDS",
        help=f"seconds to wait for /v1/models (default: {DEFAULT_TIMEOUT_S:g})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="N",
        help="bind port (default: OS-assigned ephemeral free port)",
    )
    return parser.parse_args(argv)


def _terminate(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def run_smoke(
    harness_name: str,
    *,
    port: int | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    project_root: Path | None = None,
    python: str | None = None,
) -> int:
    """Start CLI serve, probe models endpoint, tear down. Exit 0 on success."""
    root = project_root or discover_project_root()
    bind_port = free_localhost_port() if port is None else port
    py = python or sys.executable
    cmd = [
        py,
        "-m",
        "zaumzeug",
        "serve",
        harness_name,
        "--port",
        str(bind_port),
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{bind_port}"
    models_url = f"{base}/v1/models"
    deadline = time.monotonic() + timeout_s
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                out = proc.stdout.read() if proc.stdout else ""
                print(
                    f"serve exited early (code {proc.returncode}) before ready:\n{out}",
                    file=sys.stderr,
                )
                return 1
            try:
                response = httpx.get(models_url, timeout=1.0)
            except (httpx.HTTPError, OSError):
                time.sleep(POLL_INTERVAL_S)
                continue
            if response.status_code == 200:
                print(f"OK: {models_url} -> {response.status_code}")
                print(f"  harness={harness_name} port={bind_port} (mock CI smoke)")
                return 0
            time.sleep(POLL_INTERVAL_S)
        print(
            f"timeout after {timeout_s:g}s waiting for {models_url}",
            file=sys.stderr,
        )
        return 1
    finally:
        _terminate(proc)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_smoke(
        args.harness_name,
        port=args.port,
        timeout_s=args.timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
