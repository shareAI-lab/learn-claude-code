#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/out"
TEST_SERVER_PID=""

base_url_port() {
  python3 - "$1" <<'PY'
from urllib.parse import urlparse
import sys

url = sys.argv[1]
parsed = urlparse(url)
if not parsed.scheme or not parsed.hostname or not parsed.port:
    raise SystemExit(f"Unable to parse host/port from BASE_URL: {url}")
print(parsed.port)
PY
}

base_url_ready() {
  local base_url="$1"
  curl -fsS -o /dev/null "${base_url}/" >/dev/null 2>&1
}

start_static_server_if_needed() {
  local base_url="$1"
  local port
  local log_file
  local attempt

  if base_url_ready "$base_url"; then
    return 0
  fi

  if [[ ! -d "$OUT_DIR" ]]; then
    echo "Static export not found at $OUT_DIR. Run 'npm run build' first." >&2
    return 1
  fi

  port="$(base_url_port "$base_url")"
  log_file="${TMPDIR:-/tmp}/learn-claude-code-browser-tests-${port}.log"

  python3 -m http.server "$port" -d "$OUT_DIR" >"$log_file" 2>&1 &
  TEST_SERVER_PID=$!

  for attempt in {1..40}; do
    if base_url_ready "$base_url"; then
      return 0
    fi
    sleep 0.25
  done

  echo "Failed to start static server for ${base_url}" >&2
  if [[ -f "$log_file" ]]; then
    cat "$log_file" >&2
  fi
  return 1
}

stop_static_server_if_started() {
  if [[ -n "${TEST_SERVER_PID:-}" ]]; then
    kill "$TEST_SERVER_PID" >/dev/null 2>&1 || true
    wait "$TEST_SERVER_PID" >/dev/null 2>&1 || true
    TEST_SERVER_PID=""
  fi
}

open_url_with_retry() {
  local url="$1"
  local attempt
  local current_url=""

  for attempt in 1 2 3; do
    if agent-browser open "$url" >/dev/null 2>&1; then
      agent-browser wait --load networkidle >/dev/null 2>&1 || agent-browser wait 800 >/dev/null 2>&1 || true
      current_url="$(agent-browser get url 2>/dev/null | tr -d '\r' | tail -n 1)"
      current_url="${current_url%/}"
      if [[ -n "$current_url" && "$current_url" != "about:blank" ]]; then
        return 0
      fi
      agent-browser wait 600 >/dev/null 2>&1 || true
      current_url="$(agent-browser get url 2>/dev/null | tr -d '\r' | tail -n 1)"
      current_url="${current_url%/}"
      if [[ -n "$current_url" && "$current_url" != "about:blank" ]]; then
        return 0
      fi
    fi
    agent-browser close >/dev/null 2>&1 || true
    sleep 0.4
  done

  return 1
}
