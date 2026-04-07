#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${BASE_URL:-${1:-http://127.0.0.1:3002}}"
LOCALES="${LOCALES:-zh}"

TMP_DIR="$(mktemp -d)"
source "$ROOT_DIR/scripts/browser-test-lib.sh"

trap 'rm -rf "$TMP_DIR"; stop_static_server_if_started; agent-browser close >/dev/null 2>&1 || true' EXIT

discover_routes() {
  local locale="$1"
  find "$ROOT_DIR/out/$locale" -type f -name 'index.html' | sort | while read -r file; do
    local route="${file#"$ROOT_DIR/out"}"
    route="${route%index.html}"
    echo "$route"
  done
}

check_route() {
  local route="$1"
  local safe_name="${route#/}"
  local snapshot_file="$TMP_DIR/${safe_name//\//_}.png"
  local info_json
  local errors_json
  local check_output=""
  local attempt

  agent-browser --json errors --clear >/dev/null 2>&1 || true
  agent-browser close >/dev/null 2>&1 || true
  if ! open_url_with_retry "${BASE_URL}${route}"; then
    echo "FAIL	${route}	navigation-failed"
    return 1
  fi
  agent-browser wait --load networkidle >/dev/null 2>&1 || agent-browser wait 500 >/dev/null 2>&1 || true
  agent-browser get title >/dev/null 2>&1 || true

  for attempt in 1 2 3 4 5; do
    info_json="$(agent-browser --json eval '({
      title: document.title,
      h1Count: document.querySelectorAll("h1").length,
      mainExists: Boolean(document.querySelector("main")),
      overflow: document.documentElement.scrollWidth > window.innerWidth,
      notFound: document.body.innerText.includes("This page could not be found."),
      bodyLength: document.body.innerText.trim().length
    })')"
    errors_json="$(agent-browser --json errors)"

    if check_output="$(
      INFO_JSON="$info_json" ERRORS_JSON="$errors_json" python3 - "$route" <<'PY'
import json
import os
import sys

route = sys.argv[1]
info = json.loads(os.environ["INFO_JSON"]) or {}
errors = json.loads(os.environ["ERRORS_JSON"]) or {}

if not isinstance(info, dict):
    info = {}
if not isinstance(errors, dict):
    errors = {}

result = (info.get("data") or {}).get("result") or {}
page_errors = (errors.get("data") or {}).get("errors") or []
issues = []

if not result:
    issues.append("missing-eval-result")
if not result.get("title"):
    issues.append("missing-title")
if result.get("h1Count", 0) < 1:
    issues.append("missing-h1")
if not result.get("mainExists"):
    issues.append("missing-main")
if result.get("overflow"):
    issues.append("horizontal-overflow")
if result.get("notFound"):
    issues.append("rendered-404")
if result.get("bodyLength", 0) < 80:
    issues.append("body-too-short")
if page_errors:
    issues.append(f"page-errors:{len(page_errors)}")

if issues:
    print(f"FAIL\t{route}\t{','.join(issues)}")
    sys.exit(1)

print(f"OK\t{route}")
PY
    )"; then
      echo "$check_output"
      return 0
    fi

    if [[ "$attempt" -lt 5 ]]; then
      agent-browser wait 900 >/dev/null 2>&1 || true
    fi
  done

  echo "${check_output:-FAIL	${route}	unknown-check-failure}"
  agent-browser screenshot "$snapshot_file" >/dev/null 2>&1 || true
  if [[ -f "$snapshot_file" ]]; then
    echo "ARTIFACT	${route}	${snapshot_file}" >&2
  fi
  return 1
}

main() {
  local failed=0
  local total=0
  local warm_locale="${LOCALES%%,*}"

  start_static_server_if_needed "$BASE_URL"
  agent-browser close >/dev/null 2>&1 || true
  agent-browser set viewport 1440 960 >/dev/null 2>&1 || true
  open_url_with_retry "${BASE_URL}/${warm_locale}/" >/dev/null 2>&1 || open_url_with_retry "${BASE_URL}/" >/dev/null 2>&1 || true
  agent-browser wait 400 >/dev/null 2>&1 || true

  for locale in ${LOCALES//,/ }; do
    while read -r route; do
      [[ -z "$route" ]] && continue
      total=$((total + 1))
      if ! check_route "$route"; then
        failed=$((failed + 1))
      fi
    done < <(discover_routes "$locale")
  done

  echo
  echo "Smoke summary: ${total} checked, ${failed} failed"
  if [[ "$failed" -ne 0 ]]; then
    exit 1
  fi
}

main "$@"
