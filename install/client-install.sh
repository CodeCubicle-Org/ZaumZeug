#!/usr/bin/env bash
# Thin POSIX wrapper for install/client_install.py (E1-S02 / E1.2).
# All install logic lives in the Python script; this file only finds Python and forwards args.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/install/client_install.py"

_python_ok() {
  # $1 = executable; remaining args are prefix flags (e.g. py -3).
  local exe="$1"
  shift
  "$exe" "$@" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1
}

# Prefer Windows py launcher when present (avoids Microsoft Store python stubs).
if command -v py >/dev/null 2>&1 && _python_ok py -3; then
  exec py -3 "$SCRIPT" "$@"
fi

for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && _python_ok "$cand"; then
    exec "$cand" "$SCRIPT" "$@"
  fi
done

echo "error: Python 3.11+ is required but no working python3/python/py was found on PATH." >&2
exit 1
