#!/usr/bin/env bash
# Dev environment bootstrap for learn-claude-code.
# Creates a local .venv, installs requirements.txt, and seeds .env from
# .env.example. Safe to re-run -- existing venv and .env are preserved.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MIN_PY_MAJOR=3
MIN_PY_MINOR=10

say() { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

# 1. Check Python
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  die "'$PYTHON_BIN' not found. Install Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+ or set PYTHON_BIN."
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
say "Using $PYTHON_BIN ($PY_VERSION)"

"$PYTHON_BIN" - <<PY || die "Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+ required (found $PY_VERSION)."
import sys
sys.exit(0 if sys.version_info >= (${MIN_PY_MAJOR}, ${MIN_PY_MINOR}) else 1)
PY

# 2. Create venv
if [ ! -d "$VENV_DIR" ]; then
  say "Creating virtualenv at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  say "Reusing virtualenv at $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 3. Configure Instacart CodeArtifact (skip silently if `isc` isn't installed)
if command -v isc >/dev/null 2>&1; then
  say "Configuring Instacart CodeArtifact (isc codeartifact configure)"
  isc codeartifact configure
else
  warn "'isc' not found; skipping CodeArtifact configure (non-Instacart users can ignore)."
fi

# 4. Install deps
say "Upgrading pip"
python -m pip install --upgrade pip >/dev/null

say "Installing requirements.txt"
python -m pip install -r requirements.txt

# 5. Seed .env
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    say "Creating .env from .env.example"
    cp .env.example .env
    warn "Edit .env and set your API key + MODEL_ID before running the agents."
  else
    warn "No .env.example found; skipping .env creation."
  fi
else
  say ".env already exists (leaving as-is)"
fi

# 6. Quick import sanity check
say "Verifying imports"
python - <<'PY'
import importlib.util, sys
missing = [m for m in ("openai", "dotenv", "yaml") if not importlib.util.find_spec(m)]
if missing:
    sys.exit(f"Missing modules after install: {missing}")
print("  openai, python-dotenv, pyyaml OK")
PY

# Pick the right activate script for the user's shell.
USER_SHELL="$(basename "${SHELL:-bash}")"
case "$USER_SHELL" in
  fish)     ACTIVATE_CMD="source $VENV_DIR/bin/activate.fish" ;;
  csh|tcsh) ACTIVATE_CMD="source $VENV_DIR/bin/activate.csh" ;;
  *)        ACTIVATE_CMD="source $VENV_DIR/bin/activate" ;;
esac

cat <<EOF

Done. Activate the venv and try an agent:

  $ACTIVATE_CMD
  # edit .env to set OPENAI_API_KEY, OPENAI_BASE_URL (optional), MODEL_ID
  python agents/s01_agent_loop.py

EOF
