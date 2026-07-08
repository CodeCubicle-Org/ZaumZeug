"""ZaumZeug CLI entry point."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from zaumzeug.doctor import run_doctor
from zaumzeug.logging import configure_logging
from zaumzeug.serve import format_dry_run, validate_serve
from zaumzeug.serve.dry_run import dry_run_to_json


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


def _doctor_command(args: argparse.Namespace) -> int:
    report = run_doctor(harness_name=args.harness_name, deploy=args.deploy)
    if args.json:
        print(report.to_json())
    else:
        print(report.format(verbose=args.verbose))
    return report.exit_code


def _compile_command(args: argparse.Namespace) -> int:
    configure_logging(verbose=args.verbose)
    print("zaumzeug compile: not implemented yet", file=sys.stderr)
    return 0


def _serve_command(args: argparse.Namespace) -> int:
    configure_logging(verbose=args.verbose)
    if args.dry_run:
        result = validate_serve(args.harness_name, deploy=args.deploy)
        if args.json:
            print(dry_run_to_json(result))
        else:
            print(format_dry_run(result))
        return result.exit_code
    print("zaumzeug serve: not implemented yet", file=sys.stderr)
    return 0


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

    doctor = sub.add_parser(
        "doctor",
        help="preflight environment and harness config",
    )
    doctor.add_argument(
        "harness_name",
        nargs="?",
        default=None,
        help="harness name under usr-harnesses/ (default: scan all)",
    )
    doctor.add_argument(
        "--deploy",
        action="store_true",
        help="validate deploy bundle under deploy/ (or HARNESS_ROOT=deploy)",
    )
    doctor.add_argument(
        "--verbose",
        action="store_true",
        help="show passing checks",
    )
    doctor.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON report",
    )
    doctor.set_defaults(_handler=_doctor_command)

    serve = sub.add_parser("serve", help="start Hayhooks for a harness")
    serve.add_argument(
        "harness_name",
        help="harness name under usr-harnesses/ (or deploy/ with --deploy)",
    )
    serve.add_argument(
        "--dry-run",
        action="store_true",
        help="validate config and resolved paths without starting Hayhooks",
    )
    serve.add_argument(
        "--deploy",
        action="store_true",
        help="load harness from deploy/<name>/ (or HARNESS_ROOT=deploy)",
    )
    serve.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON dry-run report",
    )
    serve.add_argument(
        "--verbose",
        action="store_true",
        help="enable SDK and Haystack debug logging",
    )
    serve.set_defaults(_handler=_serve_command)

    for name in _COMMANDS:
        if name in {"doctor", "serve", "compile"}:
            continue
        cmd = sub.add_parser(name, help=f"{name} command (stub)")
        cmd.set_defaults(_handler=_stub_command(name))

    compile_cmd = sub.add_parser("compile", help="compile harness artifacts (stub)")
    compile_cmd.add_argument(
        "--verbose",
        action="store_true",
        help="enable SDK and Haystack debug logging",
    )
    compile_cmd.set_defaults(_handler=_compile_command)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args._handler
    raise SystemExit(handler(args))


if __name__ == "__main__":
    main()
