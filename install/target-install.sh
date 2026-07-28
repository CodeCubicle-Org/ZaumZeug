#!/usr/bin/env bash
# Thin POSIX wrapper for target_install.py (E5-S01 bundle / E5-S09b).
# Invokes the sibling target_install.py so this works both under install/
# and when copied into deploy/<name>/.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${HERE}/target_install.py"

_python_ok() {
  local exe="$1"
  shift
  "$exe" "$@" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1
}

for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && _python_ok "$cand"; then
    exec "$cand" "$SCRIPT" "$@"
  fi
done

if command -v py >/dev/null 2>&1 && _python_ok py -3; then
  exec py -3 "$SCRIPT" "$@"
fi

echo "error: Python 3.11+ is required but no working python3/python/py was found on PATH." >&2
exit 1
