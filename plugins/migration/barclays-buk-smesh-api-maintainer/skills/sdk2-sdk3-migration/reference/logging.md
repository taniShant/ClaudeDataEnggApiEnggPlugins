# Migration Logging Convention

All sdk3-migration agents write to `{PROJECT_PATH}/logs/migration.log`.

## Log Rotation (sdk3-migrate.md startup only)

Run once at the very start of a new migration run before any agent is spawned:

```bash
mkdir -p "{PROJECT_PATH}/logs"
if [ -f "{PROJECT_PATH}/logs/migration.log" ]; then
    mv "{PROJECT_PATH}/logs/migration.log" \
       "{PROJECT_PATH}/logs/migration_$(date '+%d%m%y%H%M').log"
fi
touch "{PROJECT_PATH}/logs/migration.log"
```

## Log Entry Format

```
[DD/MM/YY HH:MM:SS] [AGENT:<agent-name>] [<LEVEL>] <message>
```

Levels:
- `START`    — agent invoked, inputs received
- `INFO`     — significant action taken (file changed, test fixed, phase done)
- `SKIP`     — work item skipped because already completed in a prior run
- `WARN`     — recoverable issue encountered
- `ERROR`    — failure that blocked progress
- `COMPLETE` — agent finished, summary stats

## Bash Helper (copy into each agent that uses Bash)

```bash
MIGRATION_LOG="{PROJECT_PATH}/logs/migration.log"
log() { echo "[$(date '+%d/%m/%y %H:%M:%S')] [AGENT:{AGENT_NAME}] $1" >> "$MIGRATION_LOG"; }
```

Replace `{AGENT_NAME}` with the agent's actual name, e.g. `spring-conventions-agent`.

## Example Entries

```
[25/02/26 10:01:03] [AGENT:sdk3-migration-agent]   [START]    CARDOPSAPI-1234 — Project: /home/user/my-api
[25/02/26 10:01:10] [AGENT:spring-conventions-agent] [INFO]    MyService.java: constructor injection applied
[25/02/26 10:01:11] [AGENT:spring-conventions-agent] [SKIP]    OrderGateway.java: already completed in prior run
[25/02/26 10:02:45] [AGENT:test-writer-agent]        [INFO]    PaymentService: 14 tests written, all green
[25/02/26 10:02:45] [AGENT:test-writer-agent]        [ERROR]   FeeCalculator: compileTestJava failed — ClassNotFound FeeRepository
[25/02/26 10:05:00] [AGENT:coverage-orchestrator-agent] [COMPLETE] Wave 2 done — line 93%, mutation 91%
```

## Resume Convention

Every agent that processes discrete work units (files, test classes, phases) uses TaskCreate/TaskUpdate to persist state so it can resume if interrupted:

- Call `TaskList()` at startup — find tasks from a prior run matching this agent's subject prefix
- Tasks with `completed` status → log `[SKIP]` and exclude from work list
- Tasks with `in_progress` status → were interrupted; reset to `pending` and re-process
- No matching tasks → fresh run; create tasks and process normally
