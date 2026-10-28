#!/usr/bin/env bash
# Manage the Metro bundler lifecycle for ui-engineer visual validation.
# Usage:
#   metro.sh start <project-path> <jira-id>   — kill stale, start fresh, wait until ready
#   metro.sh stop  <jira-id>                  — kill the Metro process started by this script
#   metro.sh status                           — print whether Metro is ready on port 8081
set -euo pipefail

METRO_PORT=8081
COMMAND=${1:-}
PROJECT_PATH=${2:-}
JIRA_ID=${3:-default}
PID_FILE="/tmp/metro-${JIRA_ID}.pid"
LOG_FILE="/tmp/metro-${JIRA_ID}.log"

_ready() {
  curl -s "http://localhost:${METRO_PORT}/status" 2>/dev/null | grep -q "packager-status:running"
}

_kill_stale() {
  local pids
  pids=$(lsof -ti ":${METRO_PORT}" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "[metro] killing stale processes on port ${METRO_PORT} (PIDs: $(echo $pids | tr '\n' ' '))"
    echo "$pids" | xargs kill 2>/dev/null || true
    sleep 1
  fi
}

case "$COMMAND" in
  start)
    if [[ -z "$PROJECT_PATH" ]]; then
      echo "ERROR: project-path required. Usage: metro.sh start <project-path> <jira-id>" >&2
      exit 1
    fi

    _kill_stale

    echo "[metro] starting from $PROJECT_PATH (log: $LOG_FILE)"
    cd "$PROJECT_PATH"
    nohup npx react-native start --reset-cache > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"

    echo "[metro] waiting for Metro to be ready (up to 60s)..."
    for i in $(seq 1 60); do
      sleep 1
      if _ready; then
        echo "[metro] READY (${i}s)"
        exit 0
      fi
    done

    echo "[metro] TIMEOUT — Metro did not become ready within 60s" >&2
    echo "[metro] last log output:" >&2
    tail -20 "$LOG_FILE" >&2
    exit 1
    ;;

  stop)
    if [[ -f "$PID_FILE" ]]; then
      pid=$(cat "$PID_FILE")
      echo "[metro] stopping Metro (PID $pid)"
      kill "$pid" 2>/dev/null || true
      rm -f "$PID_FILE"
    else
      # Fall back to killing by port in case PID file is missing
      _kill_stale
    fi
    echo "[metro] stopped"
    ;;

  status)
    if _ready; then
      echo "[metro] READY on port ${METRO_PORT}"
      exit 0
    else
      echo "[metro] NOT READY on port ${METRO_PORT}"
      exit 1
    fi
    ;;

  *)
    echo "Usage: metro.sh <start|stop|status> [project-path] [jira-id]" >&2
    exit 1
    ;;
esac
