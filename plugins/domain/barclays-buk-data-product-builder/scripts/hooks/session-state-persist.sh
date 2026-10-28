#!/usr/bin/env bash
# Atomic session state persistence after writes to session/
# PostToolUse hook — triggered on Write(session/**)|Edit(session/**)
set -euo pipefail

SESSION_FILE="session/session_state.json"
AUDIT_LOG="session/audit_log.jsonl"
TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Guard: only run if session file exists
if [ ! -f "$SESSION_FILE" ]; then
  exit 0
fi

# 1. Validate JSON is parseable (detect corruption from partial writes)
#    Python resolution — follows agents/refs/python-runtime-contract.md § Bash Script Pattern
PYTHON_CMD=""
if command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
elif [ -n "${PYTHON_PATH:-}" ]; then
  PYTHON_CMD="$PYTHON_PATH"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v py >/dev/null 2>&1; then
  PYTHON_CMD="py"
fi

if [ -n "$PYTHON_CMD" ]; then
  if ! "$PYTHON_CMD" -c "import json,sys; json.load(open(sys.argv[1]))" "$SESSION_FILE" 2>/dev/null; then
    echo "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"session_state_persist_error\",\"error\":\"JSON validation failed — file may be corrupted\",\"trigger\":\"post_tool_use\"}" >> "$AUDIT_LOG" 2>/dev/null
    exit 1
  fi
else
  # Bash-only fallback: basic JSON structure check when Python unavailable
  FIRST_CHAR=$(head -c1 "$SESSION_FILE" 2>/dev/null)
  LAST_CHAR=$(tail -c2 "$SESSION_FILE" 2>/dev/null | head -c1)
  if [ "$FIRST_CHAR" != "{" ] || [ "$LAST_CHAR" != "}" ]; then
    echo "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"session_state_persist_error\",\"error\":\"Basic JSON structure check failed (no Python available)\",\"trigger\":\"post_tool_use\"}" >> "$AUDIT_LOG" 2>/dev/null
    exit 1
  fi
fi

# 2. Log successful persistence
echo "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"session_state_persisted\",\"trigger\":\"post_tool_use\"}" >> "$AUDIT_LOG" 2>/dev/null || true

exit 0
