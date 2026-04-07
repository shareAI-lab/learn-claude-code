#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-${1:-http://127.0.0.1:3002}}"
LOCALE="${LOCALE:-zh}"
SESSION_NAME="${SESSION_NAME:-learn-claude-code-flows-${LOCALE}}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/browser-test-lib.sh"

agent-browser() {
  command agent-browser --session-name "$SESSION_NAME" "$@"
}

trap 'stop_static_server_if_started; agent-browser close >/dev/null 2>&1 || true' EXIT

locale_text() {
  local key="$1"
  case "$LOCALE:$key" in
    zh:deep_dive) echo '深入探索' ;;
    en:deep_dive) echo 'Deep Dive' ;;
    ja:deep_dive) echo '深掘り' ;;

    zh:bridge_control_plane) echo '工具控制平面' ;;
    en:bridge_control_plane) echo 'Tool Control Plane' ;;
    ja:bridge_control_plane) echo 'ツール制御プレーン' ;;

    *) echo "Unknown locale text key: ${LOCALE}:${key}" >&2; return 1 ;;
  esac
}

wait_page() {
  agent-browser wait --load networkidle >/dev/null 2>&1 || agent-browser wait 600 >/dev/null 2>&1 || true
  agent-browser wait 1200 >/dev/null 2>&1 || true
  agent-browser get title >/dev/null 2>&1 || true
}

open_page() {
  local path="$1"
  local attempt

  agent-browser close >/dev/null 2>&1 || true
  for attempt in 1 2 3; do
    agent-browser --json errors --clear >/dev/null 2>&1 || true
    if ! open_url_with_retry "${BASE_URL}${path}"; then
      continue
    fi
    wait_page
    if assert_url_contains "$path" >/dev/null 2>&1; then
      return 0
    fi
    agent-browser close >/dev/null 2>&1 || true
    sleep 0.4
  done

  echo "Navigation failed for ${BASE_URL}${path}" >&2
  return 1
}

assert_url_contains() {
  local expected="$1"
  local url_json
  url_json="$(agent-browser --json get url)"
  URL_JSON="$url_json" EXPECTED="$expected" python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["URL_JSON"])
url = payload.get("data", {}).get("url", "")
expected = os.environ["EXPECTED"]
if expected not in url:
    print(f"Expected URL containing {expected!r}, got {url!r}", file=sys.stderr)
    sys.exit(1)
PY
}

assert_body_contains() {
  local pattern="$1"
  agent-browser get text body | rg -q "$pattern"
}

assert_no_overflow() {
  local info_json
  info_json="$(agent-browser --json eval '({
    overflow: document.documentElement.scrollWidth > window.innerWidth,
    width: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth
  })')"
  INFO_JSON="$info_json" python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["INFO_JSON"])
result = payload.get("data", {}).get("result", {})
if result.get("overflow"):
    print(
        f"Overflow detected: width={result.get('width')} scrollWidth={result.get('scrollWidth')}",
        file=sys.stderr,
    )
    sys.exit(1)
PY
}

assert_no_page_errors() {
  local errors_json
  errors_json="$(agent-browser --json errors)"
  ERRORS_JSON="$errors_json" python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["ERRORS_JSON"])
errors = payload.get("data", {}).get("errors", [])
if errors:
    print(f"Unexpected page errors: {errors}", file=sys.stderr)
    sys.exit(1)
PY
}

click_locale_button() {
  local label="$1"
  agent-browser --json eval "(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const match = buttons.find((button) => button.textContent.trim() === '${label}');
    if (!match) {
      throw new Error('Locale button not found: ${label}');
    }
    match.click();
    return true;
  })() " >/dev/null
}

click_link_exact() {
  local label="$1"
  agent-browser --json eval "(() => {
    const links = Array.from(document.querySelectorAll('a'));
    const match = links.find((link) => link.textContent.trim() === '${label}');
    if (!match) {
      throw new Error('Link not found: ${label}');
    }
    match.click();
    return true;
  })() " >/dev/null
}

click_link_containing() {
  local label="$1"
  agent-browser --json eval "(() => {
    const normalize = (value) => value.replace(/\s+/g, ' ').trim();
    const links = Array.from(document.querySelectorAll('a'));
    const match = links.find((link) => normalize(link.textContent).includes('${label}'));
    if (!match) {
      throw new Error('Link not found: ${label}');
    }
    match.click();
    return true;
  })() " >/dev/null
}

click_link_by_href() {
  local href_fragment="$1"
  local label_fragment="${2:-}"
  agent-browser --json eval "(() => {
    const normalize = (value) => value.replace(/\s+/g, ' ').trim();
    const links = Array.from(document.querySelectorAll('a'));
    const match = links.find((link) => {
      const hrefMatches = link.href.includes('${href_fragment}');
      const labelMatches = '${label_fragment}' ? normalize(link.textContent).includes('${label_fragment}') : true;
      return hrefMatches && labelMatches;
    });
    if (!match) {
      throw new Error('Link not found for href: ${href_fragment}');
    }
    match.click();
    return true;
  })() " >/dev/null
}

run_flow() {
  local name="$1"
  shift
  echo "FLOW\t${name}"
  "$@"
  echo "PASS\t${name}"
}

flow_home_to_s01() {
  open_page "/${LOCALE}/"
  click_link_by_href "/${LOCALE}/s01/"
  wait_page
  assert_url_contains "/${LOCALE}/s01/"
  assert_body_contains 's01'
  assert_no_overflow
  assert_no_page_errors
}

flow_home_to_timeline() {
  open_page "/${LOCALE}/timeline/"
  assert_url_contains "/${LOCALE}/timeline/"
  assert_body_contains 's01'
  assert_body_contains 's19'
  assert_no_overflow
  assert_no_page_errors
}

flow_home_to_layers() {
  open_page "/${LOCALE}/layers/"
  assert_url_contains "/${LOCALE}/layers/"
  assert_body_contains 'P1'
  assert_body_contains 's19'
  assert_no_overflow
  assert_no_page_errors
}

flow_home_to_compare() {
  open_page "/${LOCALE}/"
  click_link_by_href "/${LOCALE}/compare/"
  wait_page
  assert_url_contains "/${LOCALE}/compare/"
  assert_body_contains 's14 -> s15'
  assert_no_overflow
  assert_no_page_errors
}

flow_compare_default_state() {
  open_page "/${LOCALE}/compare"
  assert_body_contains 's01'
  assert_body_contains 's02'
  assert_body_contains 's14 -> s15'
  assert_no_overflow
  assert_no_page_errors
}

flow_timeline_to_stage_exit() {
  open_page "/${LOCALE}/timeline"
  click_link_by_href "/${LOCALE}/s06/"
  wait_page
  assert_url_contains "/${LOCALE}/s06/"
  assert_body_contains 's06'
  assert_no_overflow
  assert_no_page_errors
}

flow_layers_to_stage_entry() {
  open_page "/${LOCALE}/layers"
  click_link_by_href "/${LOCALE}/s15/"
  wait_page
  assert_url_contains "/${LOCALE}/s15/"
  assert_body_contains 's15'
  assert_no_overflow
  assert_no_page_errors
}

flow_chapter_to_bridge_doc() {
  open_page "/${LOCALE}/s02"
  agent-browser --json find text "$(locale_text deep_dive)" click >/dev/null
  wait_page
  click_link_by_href "/${LOCALE}/docs/s02a-tool-control-plane/" "$(locale_text bridge_control_plane)"
  wait_page
  assert_url_contains "/${LOCALE}/docs/s02a-tool-control-plane/"
  assert_body_contains "$(locale_text bridge_control_plane)"
  assert_no_overflow
  assert_no_page_errors
}

flow_bridge_doc_home_return() {
  open_page "/${LOCALE}/docs/s00f-code-reading-order"
  click_link_by_href "/${LOCALE}/"
  wait_page
  assert_url_contains "/${LOCALE}/"
  assert_body_contains 's01'
  assert_no_overflow
  assert_no_page_errors
}

flow_bridge_doc_back_to_chapter() {
  open_page "/${LOCALE}/docs/s02a-tool-control-plane"
  click_link_by_href "/${LOCALE}/s02/" 's02'
  wait_page
  assert_url_contains "/${LOCALE}/s02/"
  assert_body_contains 's02'
  assert_no_overflow
  assert_no_page_errors
}

flow_bridge_doc_locale_switching() {
  open_page "/${LOCALE}/docs/s00f-code-reading-order"
  click_locale_button 'EN'
  wait_page
  assert_url_contains '/en/docs/s00f-code-reading-order/'
  click_locale_button '日本語'
  wait_page
  assert_url_contains '/ja/docs/s00f-code-reading-order/'
  click_locale_button '中文'
  wait_page
  assert_url_contains '/zh/docs/s00f-code-reading-order/'
  assert_no_page_errors
}

flow_compare_preset() {
  open_page "/${LOCALE}/compare"
  agent-browser --json find text 's14 -> s15' click >/dev/null
  agent-browser wait 800 >/dev/null 2>&1 || true
  assert_body_contains 's14'
  assert_body_contains 's15'
  assert_no_overflow
  assert_no_page_errors
}

flow_chapter_next_navigation() {
  open_page "/${LOCALE}/s15"
  click_link_by_href "/${LOCALE}/s16/"
  wait_page
  assert_url_contains "/${LOCALE}/s16/"
  assert_body_contains 's16'
  assert_no_overflow
  assert_no_page_errors
}

flow_locale_switching() {
  open_page "/${LOCALE}/s01"
  click_locale_button 'EN'
  wait_page
  assert_url_contains '/en/s01/'
  click_locale_button '日本語'
  wait_page
  assert_url_contains '/ja/s01/'
  click_locale_button '中文'
  wait_page
  assert_url_contains '/zh/s01/'
  assert_no_page_errors
}

flow_mobile_core_pages() {
  agent-browser set viewport 390 844 >/dev/null 2>&1
  for path in \
    "/${LOCALE}/" \
    "/${LOCALE}/timeline" \
    "/${LOCALE}/layers" \
    "/${LOCALE}/compare" \
    "/${LOCALE}/s15" \
    "/${LOCALE}/docs/s00f-code-reading-order"
  do
    open_page "$path"
    assert_no_overflow
    assert_no_page_errors
  done
  agent-browser set viewport 1440 960 >/dev/null 2>&1
}

main() {
  start_static_server_if_needed "$BASE_URL"
  agent-browser close >/dev/null 2>&1 || true
  agent-browser set viewport 1440 960 >/dev/null 2>&1 || true
  open_url_with_retry "${BASE_URL}/${LOCALE}/" >/dev/null 2>&1 || open_url_with_retry "${BASE_URL}/" >/dev/null 2>&1 || true
  agent-browser wait 400 >/dev/null 2>&1 || true

  run_flow home-to-s01 flow_home_to_s01
  run_flow home-to-timeline flow_home_to_timeline
  run_flow home-to-layers flow_home_to_layers
  run_flow home-to-compare flow_home_to_compare
  run_flow compare-default-state flow_compare_default_state
  run_flow timeline-to-stage-exit flow_timeline_to_stage_exit
  run_flow layers-to-stage-entry flow_layers_to_stage_entry
  run_flow chapter-to-bridge-doc flow_chapter_to_bridge_doc
  run_flow bridge-doc-home-return flow_bridge_doc_home_return
  run_flow bridge-doc-back-to-chapter flow_bridge_doc_back_to_chapter
  run_flow bridge-doc-locale-switching flow_bridge_doc_locale_switching
  run_flow compare-preset flow_compare_preset
  run_flow chapter-next-navigation flow_chapter_next_navigation
  run_flow locale-switching flow_locale_switching
  run_flow mobile-core-pages flow_mobile_core_pages
}

main "$@"
