#!/usr/bin/env bash
# Preflight checks for ui-engineer visual validation.
# Verifies all prerequisites before screen generation begins.
# Usage: preflight.sh <project-path> <jira-id> [figma-url]
# Exit 0 = all checks passed. Exit 1 = one or more checks failed (error printed to stderr).
set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_PATH=${1:-}
JIRA_ID=${2:-}
FIGMA_URL=${3:-}
FAILURES=0

_pass() { echo "✅ $1"; }
_fail() { echo "❌ $1" >&2; FAILURES=$((FAILURES + 1)); }

if [[ -z "$PROJECT_PATH" || -z "$JIRA_ID" ]]; then
  echo "ERROR: Usage: preflight.sh <project-path> <jira-id> [figma-url]" >&2
  exit 1
fi

echo "[preflight] checking prerequisites for $PROJECT_PATH ($JIRA_ID)"
echo ""

# 1 — agent-device installed
if command -v agent-device &>/dev/null; then
  _pass "agent-device installed ($(agent-device --version 2>/dev/null || echo 'found'))"
else
  _fail "agent-device not installed. Run: npm install -g agent-device@latest"
fi

# 2 — simulator booted
BOOTED=$(xcrun simctl list devices 2>/dev/null | grep -w "Booted" || true)
if [[ -n "$BOOTED" ]]; then
  _pass "simulator booted: $(echo "$BOOTED" | head -1 | sed 's/^ *//')"
else
  _fail "no booted iOS simulator. Open Simulator.app and boot a device."
fi

# 3 — Shell app installed
SHELL_APP=$(xcrun simctl listapps booted 2>/dev/null | grep -i "org.reactjs.native.example.ShellApp" || true)
if [[ -n "$SHELL_APP" ]]; then
  _pass "Shell app installed on booted simulator"
else
  _fail "Shell app not installed. Build and install it from the shell-app repo: npx react-native run-ios"
fi

# 4 — Start Metro from PROJECT_PATH
echo ""
echo "[preflight] starting Metro from $PROJECT_PATH..."
if bash "$SCRIPTS_DIR/metro.sh" start "$PROJECT_PATH" "$JIRA_ID"; then
  _pass "Metro ready on port 8081"
else
  _fail "Metro failed to start. Check: cat /tmp/metro-${JIRA_ID}.log"
fi

# 5 — Point Shell app at Metro via deep link (includes component name from target project)
APP_NAME=$(python3 -c "import json,sys; d=json.load(open('${PROJECT_PATH}/app.json')); print(d.get('name',''))" 2>/dev/null || true)
if [[ -z "$APP_NAME" ]]; then
  _fail "Could not read app name from ${PROJECT_PATH}/app.json"
fi

echo ""
echo "[preflight] pointing Shell app at Metro ($PROJECT_PATH, component: $APP_NAME)..."
# Launch app first (bypasses "Open in Shell?" confirmation dialog in simulator)
# then send the deep link to switch bundle host and component name
if xcrun simctl list devices 2>/dev/null | grep -w "Booted" &>/dev/null; then
  METRO_URL="http%3A%2F%2Flocalhost%3A8081"
  APP_NAME_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${APP_NAME}'))")
  xcrun simctl launch booted "org.reactjs.native.example.ShellApp" 2>/dev/null || true
  sleep 1
  xcrun simctl openurl booted "shellapp://bundle?url=${METRO_URL}&name=${APP_NAME_ENCODED}"
  _pass "Shell app pointed at localhost:8081 (component: $APP_NAME)"
elif command -v adb &>/dev/null && adb devices 2>/dev/null | grep -v "List of devices" | grep "device$" &>/dev/null; then
  METRO_URL="http%3A%2F%2F10.0.2.2%3A8081"
  APP_NAME_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${APP_NAME}'))")
  adb shell am start -a android.intent.action.VIEW \
    -d "shellapp://bundle?url=${METRO_URL}&name=${APP_NAME_ENCODED}" \
    com.shellapp/.MainActivity
  _pass "Shell app pointed at 10.0.2.2:8081 (component: $APP_NAME)"
else
  _fail "No booted iOS simulator or connected Android device found."
fi

# 6 — Open Figma Desktop at the correct node (if URL provided)
if [[ -n "$FIGMA_URL" ]]; then
  echo ""
  echo "[preflight] opening Figma Desktop..."
  if bash "$SCRIPTS_DIR/open-figma.sh" "$FIGMA_URL"; then
    _pass "Figma Desktop opened to correct node"
  else
    _fail "Failed to open Figma Desktop. Ensure Figma Desktop app is installed."
  fi
else
  echo "⚠️  no FIGMA_URL provided — skipping Figma Desktop open"
fi

echo ""
if [[ $FAILURES -gt 0 ]]; then
  echo "❌ PREFLIGHT FAILED — $FAILURES check(s) did not pass. Fix the errors above and re-run."
  exit 1
else
  echo "✅ PREFLIGHT PASSED — all checks passed. Proceeding with screen generation."
  exit 0
fi
