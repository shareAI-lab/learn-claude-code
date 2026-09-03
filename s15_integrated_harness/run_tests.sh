#!/bin/sh
# Run the full s15 integrated harness test suite: pytest tests/.
# Portable POSIX sh; no bashisms.
set -eu

# Always run from the directory containing this script (the s15 lesson root).
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    PY=python
fi

if ! "$PY" -m pytest --version >/dev/null 2>&1; then
    echo "error: pytest is required (install with: pip install pytest)" >&2
    exit 1
fi

exec "$PY" -m pytest tests/ -v
