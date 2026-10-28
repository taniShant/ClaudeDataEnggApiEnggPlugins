# Detox Observability — Database Schema

> Schema definitions for the Detox telemetry data. Share these with the DB team to create tables in any database engine.

---

## Schema Files

| File | Description | Row Volume |
|---|---|---|
| [`detox-pipeline-runs-schema.json`](detox-pipeline-runs-schema.json) | **Primary table.** One row per pipeline run. Contains all metrics: vulnerability counts, fix outcomes, validation rates, test results, phase timing, cost estimates, and governance flags. | ~1-50 rows/day (one per `/barclays-buk-detox:remediate` invocation) |
| [`detox-otel-events-schema.json`](detox-otel-events-schema.json) | Granular event log. One row per telemetry event (phase transitions, fix attempts, validation results, test outcomes, errors). OTel-native format with TraceId/SpanId for distributed tracing. | ~20-200 rows per pipeline run |
| [`detox-identity-schema.json`](detox-identity-schema.json) | Identity context. WHO ran the pipeline and WHAT repo was targeted. Embedded in both tables above, but defined separately for normalization if needed. | Embedded (not a standalone table unless normalized) |

---

## Data Flow

```
Developer runs /barclays-buk-detox:remediate
        │
        ├─► identity.py resolves WHO + WHAT REPO
        │
        ├─► Pipeline executes 9 stages
        │       │
        │       ├─► telemetry.py emits OTel events ──► detox_otel_events table
        │       │
        │       └─► pipeline_state.py auto-injects phase timestamps
        │
        └─► run_recorder.py builds summary ──────────► detox_pipeline_runs table
                │
                └─► otel_exporter.py + observe_batch.py (+ plugin_observability.py)
                        │   at run end: send 'detox.pipeline_run' + all
                        │   'detox.<event_type>' events in ONE gRPC OTLP batch
                        └─► Barclays Collector → FluentBit → CloudWatch → Observe
                                (dataset: claude_code_client)
```

---

## Recommended Table Design

### Option A: Two Tables (Recommended)

| Table | Primary Key | Source Schema | Purpose |
|---|---|---|---|
| `detox_pipeline_runs` | `job_id` (VARCHAR 8) | `detox-pipeline-runs-schema.json` | Dashboards, reporting, remediation-effectiveness metrics |
| `detox_otel_events` | `detox.event_id` (VARCHAR 12) | `detox-otel-events-schema.json` | Drill-down, debugging, distributed tracing |

**Relationship:** `detox_otel_events.detox.job_id` → `detox_pipeline_runs.job_id` (many-to-one)

### Option B: Normalized (5 Tables)

For larger scale or if the DB team prefers normalization:

| Table | Primary Key | Derived From |
|---|---|---|
| `detox_pipeline_runs` | `job_id` | Top-level fields from pipeline-runs-schema |
| `detox_run_phases` | `job_id` + `phase_number` | `phases` object (extracted into rows) |
| `detox_run_errors` | `job_id` + `phase` | `errors` array (extracted into rows) |
| `detox_run_cwes` | `job_id` + `cwe_id` | `cwes_targeted` array (extracted into rows) |
| `detox_otel_events` | `event_id` | OTel events schema |

---

## Field Type Mapping Guide

For the DB team to map JSON Schema types to their database engine:

| JSON Schema Type | PostgreSQL | Oracle | SQL Server | MySQL |
|---|---|---|---|---|
| `string` | `VARCHAR(N)` / `TEXT` | `VARCHAR2(N)` | `NVARCHAR(N)` | `VARCHAR(N)` |
| `string` (format: date-time) | `TIMESTAMPTZ` | `TIMESTAMP WITH TIME ZONE` | `DATETIMEOFFSET` | `DATETIME(3)` |
| `string` (format: uri) | `TEXT` | `VARCHAR2(4000)` | `NVARCHAR(2048)` | `VARCHAR(2048)` |
| `string` (format: email) | `VARCHAR(320)` | `VARCHAR2(320)` | `NVARCHAR(320)` | `VARCHAR(320)` |
| `integer` | `INTEGER` / `BIGINT` | `NUMBER(10)` | `INT` / `BIGINT` | `INT` / `BIGINT` |
| `number` (0.0–1.0) | `NUMERIC(4,3)` | `NUMBER(4,3)` | `DECIMAL(4,3)` | `DECIMAL(4,3)` |
| `number` (USD) | `NUMERIC(10,2)` | `NUMBER(10,2)` | `DECIMAL(10,2)` | `DECIMAL(10,2)` |
| `boolean` | `BOOLEAN` | `NUMBER(1)` | `BIT` | `TINYINT(1)` |
| `array` | `JSONB` | `CLOB` (JSON) | `NVARCHAR(MAX)` (JSON) | `JSON` |
| `object` | `JSONB` | `CLOB` (JSON) | `NVARCHAR(MAX)` (JSON) | `JSON` |
| `null` | Use nullable columns | Use nullable columns | Use nullable columns | Use nullable columns |

---

## Suggested Indexes

### detox_pipeline_runs

| Index | Columns | Purpose |
|---|---|---|
| PK | `job_id` | Primary key |
| IX_runs_repo | `repo_name`, `started_at` | Filter by repo + time range |
| IX_runs_user | `user_name`, `started_at` | Filter by user + time range |
| IX_runs_status | `status`, `started_at` | Find failures in time window |
| IX_runs_time | `started_at` | Time-series queries, retention |

### detox_otel_events

| Index | Columns | Purpose |
|---|---|---|
| PK | `Attributes.detox.event_id` | Primary key |
| IX_events_job | `Attributes.detox.job_id` | Join to pipeline_runs |
| IX_events_trace | `TraceId` | Distributed tracing lookups |
| IX_events_type_time | `Attributes.detox.event_type`, `Timestamp` | Filter events by type + time |
| IX_events_time | `Timestamp` | Time-series queries, retention |

---

## Key Constraints and Rules

1. **`job_id` is the primary key** for pipeline runs — 8 hex characters, unique per run
2. **`detox.event_id` is the primary key** for OTel events — 12 hex characters, unique per event
3. **`TraceId`** links all events from the same pipeline run (32 hex chars, derived from `job_id`)
4. **Nullable fields**: `ci_job_id`, `ci_pipeline_id`, `pr_url`, `validation_pass_rate`, `total_duration_ms`, `started_at` can be null
5. **JSON columns**: `vulns_by_severity`, `vulns_by_type`, `cwes_targeted`, `phases`, `errors`, `flags_raised` are structured JSON — store as JSONB/JSON or normalize into child tables
6. **No customer PII**: these schemas contain only operational identity (developer git config, CI metadata). No PAN, sort codes, NI numbers, DOB, customer emails, or customer names per `barclays-buk-standards:observability`
7. **Idempotency**: `job_id` has a uniqueness constraint — duplicate inserts for the same pipeline run should be handled with `ON CONFLICT DO NOTHING` / `MERGE`
8. **Retention**: recommend 365-day retention on `detox_otel_events` (high volume), indefinite on `detox_pipeline_runs` (low volume, needed for effectiveness/trend reporting)

---

## Sample Data

### Pipeline Run Record (one row)

```json
{
  "job_id": "a1b2c3d4",
  "command": "remediate",
  "started_at": "2026-09-14T10:00:00Z",
  "ended_at": "2026-09-14T10:12:30Z",
  "total_duration_ms": 750000,
  "status": "completed",
  "user_name": "Devesh Kumar",
  "user_email": "devesh.kumar@barclays.com",
  "ci_job_id": null,
  "model": "sonnet",
  "project_path": "/home/user/repos/payments-gateway",
  "repo_name": "payments-gateway",
  "severity_filter": "all",
  "dry_run": false,
  "vulns_total": 12,
  "vulns_by_severity": {"high": 5, "medium": 7},
  "vulns_by_type": {"code_fix": 10, "infra_config": 2},
  "cwes_targeted": ["CWE-79", "CWE-89", "CWE-798"],
  "fixes_attempted": 12,
  "fixes_succeeded": 10,
  "fixes_failed": 1,
  "fixes_skipped": 1,
  "retries_total": 3,
  "validation_pass_count": 9,
  "validation_fail_count": 1,
  "validation_pass_rate": 0.9,
  "tests_generated": 8,
  "tests_passed": 7,
  "tests_failed": 1,
  "pr_created": true,
  "pr_url": "https://app.gitlab.barcapint.com/group/payments-gateway/-/merge_requests/42",
  "agent_invocations": 15,
  "flags_raised": [],
  "self_check_passed": true,
  "phases": {
    "1": {"status": "completed", "started_at": "2026-09-14T10:00:05Z", "ended_at": "2026-09-14T10:00:30Z", "duration_ms": 25000},
    "2": {"status": "completed", "started_at": "2026-09-14T10:00:30Z", "ended_at": "2026-09-14T10:01:00Z", "duration_ms": 30000},
    "4": {"status": "completed", "started_at": "2026-09-14T10:01:15Z", "ended_at": "2026-09-14T10:05:00Z", "duration_ms": 225000}
  },
  "errors": [],
  "cio": "DIGITAL",
  "plugin_version": "2.6.2"
}
```

### OTel Event Record (one row)

```json
{
  "Timestamp": "2026-09-14T10:03:15.456Z",
  "SeverityText": "INFO",
  "SeverityNumber": 9,
  "Body": "Event: fix.applied",
  "TraceId": "a1b2c3d4000000000000000000000000",
  "SpanId": "e7f3a9b1c2d4e5f6",
  "Resource": {
    "service.name": "detox",
    "service.version": "2.6.2",
    "deployment.environment": "local",
    "barclays_cio": "DIGITAL"
  },
  "Attributes": {
    "detox.event_type": "fix.applied",
    "detox.job_id": "a1b2c3d4",
    "detox.event_id": "f3a9b1c2d4e5",
    "detox.phase": 4,
    "detox.user.name": "Devesh Kumar",
    "detox.cio": "DIGITAL",
    "detox.repo_name": "payments-gateway",
    "detox.cwe_id": "CWE-79",
    "detox.file_path": "src/main/java/Controller.java",
    "detox.commit_sha": "abc1234"
  }
}
```

---

## Version

| Field | Value |
|---|---|
| Schema version | `1` |
| Plugin version | `2.6.2` |
| Generated | 2026-10-14 |
| Author | Detox Platform Engineering |
