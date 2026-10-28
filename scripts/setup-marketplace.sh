#!/usr/bin/env bash
# Sets up the BUK marketplace scoped to this project.
# Usage: ./scripts/setup-marketplace.sh [branch]
# Default branch: main
set -euo pipefail

BRANCH=${1:-main}
SETTINGS=".claude/settings.json"
MARKETPLACE_NAME="barclays-cio-buk"
REPO_URL="git@app.gitlab.barcapint.com:barclays/claude/marketplace/cio/buk.git"

claude plugin marketplace remove "$MARKETPLACE_NAME" --scope project 2>/dev/null || true

claude plugin marketplace add "$REPO_URL" \
  --scope project

if ! command -v jq &>/dev/null; then
  echo "WARNING: jq not found — manually set .extraKnownMarketplaces[\"$MARKETPLACE_NAME\"].source.ref = \"$BRANCH\" in $SETTINGS"
  exit 0
fi

tmp=$(mktemp)
jq --arg ref "$BRANCH" \
  '.extraKnownMarketplaces["'"$MARKETPLACE_NAME"'"].source.ref = $ref' \
  "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"

echo "Marketplace '$MARKETPLACE_NAME' configured (branch: $BRANCH)"
