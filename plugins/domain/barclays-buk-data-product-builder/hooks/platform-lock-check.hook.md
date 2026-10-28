# Hook: platform-lock-check

**Trigger**: PreToolUse on `Write|Edit` operations (fires before any file write/edit tool call)

**Purpose**: Block cross-platform commands. Ensure Glue-only commands are not run in a Databricks session and vice versa.

---

## Platform Lock Table

| Platform | Commands BLOCKED |
|---|---|
| `glue` | `/gen-driver`, `/gen-ddl` |
| `databricks` | `/gen-mesh`, `/gen-wrapper`, `/gen-dtxog` |

---

## Behaviour

### If platform is set and command is cross-platform blocked:

**Example — Glue session, Databricks command attempted:**
> "❌ `/gen-driver` is not available for the **AWS Glue** platform selected in this session.
> For Glue: use `/gen-wrapper` to generate wrapper.py.
> To switch to Databricks: start a new session with `/init`."

**Example — Databricks session, Glue command attempted:**
> "❌ `/gen-mesh` is not available for the **Databricks** platform selected in this session.
> For Databricks: use `/gen-ddl` to generate Iceberg table DDL.
> Mesh JSON and dtxog config are AWS Glue / DTX framework only."

### If platform is NOT yet set (G1 unresolved):

Block all generation commands:
> "⛔ Platform not set. Answer Gate G1 first: run `/init` and select Glue (A) or Databricks (B)."

### Allowed commands (no platform restriction):

`/init`, `/parse-mapping`, `/classify-sources`, `/identify-intent`, `/gen-transform`, `/gen-tests`, `/validate`, `/status`

---

## Immutability Rule

The `platform` field is set once at G1 and cannot be changed within a session. The platform lock is permanent for the session lifetime. To switch platforms, start a new session with `/init`.

---

## Audit Log

Every blocked command attempt is logged to `session/audit_log.jsonl` with:
- `event`: `platform_lock_violation`
- `attempted_command`: the command attempted
- `session_platform`: the current platform
- `timestamp`
