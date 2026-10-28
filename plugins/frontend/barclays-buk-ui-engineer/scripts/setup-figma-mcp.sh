#!/usr/bin/env bash
# Configures Figma Desktop MCP for a project so ui-engineer agents can access design context.
# Usage: ./scripts/setup-figma-mcp.sh [project-path]
# Default project-path: current directory
set -euo pipefail

PROJECT_PATH=${1:-$(pwd)}
MCP_JSON="$PROJECT_PATH/.mcp.json"
SETTINGS_DIR="$PROJECT_PATH/.claude"
SETTINGS_JSON="$SETTINGS_DIR/settings.json"
# Use settings.local.json for enabledMcpjsonServers — this file is untracked by git,
# which means Claude Code applies it without requiring workspace trust approval.
# A committed settings.json is ignored until the user accepts the trust dialog.
SETTINGS_LOCAL_JSON="$SETTINGS_DIR/settings.local.json"
SERVER_NAME="figma-local"
FIGMA_URL="http://127.0.0.1:3845/mcp"

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required. Install with: brew install jq"
  exit 1
fi

# Check Figma Desktop MCP is actually running
if ! curl -s "$FIGMA_URL" 2>&1 | grep -q "jsonrpc"; then
  echo "WARNING: Figma Desktop MCP not reachable at $FIGMA_URL"
  echo "  Open Figma Desktop → Preferences → Enable Dev Mode MCP Server, then re-run."
fi

# Write .mcp.json
if [[ -f "$MCP_JSON" ]]; then
  tmp=$(mktemp) || { echo "ERROR: mktemp failed"; exit 1; }
  if jq --arg name "$SERVER_NAME" --arg url "$FIGMA_URL" \
    '.mcpServers[$name] = {"type": "http", "url": $url}' \
    "$MCP_JSON" > "$tmp" && [[ -s "$tmp" ]] && jq empty "$tmp" 2>/dev/null; then
    mv "$tmp" "$MCP_JSON"
  else
    rm -f "$tmp"; echo "ERROR: jq failed to update $MCP_JSON — file left unchanged"; exit 1
  fi
  echo "Updated $MCP_JSON"
else
  cat > "$MCP_JSON" <<EOF
{
  "mcpServers": {
    "$SERVER_NAME": {
      "type": "http",
      "url": "$FIGMA_URL"
    }
  }
}
EOF
  echo "Created $MCP_JSON"
fi

# Write/update .claude/settings.local.json to enable the server.
# This file is untracked by git — Claude Code applies it without requiring workspace
# trust approval. Do NOT put enabledMcpjsonServers in settings.json: a committed
# settings.json is ignored until the user accepts the trust dialog, which makes the
# server silently unavailable in fresh clones and spawned subagents.
mkdir -p "$SETTINGS_DIR"

# MCP tool permission entries — pre-approve figma-local tools so agents never
# prompt the user for confirmation when calling get_design_context etc.
MCP_TOOLS='["mcp__figma-local__get_design_context","mcp__figma-local__get_variable_defs","mcp__figma-local__get_screenshot"]'

if [[ -f "$SETTINGS_LOCAL_JSON" ]]; then
  tmp=$(mktemp) || { echo "ERROR: mktemp failed"; exit 1; }
  if jq --arg name "$SERVER_NAME" --argjson tools "$MCP_TOOLS" '
    .enabledMcpjsonServers = ((.enabledMcpjsonServers // []) + [$name] | unique) |
    .permissions.allow = ((.permissions.allow // []) + $tools | unique)
  ' "$SETTINGS_LOCAL_JSON" > "$tmp" && [[ -s "$tmp" ]] && jq empty "$tmp" 2>/dev/null; then
    mv "$tmp" "$SETTINGS_LOCAL_JSON"
  else
    rm -f "$tmp"; echo "ERROR: jq failed to update $SETTINGS_LOCAL_JSON — file left unchanged"; exit 1
  fi
  echo "Updated $SETTINGS_LOCAL_JSON"
else
  cat > "$SETTINGS_LOCAL_JSON" <<EOF
{
  "enabledMcpjsonServers": ["$SERVER_NAME"],
  "permissions": {
    "allow": [
      "mcp__figma-local__get_design_context",
      "mcp__figma-local__get_variable_defs",
      "mcp__figma-local__get_screenshot"
    ]
  }
}
EOF
  echo "Created $SETTINGS_LOCAL_JSON"
fi

# Also ensure settings.json does NOT contain enabledMcpjsonServers (remove if present,
# to avoid the committed-file trust-gate problem)
if [[ -f "$SETTINGS_JSON" ]] && jq -e '.enabledMcpjsonServers' "$SETTINGS_JSON" &>/dev/null; then
  tmp=$(mktemp) || { echo "ERROR: mktemp failed"; exit 1; }
  if jq 'del(.enabledMcpjsonServers)' "$SETTINGS_JSON" > "$tmp" && [[ -s "$tmp" ]] && jq empty "$tmp" 2>/dev/null; then
    mv "$tmp" "$SETTINGS_JSON"
  else
    rm -f "$tmp"; echo "ERROR: jq failed to update $SETTINGS_JSON — file left unchanged"; exit 1
  fi
  echo "Removed enabledMcpjsonServers from $SETTINGS_JSON (moved to settings.local.json)"
fi

# Pre-approve agent-device Bash calls so visual preview steps never prompt
AGENT_DEVICE_TOOLS='["Bash(agent-device *)"]'

if [[ -f "$SETTINGS_LOCAL_JSON" ]]; then
  tmp=$(mktemp) || { echo "ERROR: mktemp failed"; exit 1; }
  if jq --argjson tools "$AGENT_DEVICE_TOOLS" '
    .permissions.allow = ((.permissions.allow // []) + $tools | unique)
  ' "$SETTINGS_LOCAL_JSON" > "$tmp" && [[ -s "$tmp" ]] && jq empty "$tmp" 2>/dev/null; then
    mv "$tmp" "$SETTINGS_LOCAL_JSON"
  else
    rm -f "$tmp"; echo "ERROR: jq failed to update $SETTINGS_LOCAL_JSON — file left unchanged"; exit 1
  fi
else
  # settings.local.json doesn't exist yet — create it (should have been created above,
  # but guard against edge cases where the figma section was skipped)
  cat > "$SETTINGS_LOCAL_JSON" <<EOF
{
  "permissions": {
    "allow": [
      "Bash(agent-device *)"
    ]
  }
}
EOF
fi

# Check agent-device is reachable
if ! command -v agent-device &>/dev/null; then
  echo ""
  echo "MISSING PREREQUISITE: agent-device not found in PATH"
  echo "  Visual preview steps in agents require agent-device."
  echo "  Install it now:"
  echo ""
  echo "    npm install -g agent-device@latest"
  echo ""
  echo "  Then re-run this script to register its permissions."
else
  echo "agent-device: $(agent-device --version 2>/dev/null || echo 'found')"
fi

echo ""
echo "Figma MCP configured for: $PROJECT_PATH"
echo "Start a new Claude Code session in that directory to pick it up."
echo "(MCP servers load at session start — an existing session will not see them.)"
