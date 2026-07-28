#!/usr/bin/env python3
"""Target runtime install for a ZaumZeug deploy bundle (Architecture §10.7).

Full install behaviour (venv, pip install zaumzeug, doctor --deploy, --verify)
lands in E5-S09. This stub ships inside each ``deploy/<name>/`` bundle (E5-S01)
so the folder is self-describing when copied alone.

Usage (from the deploy bundle directory)::

    python target_install.py
    python target_install.py --deploy-dir /path/to/deploy/my_agent
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

__all__ = ["main", "preflight_bundle"]


def preflight_bundle(deploy_dir: Path) -> list[str]:
    """Return human-readable errors if the bundle is incomplete."""
    errors: list[str] = []
    if not (deploy_dir / "harness.yaml").is_file():
        errors.append(f"Missing harness.yaml in {deploy_dir}")
    if not (deploy_dir / "manifest.json").is_file():
        errors.append(f"Missing manifest.json in {deploy_dir}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="target_install",
        description=(
            "Prepare a ZaumZeug deploy bundle on the target host "
            "(full install: E5-S09)."
        ),
    )
    parser.add_argument(
        "--deploy-dir",
        type=Path,
        default=None,
        help="Deploy bundle directory (default: current working directory)",
    )
    parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="Reserved for E5-S09 (optional .venv creation)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Reserved for E5-S09c (doctor --deploy + serve --dry-run)",
    )
    args = parser.parse_args(argv)

    deploy_dir = (args.deploy_dir or Path.cwd()).resolve()
    errors = preflight_bundle(deploy_dir)
    if errors:
        for message in errors:
            print(f"error: {message}", file=sys.stderr)
        print(
            "Suggestion: run this script from deploy/<name>/ "
            "(must contain harness.yaml and manifest.json)",
            file=sys.stderr,
        )
        return 1

    harness_name = deploy_dir.name
    print(f"Deploy bundle OK: {deploy_dir}")
    print(
        "Note: full runtime install (venv + pip install zaumzeug) lands in E5-S09."
    )
    if args.skip_venv or args.verify:
        print("Flags --skip-venv / --verify are reserved for E5-S09 / E5-S09c.")
    print()
    print("Next steps:")
    print("  1. Ensure Python 3.11+ is on PATH")
    print(
        "  2. pip install zaumzeug   # runtime only — no [dev]/[eval]; "
        "no DSPy, GEPA, or DeepEval on the target"
    )
    print("  3. Create .env from .env.example if present (never overwrite .env)")
    print(f"  4. zaumzeug doctor {harness_name} --deploy")
    print(f"  5. zaumzeug serve {harness_name} --deploy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
