# Quick validation after artefact generation — checks for unresolved placeholders
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PLUGIN_ROOT/logs"

INPUT=$(cat)
# Pure-bash JSON extraction — no Python dependency (file_path is a simple top-level string)
FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' 2>/dev/null | head -1 | sed 's/.*:[[:space:]]*"\([^"]*\)".*/\1/')

if [ -f "$FILE_PATH" ]; then
  PLACEHOLDERS=$(grep -oP '\{\{[a-z_]+\}\}' "$FILE_PATH" 2>/dev/null | sort -u)
  if [ -n "$PLACEHOLDERS" ]; then
    mkdir -p "$LOG_DIR"
    echo "[$(date '+%d/%m/%y %H:%M:%S')] [HOOK:post-generate-validate] [WARN] Unresolved placeholders in $FILE_PATH: $PLACEHOLDERS" >> "$LOG_DIR/de-pipeline.log"
  fi
fi

exit 0
