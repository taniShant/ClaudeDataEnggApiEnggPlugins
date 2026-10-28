#!/bin/bash
# chameleon-preview.sh
#
# Moves a named screen to routes[0], opens the shell app via agent-device,
# waits for the JS bundle to load, captures a screenshot, then restores routes.tsx.
#
# Usage:
#   bash scripts/chameleon-preview.sh --screen InterestRatesScreen --project /path/to/sdf-project [--output /tmp/preview.png] [--bundle-id org.reactjs.native.example.ShellApp]
#
# Requirements:
#   - agent-device installed globally: npm install -g agent-device
#   - iOS Simulator booted with shell app installed
#   - Metro running: npm run start (in a separate terminal)

set -e

# --- Args ---
SCREEN=""
PROJECT=""
OUTPUT="/tmp/chameleon-preview.png"
BUNDLE_ID="org.reactjs.native.example.ShellApp"

while [[ $# -gt 0 ]]; do
  case $1 in
    --screen)    SCREEN="$2";    shift 2 ;;
    --project)   PROJECT="$2";   shift 2 ;;
    --output)    OUTPUT="$2";    shift 2 ;;
    --bundle-id) BUNDLE_ID="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$SCREEN" ] || [ -z "$PROJECT" ]; then
  echo "Usage: chameleon-preview.sh --screen <ScreenName> --project <path> [--output <path>] [--bundle-id <id>]"
  exit 1
fi

ROUTES_FILE="$PROJECT/src/routes.tsx"

# --- Prerequisite checks ---

if ! command -v agent-device &>/dev/null; then
  echo "agent-device not found. Install it:"
  echo "  npm install -g agent-device"
  exit 1
fi

if [ ! -f "$ROUTES_FILE" ]; then
  echo "routes.tsx not found: $ROUTES_FILE"
  exit 1
fi

if ! grep -q "\"$SCREEN\"\|'$SCREEN'" "$ROUTES_FILE"; then
  echo "Screen '$SCREEN' not found in $ROUTES_FILE"
  echo "Available screens:"
  grep "name:" "$ROUTES_FILE" | sed "s/.*name: ['\"]//;s/['\"].*//" | sed 's/^/   /'
  exit 1
fi

# Check Metro is running
if ! curl -sf http://localhost:8081/status 2>/dev/null | grep -q "packager-status:running"; then
  echo "Metro not running. Start it first:"
  echo "  cd $PROJECT && npm run start"
  exit 1
fi

echo "Chameleon Preview: $SCREEN"
echo "  Project   : $PROJECT"
echo "  Bundle ID : $BUNDLE_ID"
echo "  Output    : $OUTPUT"
echo ""

# --- Save original routes and set up restore trap ---
ORIGINAL_ROUTES=$(cat "$ROUTES_FILE")

restore_routes() {
  printf '%s' "$ORIGINAL_ROUTES" > "$ROUTES_FILE"
  echo "  routes.tsx restored"
}
trap restore_routes EXIT

# --- Close any stale agent-device session ---
STALE_SESSION=$(agent-device session list --json 2>/dev/null | grep -o '"session":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$STALE_SESSION" ]; then
  echo "  Closing stale session: $STALE_SESSION"
  agent-device close --json 2>/dev/null || true
fi

# --- Move screen to routes[0] ---
echo "  Moving $SCREEN to routes[0]..."

node << EOF
const fs = require('fs');
const src = fs.readFileSync('$ROUTES_FILE', 'utf8');

const arrayStart = src.indexOf('= [') + 3;
const arrayEnd = src.lastIndexOf(']');
const prefix = src.slice(0, arrayStart);
const suffix = src.slice(arrayEnd);
const body = src.slice(arrayStart, arrayEnd);

const routes = [];
let depth = 0, start = -1;
for (let i = 0; i < body.length; i++) {
  if (body[i] === '{') {
    if (depth === 0) start = i;
    depth++;
  } else if (body[i] === '}') {
    depth--;
    if (depth === 0 && start !== -1) {
      routes.push(body.slice(start, i + 1));
      start = -1;
    }
  }
}

const targetIdx = routes.findIndex(r => r.includes("name: '$SCREEN'") || r.includes('name: "$SCREEN"'));
if (targetIdx === -1) {
  process.stderr.write("Screen '$SCREEN' not found in route objects\n");
  process.exit(1);
}
const target = routes.splice(targetIdx, 1)[0];
routes.unshift(target);

const newBody = '\n' + routes.map(r => '  ' + r.replace(/\n/g, '\n  ')).join(',\n') + ',\n';
fs.writeFileSync('$ROUTES_FILE', prefix + newBody + suffix);
EOF

# --- Open app via agent-device and wait for screen to load ---
echo "  Opening app..."

OPEN_RESULT=$(agent-device open "$BUNDLE_ID" --platform ios --foreground --json 2>&1)
if ! echo "$OPEN_RESULT" | grep -q '"success"'; then
  echo "  Failed to open app:"
  echo "$OPEN_RESULT"
  exit 1
fi

# Wait for Metro hot reload — routes.tsx change needs a full reload cycle
echo "  Waiting for JS bundle reload..."
sleep 5

# Verify the screen loaded — derive a keyword from the screen name (strip "Screen" suffix)
SCREEN_KEYWORD=$(echo "$SCREEN" | sed 's/Screen$//' | sed 's/\([A-Z]\)/ \1/g' | xargs)
SNAPSHOT=$(agent-device snapshot 2>/dev/null)
if ! echo "$SNAPSHOT" | grep -qi "$SCREEN_KEYWORD"; then
  echo "  Warning: '$SCREEN_KEYWORD' not found in accessibility tree — bundle may still be loading, waiting 3s more..."
  sleep 3
fi

# --- Capture screenshot ---
echo "  Capturing screenshot..."
agent-device screenshot "$OUTPUT" 2>/dev/null

# --- Close session ---
agent-device close --json 2>/dev/null || true

echo ""
echo "Screenshot saved: $OUTPUT"
