# Migration State Tracking

The MCA2 JDK upgrade uses a state file to track migration progress and prevent duplicate work.

## State File Location

`{project_path}/.mca2-jdk-migration-state.json`

**IMPORTANT**: This file is created at the start of Phase 0 and updated after each phase completes.

## State File Format

```json
{
  "version": "2.0.0",
  "jira_id": "GENAIACCEL-1234",
  "project_path": "/absolute/path/to/project",
  "build_tool": "gradle",
  "group": "capl",
  "started_at": "2026-02-21T16:10:00Z",
  "last_updated": "2026-02-21T16:30:00Z",
  "branch_name": "feature/GENAIACCEL-1234",
  "phases": {
    "phase_0": {
      "status": "completed",
      "completed_at": "2026-02-21T16:12:00Z",
      "commit_sha": "abc123...",
      "actions": [
        "Created feature branch",
        "Deduplicated 13 repository declarations to 3",
        "Resolved mca-rewrite-spring version: 1.1.5",
        "Commented out truststore/keystore in gradle.properties"
      ]
    },
    "phase_1": {
      "status": "completed",
      "completed_at": "2026-02-21T16:20:00Z",
      "commit_sha": "def456...",
      "actions": [
        "Verified Java 8 runtime",
        "Pre-rewrite build passed",
        "OpenRewrite execution succeeded",
        "Switched to Java 21",
        "Updated Gradle wrapper to 8.5",
        "Removed OpenRewrite config"
      ],
      "openrewrite_version": "1.1.5",
      "java_8_verified": true,
      "java_21_switched": true
    },
    "phase_2": {
      "status": "completed",
      "completed_at": "2026-02-21T16:25:00Z",
      "commit_sha": "ghi789...",
      "actions": [
        "Consolidated dependencies.gradle",
        "Added platform BOM: mca-dependencies:3.0.0",
        "Updated Spring Boot to 3.5.0",
        "Migrated bootRun.main to bootRun.mainClass",
        "Migrated JaCoCo.reportsDir to JaCoCo.reportsDirectory"
      ],
      "spring_boot_version": "3.5.0",
      "gradle_version": "8.5"
    },
    "phase_2_5": {
      "status": "completed",
      "completed_at": "2026-02-21T16:26:00Z",
      "commit_sha": "stu901...",
      "actions": [
        "Aligned test packages with source packages"
      ]
    },
    "phase_3": {
      "status": "completed",
      "completed_at": "2026-02-21T16:28:00Z",
      "commit_sha": "jkl012...",
      "actions": [
        "Migrated 42 javax imports to jakarta",
        "Updated jakarta dependencies"
      ],
      "javax_imports_migrated": 42
    },
    "phase_4": {
      "status": "in_progress",
      "started_at": "2026-02-21T16:28:30Z"
    },
    "phase_5": {
      "status": "pending",
      "will_execute": true
    },
    "phase_6": {
      "status": "pending"
    },
    "phase_7": {
      "status": "pending"
    },
    "phase_8": {
      "status": "pending"
    }
  }
}
```

## Phase Status Values

- `"pending"` - Phase has not started
- `"in_progress"` - Phase is currently executing
- `"completed"` - Phase finished successfully
- `"failed"` - Phase failed (migration stopped)
- `"skipped"` - Phase was intentionally skipped (e.g., Phase 5 if no HttpClient detected)

## Phase-Specific Fields

### Phase 5: HttpClient Migration

Phase 5 has an additional field `will_execute` that is set during Phase 0:

```json
"phase_5": {
  "status": "pending",
  "will_execute": true
}
```

- `will_execute: true` - Apache HttpClient was detected in Phase 0, Phase 5 will execute migration
- `will_execute: false` - Apache HttpClient was not detected in Phase 0, Phase 5 will be skipped

**CRITICAL**: This detection happens ONLY in Phase 0. Phase 5 MUST NOT perform any file scanning or heuristics - it must trust the `will_execute` value from the state file.

## Usage in Agent

### Phase 0: Initialize State File

```bash
# Create state file at project root
STATE_FILE="$PROJECT_PATH/.mca2-jdk-migration-state.json"

cat > "$STATE_FILE" << EOF
{
  "version": "2.0.0",
  "jira_id": "$JIRA_ID",
  "project_path": "$PROJECT_PATH",
  "build_tool": "$BUILD_TOOL",
  "group": "$GROUP",
  "started_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "branch_name": "feature/$JIRA_ID",
  "phases": {
    "phase_0": {"status": "in_progress", "started_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"},
    "phase_1": {"status": "pending"},
    "phase_2": {"status": "pending"},
    "phase_2_5": {"status": "pending"},
    "phase_3": {"status": "pending"},
    "phase_4": {"status": "pending"},
    "phase_5": {"status": "pending", "will_execute": true},
    "phase_6": {"status": "pending"},
    "phase_7": {"status": "pending"},
    "phase_8": {"status": "pending"}
  }
}
EOF

log "├─ Created migration state file: $STATE_FILE"
```

### After Each Phase: Update State

```bash
# Use jq to update state file (cross-platform JSON manipulation)
# If jq not available, use Python as fallback

update_phase_state() {
  local phase="$1"
  local status="$2"
  local commit_sha="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"

  # Try jq first
  if command -v jq > /dev/null 2>&1; then
    jq --arg phase "$phase" \
       --arg status "$status" \
       --arg commit "$commit_sha" \
       --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
       '.last_updated = $timestamp |
        .phases[$phase].status = $status |
        .phases[$phase].completed_at = $timestamp |
        .phases[$phase].commit_sha = $commit' \
       "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
  else
    # Fallback: use Python
    python3 << PYEOF
import json
from datetime import datetime

with open("$STATE_FILE", 'r') as f:
    state = json.load(f)

state['last_updated'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
state['phases']['$phase']['status'] = '$status'
state['phases']['$phase']['completed_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
state['phases']['$phase']['commit_sha'] = '$commit_sha'

with open("$STATE_FILE", 'w') as f:
    json.dump(state, f, indent=2)
PYEOF
  fi

  log "│  └─ Updated state: $phase -> $status"
}

# Example usage after Phase 0 completes:
update_phase_state "phase_0" "completed"
```

### Resume Detection: Check State File

```bash
# At start of migration, check for existing state file
STATE_FILE="$PROJECT_PATH/.mca2-jdk-migration-state.json"

if [ -f "$STATE_FILE" ]; then
  log "├─ Found existing migration state file"

  # Parse state to find last completed phase
  if command -v jq > /dev/null 2>&1; then
    LAST_COMPLETED=$(jq -r '[.phases | to_entries[] | select(.value.status == "completed") | .key] | last' "$STATE_FILE")
    IN_PROGRESS=$(jq -r '[.phases | to_entries[] | select(.value.status == "in_progress") | .key] | first' "$STATE_FILE")
  else
    # Python fallback
    LAST_COMPLETED=$(python3 << PYEOF
import json
with open("$STATE_FILE") as f:
    state = json.load(f)
completed = [k for k, v in state['phases'].items() if v['status'] == 'completed']
print(completed[-1] if completed else '')
PYEOF
)
    IN_PROGRESS=$(python3 << PYEOF
import json
with open("$STATE_FILE") as f:
    state = json.load(f)
in_prog = [k for k, v in state['phases'].items() if v['status'] == 'in_progress']
print(in_prog[0] if in_prog else '')
PYEOF
)
  fi

  if [ -n "$IN_PROGRESS" ]; then
    log "│  └─ Migration was interrupted during $IN_PROGRESS"
    log "│  └─ Will resume from $IN_PROGRESS"
    RESUME_FROM_PHASE="$IN_PROGRESS"
  elif [ -n "$LAST_COMPLETED" ]; then
    # Extract phase number and add 1
    LAST_NUM=$(echo "$LAST_COMPLETED" | sed 's/phase_//')
    NEXT_NUM=$((LAST_NUM + 1))
    RESUME_FROM_PHASE="phase_$NEXT_NUM"
    log "│  └─ Last completed: $LAST_COMPLETED"
    log "│  └─ Will resume from $RESUME_FROM_PHASE"
  else
    log "│  └─ No completed phases found, starting from phase_0"
    RESUME_FROM_PHASE="phase_0"
  fi
else
  log "├─ No existing state file, starting fresh migration"
  RESUME_FROM_PHASE="phase_0"
fi
```

## Benefits of State File Approach

1. **Accurate resume**: Know exactly which phase to resume from
2. **Audit trail**: Complete history of what was done and when
3. **Idempotency**: Can safely re-run migration without duplicating work
4. **Debugging**: Can see exactly where migration failed
5. **Rollback support**: Have commit SHAs for each phase to rollback if needed
6. **No heuristics**: Don't need to guess if OpenRewrite ran by checking javax imports

## State File as Single Source of Truth

**IRON LAW**: The state file is the ONLY authoritative record of migration progress.

**NEVER use heuristics:**
- ❌ DO NOT check for jakarta imports to determine if OpenRewrite ran
- ❌ DO NOT check for Apache HttpClient imports to determine if Phase 5 should run
- ❌ DO NOT examine file contents to decide if a phase is complete
- ❌ DO NOT make assumptions based on Java version or other environmental checks

**ALWAYS trust state.json:**
- ✅ Check `phases.phase_N.status` at the start of every phase
- ✅ If status is "completed" or "skipped", skip the phase immediately
- ✅ If status is "pending" or "in_progress", execute the phase
- ✅ For Phase 5, check `will_execute` field (set in Phase 0)

**Why this is critical**: A previous migration attempt may have partially modified the codebase, leaving it in an intermediate state. Heuristics like "check for jakarta imports" will give false positives. Only the state file knows what actually completed successfully.

## State File in .gitignore

Add to `.gitignore`:
```
.mca2-jdk-migration-state.json
```

The state file is local workspace state, not source code. Each developer's migration is independent.

## Cleanup

After successful Phase 8 (push & MR creation), the state file can optionally be removed:

```bash
# Optional: Remove state file after successful migration
if [ "$ALL_PHASES_COMPLETE" = "true" ]; then
  rm -f "$STATE_FILE"
  log "├─ Removed migration state file (migration complete)"
fi
```

Or keep it as a record of the migration that was performed.
