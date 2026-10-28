# Validates that generated files match the locked platform in session state
SESSION_FILE="session/session_state.json"
if [ ! -f "$SESSION_FILE" ]; then exit 0; fi

# Pure-bash JSON extraction — no Python dependency (values are simple top-level strings)
PLATFORM=$(grep -o '"platform"[[:space:]]*:[[:space:]]*"[^"]*"' "$SESSION_FILE" 2>/dev/null | head -1 | sed 's/.*:[[:space:]]*"\([^"]*\)".*/\1/')
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' 2>/dev/null | head -1 | sed 's/.*:[[:space:]]*"\([^"]*\)".*/\1/')

if [ "$PLATFORM" = "glue" ] && echo "$FILE_PATH" | grep -q "databricks"; then
  echo '{"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"Platform is locked to Glue. Cannot write Databricks artefacts."}}' >&2
  exit 2
fi

if [ "$PLATFORM" = "databricks" ] && echo "$FILE_PATH" | grep -qE "(wrapper|dtxog)"; then
  echo '{"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"Platform is locked to Databricks. Cannot write Glue-specific artefacts."}}' >&2
  exit 2
fi

exit 0
