#!/usr/bin/env bash
# Open a Figma file at a specific node in the Figma Desktop app.
# Ensures the correct file is loaded before MCP tool calls are made.
# Usage: open-figma.sh <figma-web-url>
# Example: open-figma.sh "https://www.figma.com/design/NvCSfNYb1LcHcxfUj2xQdn/File?node-id=17668-26112"
set -euo pipefail

FIGMA_URL=${1:-}

if [[ -z "$FIGMA_URL" ]]; then
  echo "ERROR: Figma URL required. Usage: open-figma.sh <figma-web-url>" >&2
  exit 1
fi

# Extract file key from URL path: /design/{fileKey}/...
FILE_KEY=$(echo "$FIGMA_URL" | sed -E 's|.*/design/([^/?]+).*|\1|')

# Extract node-id query param
NODE_ID=$(echo "$FIGMA_URL" | sed -E 's/.*[?&]node-id=([^&]+).*/\1/')

if [[ -z "$FILE_KEY" || "$FILE_KEY" == "$FIGMA_URL" ]]; then
  echo "ERROR: could not extract file key from URL: $FIGMA_URL" >&2
  exit 1
fi

if [[ -z "$NODE_ID" || "$NODE_ID" == "$FIGMA_URL" ]]; then
  # No node-id — open just the file
  DEEP_LINK="figma://file/${FILE_KEY}"
else
  DEEP_LINK="figma://file/${FILE_KEY}?node-id=${NODE_ID}"
fi

echo "[figma] opening $DEEP_LINK"
open "$DEEP_LINK"

# Give the desktop app a moment to focus and load the node
sleep 2

echo "[figma] done — Figma Desktop should now be showing node ${NODE_ID:-root} in file ${FILE_KEY}"
