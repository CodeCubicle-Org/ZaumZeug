"""ZaumZeug CLI entry point."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable


# Phase 1 commands and Phase 2+ stubs listed for help discovery.
_COMMANDS: tuple[str, ...] = (
    "init",
    "doctor",
    "serve",
    "run",
    "compile",
    "deploy",
    "eval",
    "mcp",
    "acp",
)


def _stub_command(name: str) -> Callable[[argparse.Namespace], int]:
    def _run(_args: argparse.Namespace) -> int:
        print(f"zaumzeug {name}: not implemented yet", file=sys.stderr)
        return 0

    return _run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zaumzeug",
        description="ZaumZeug - harness SDK for multi-agent AI workflows",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name in _COMMANDS:
        cmd = sub.add_parser(name, help=f"{name} command (stub)")
        cmd.set_defaults(_handler=_stub_command(name))

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args._handler
    raise SystemExit(handler(args))


if __name__ == "__main__":
    main()
