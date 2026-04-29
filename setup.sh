#!/usr/bin/env bash
# Dev environment bootstrap for learn-claude-code.
# Seeds .env, pins Python via .python-version (pyenv), creates a local .venv,
# and installs requirements.txt. Safe to re-run -- existing files are preserved.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

VENV_DIR="${VENV_DIR:-.venv}"
MIN_PY_MAJOR=3
MIN_PY_MINOR=10

say() { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

# 1. Seed .env first so users can start editing while deps install
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

# 2. Pick Python interpreter.
#    If .python-version exists and pyenv is available, resolve through pyenv
#    so the user doesn't have to switch manually. Otherwise fall back to
#    $PYTHON_BIN (default: python3).
PINNED_PY=""
if [ -f .python-version ]; then
  PINNED_PY="$(tr -d '[:space:]' < .python-version)"
fi

if [ -n "$PINNED_PY" ] && command -v pyenv >/dev/null 2>&1; then
  # Capture once: piping into `grep -q` can return SIGPIPE (141) under pipefail.
  PYENV_VERSIONS="$(pyenv versions --bare)"
  if ! grep -qx "$PINNED_PY" <<<"$PYENV_VERSIONS" \
     && ! grep -q "^${PINNED_PY}\." <<<"$PYENV_VERSIONS"; then
    warn "pyenv: Python $PINNED_PY not installed. Run: pyenv install $PINNED_PY"
    die "Install the pinned Python, then re-run ./setup.sh"
  fi
  PYTHON_BIN="$(pyenv which python 2>/dev/null || true)"
  [ -n "$PYTHON_BIN" ] || die "pyenv could not resolve python for version $PINNED_PY"
  say "Using pyenv Python $PINNED_PY ($PYTHON_BIN)"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    die "'$PYTHON_BIN' not found. Install Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+ (or install pyenv + run: pyenv install $PINNED_PY)."
  fi
  if [ -n "$PINNED_PY" ]; then
    warn "pyenv not installed; using system $PYTHON_BIN (.python-version pins $PINNED_PY)."
  fi
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
say "Python interpreter: $PYTHON_BIN ($PY_VERSION)"

"$PYTHON_BIN" - <<PY || die "Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+ required (found $PY_VERSION)."
import sys
sys.exit(0 if sys.version_info >= (${MIN_PY_MAJOR}, ${MIN_PY_MINOR}) else 1)
PY

# 3. Create venv
if [ ! -d "$VENV_DIR" ]; then
  say "Creating virtualenv at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  say "Reusing virtualenv at $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 4. Configure Instacart CodeArtifact (skip silently if `isc` isn't installed)
if command -v isc >/dev/null 2>&1; then
  say "Configuring Instacart CodeArtifact (isc codeartifact configure)"
  isc codeartifact configure
else
  warn "'isc' not found; skipping CodeArtifact configure (non-Instacart users can ignore)."
fi

# 5. Install deps
say "Upgrading pip"
python -m pip install --upgrade pip >/dev/null

say "Installing requirements.txt"
python -m pip install -r requirements.txt

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
  python agents/s01_agent_loop.py

EOF
