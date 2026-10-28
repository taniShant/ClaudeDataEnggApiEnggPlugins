# fdpchnlcc Domain Knowledge

**Domain**: Contact Centre Channel (Foundation Data Product)
**Tenancy**: `fdpchnlcc`
**Data Product Type**: FDP — sourced from Contact Lens (Amazon Connect), CTR event streams, agent event streams, Amazon Lex (Digital Assistant), and GenAI RAG (Colleague Knowledge Assistant)
**Last Updated**: 2026-06-18

---

## Business Context

- The **Contact Centre** data product captures all inbound/outbound customer interactions via Amazon Connect (voice, chat, video channels). It serves as a foundational layer for downstream analytics, reporting, and business data products.
- **Contact Lens** is the AWS ML service layered on Amazon Connect providing real-time call analytics: sentiment, categories, issues detected, and transcript analysis.
- A **contact** represents a single customer interaction session (identified by `CONTACT_IDENTIFIER` from CTR). One customer call may involve multiple agent segments but shares one CONTACT_IDENTIFIER.
- An **agent metric** is a 30-minute interval performance measure (e.g., talk time, after-contact-work, hold time) derived from the agent event stream data.
- **Interaction Analytics** tags are Contact Lens ML outputs categorising conversations: Categories (e.g., "complaint", "churn risk"), Issues Detected (e.g., "billing dispute"), and Transcript segments with timing offsets.
- **Contact Channel Type** distinguishes VOICE, CHAT, and VIDEO interactions — always sourced from CTR `channel` field.
- **Digital Assistant (DA)** is a chatbot built with Amazon Lex (AI/NLP). Records interactions at request ID level (each message sent to/from DA gets a separate request ID). If not resolved, contact is transferred to the Contact Centre.
- **Colleague Knowledge Assistant (CKA)** is a RAG-based GenAI virtual assistant integrated with AWS Connect. Responds to colleague queries with summarised answers from knowledge articles. Used by BUK Customer Care colleagues during live calls.
- The `CONTACT_INITIATION_DATE` represents the date the customer interaction began — used as primary partition for analytics tables.

---

## SCD2 Team-Specific Notes

Only one SCD2 table exists: `AGENT_SCHEDULE_TYPE` — all other tables are **Transactional** (append-only).

> For full column-level detail on tables with 70+ columns (INTERACTION_DETAIL, DEMAND_SUMMARY), refer to the ER Studio `.DM1` file referenced in the ER Studio Logical Model Reference section below.

---

## Source System Details

### Source: Amazon Connect Contact Lens (via S3 landing)
- JSON files per contact, landed in S3 raw zone
- Fields extracted: Categories matched, issues detected, transcript segments with millisecond offsets
- JSON flattened into relational format — one row per tag/category per contact
- `LOWEST_MILLISECONDS`: BeginOffsetMillis at which a category first appeared in the transcript

### Source: CTR (Contact Trace Records)
- JSON records per contact lifecycle event from Amazon Connect
- `CONTACT_IDENTIFIER`, `CONTACT_CHANNEL_TYPE_NAME` (VOICE/CHAT/VIDEO), initiation timestamp, agent info, queue info
- Drives: CONTACT_CENTRE_INTERACTION_DETAIL, CONTACT_CENTRE_INTERACTION_SESSION_SUMMARY

### Source: Agent Event Stream
- Real-time event stream of agent state changes (AVAILABLE, CONNECTED, AFTER_CONTACT_WORK, etc.)
- Aggregated to 30-minute intervals for `AGENT_METRIC` table
- `SOURCE_SYSTEM_KEY`: Integer identifier for the source system feed

### Source: Amazon Lex (Digital Assistant)
- Event stream from Lex chatbot interactions
- Each user message generates a REQUEST_IDENTIFIER
- Conversations linked to Contact Centre via CONTACT_IDENTIFIER when transferred
- Drives: DIGITAL_ASSISTANT_CONVERSATION_DETAIL, DIGITAL_ASSISTANT_CONVERSATION_SUMMARY

### Source: CKA GenAI Service (Colleague Knowledge Assistant)
- RAG-based GenAI service integrated with AWS Connect agent workspace
- Captures query/response pairs with scoring and guardrail metadata
- Linked to contact via CONTACT_IDENTIFIER and agent via AGENT_IDENTIFIER
- Drives: COLLEAGUE_KNOWLEDGE_ASSISTANT_MESSAGE_DETAIL, COLLEAGUE_KNOWLEDGE_ASSISTANT_FEEDBACK_DETAIL

---

## Source System Quirks

### Partition Column Naming Inconsistency
- CKA tables (`COLLEAGUE_KNOWLEDGE_ASSISTANT_MESSAGE_DETAIL`, `COLLEAGUE_KNOWLEDGE_ASSISTANT_FEEDBACK_DETAIL`) use `DW_BUS_DATE` as the partition column — NOT `DW_BUS_DT` like all other tables in this tenancy. Exercise caution when applying cross-table partition filters.

### Source Data Volume
- **Agent Event Stream**: ~2–5M events/day (raw state changes before 30-min aggregation)
- **CTR (Contact Trace Records)**: ~200K–500K JSON records/day (one per contact lifecycle event)
- **Contact Lens JSON**: ~100K–500K files/day (one JSON per analysed contact, variable size 5KB–500KB depending on call duration)
- **Amazon Lex Events**: ~50K–200K events/day (each user utterance generates an event)
- **CKA Query/Response Events**: ~5K–20K events/day (lower volume — internal colleague usage only)
- **CKA Feedback Events**: ~1K–5K events/day (subset of messages that receive feedback)
- Total daily source ingest: ~3–6M raw events/files across all feeds
- Peak hours: 08:00–18:00 GMT (UK business hours); volume drops ~90% overnight

### NULL Patterns
- `AGENT_FIRST_NAME` / `AGENT_LAST_NAME`: NULL for automated/IVR agent IDs — valid
- `INTERACTION_ANALYTICS_TAG_VALUE`: NULL when tag type is binary (presence/absence) — valid
- `LOWEST_MILLISECONDS`: NULL for tags spanning the entire contact duration
- `CUSTOMER_IDENTIFIER` (DA Summary): NULL for unauthenticated chatbot sessions
- `CONTACT_IDENTIFIER` (CKA): NULL when colleague uses CKA outside of a live contact

### Type Quirks
- `METRIC_VALUE` is `DECIMAL(36,6)` — high precision for sub-second timing metrics
- `SOURCE_SYSTEM_KEY` in older Hive table is `BIGINT` — convert to `long` for Iceberg
- `CONTACT_IDENTIFIER` is always `STRING` (UUID from Amazon Connect)
- `GENERATED_RESPONSE_SCORE_NUMBER` (CKA) is `DECIMAL(12,8)` — ML confidence score

---

## Operational Hints for New Tables

1. **Broadcast hint**: Decode/lookup tables (INTERACTION_ANALYTICS_CATEGORY_CATALOG) are small — use `F.broadcast()`
2. **Worker sizing**: G.1X workers; 3–5 for BAU; 8–10 for Day 0 backfill
3. **Day 0 history**: Transactional tables require 24 months of historical data (see Day 0 Backfill Strategy below)

---

## Day 0 Backfill Strategy — Tranche-Based Processing

### Requirement

All **transactional tables** in this tenancy require **24 months of historical data** for the Day 0 (initial full load). The total data volume across source systems is **2–3 TB**, which exceeds the memory and execution time limits of a single Glue job run.

### Strategy: Date-Ranged Tranche Execution

Day 0 loads MUST be split into time-bounded tranches. Each tranche processes a contiguous date range (e.g., 1 month) and appends results to the target Iceberg table.

**Execution model:**
```
Tranche 1: start_date=2024-06-01, end_date=2024-06-30
Tranche 2: start_date=2024-07-01, end_date=2024-07-31
...
Tranche 24: start_date=2026-05-01, end_date=2026-05-31
```

### Code Generation Instructions

#### 1. Transform (Day 0) — Parameter Extraction from `param` String

The `_transform_day0` class receives `param` (comma-separated string) from the wrapper. Positional layout:

```
param[0] = operation    → day0
param[1] = table_type   → Transactional | Non-Transactional
param[2] = start_date   → YYYYMMDD (tranche start)
param[3] = end_date     → YYYYMMDD (tranche end)
```

The transform class MUST parse `start_date` and `end_date` from `param` and apply them as a source filter predicate:

```python
# Extract tranche dates from param string (positions 2 and 3)
params = self.param.split(',')
start_date = datetime.strptime(params[2].strip(), '%Y%m%d').date() if len(params) > 2 and params[2].strip() else None
end_date = datetime.strptime(params[3].strip(), '%Y%m%d').date() if len(params) > 3 and params[3].strip() else None

# Apply date range filter on source read (tranche mode)
if start_date and end_date:
    source_df = source_df.filter(
        (F.col("{{partition_date_column}}") >= F.lit(start_date)) &
        (F.col("{{partition_date_column}}") <= F.lit(end_date))
    )
```

- `{{partition_date_column}}` is the source date field used for filtering (typically `CONTACT_INITIATION_DATE`, `DW_BUS_DT`, or `REPORTING_DATE` depending on table)
- If both `start_date` and `end_date` are present in `param` → tranche mode (Day 0 backfill)
- If positions 2/3 are empty or absent → full-range mode (fallback; not recommended for this tenancy)

#### 2. Wrapper — No Change Required

The wrapper template already passes the full `param` string to the transform class via `common_args`. The DTXOG orchestrator populates `param` positions 2 and 3 with tranche dates when invoking Day 0. No wrapper modification is needed — tranche awareness lives entirely in the transform class.

#### 3. DTXOG Config — Tranche Param Passing

The DTXOG orchestration invokes the Glue job with `xtra-args.param` containing the tranche dates:

```
param = "day0,Transactional,20240601,20240630"
```

Each tranche invocation changes only positions 2 and 3. This is configured externally via the EventBridge + Lambda scheduler — the generated code does NOT manage tranche iteration internally.

#### 4. Orchestration — Sequential Tranche Invocation

Tranches are executed **sequentially** (not in parallel) to avoid write conflicts on the Iceberg table. Each tranche appends to the same target partition path. The EventBridge + Lambda scheduler handles tranche iteration externally.

#### 5. Worker Sizing for Tranche Execution

| Scenario | Worker Type | Worker Count | DPU |
|----------|-------------|--------------|-----|
| BAU (daily incremental) | G.1X | 3–5 | 3–5 |
| Day 0 tranche (1 month) | G.1X | 8–10 | 8–10 |
| Day 0 tranche (large table, e.g., INTERACTION_DETAIL) | G.2X | 8–10 | 16–20 |

#### 6. Idempotency Requirement

Each tranche execution MUST be idempotent — re-running the same `start_date`/`end_date` range must not create duplicate records. Implementation:

- For Iceberg tables: Use `MERGE INTO` or delete-then-insert pattern scoped to the tranche's date range
- For Hive tables (legacy): Overwrite partition corresponding to the date range

#### 7. Logging and Observability

Each tranche run MUST log:
- `start_date` and `end_date` processed
- Row count read from source
- Row count written to target
- Execution duration

This enables monitoring tranche progress across the 24-month backfill window.

### Tables Requiring Tranche Processing

All transactional tables in this tenancy require tranche-based Day 0:

| Table | Filter Column | Estimated Monthly Volume |
|-------|--------------|------------------------|
| CONTACT_CENTRE_INTERACTION_DETAIL | CONTACT_INITIATION_DATE | ~6–15M rows |
| CONTACT_CENTRE_INTERACTION_ANALYTICS | CONTACT_INITIATION_DATE | ~3–15M rows |
| CONTACT_CENTRE_INTERACTION_SESSION_SUMMARY | DW_BUS_DT | ~3–8M rows |
| CONTACT_CENTRE_DEMAND_SUMMARY | DW_BUS_DT | ~1–3M rows |
| AGENT_METRIC | DW_BUS_DT | ~60–150M rows |
| DIGITAL_ASSISTANT_CONVERSATION_DETAIL | DW_BUS_DT | ~1.5–6M rows |
| DIGITAL_ASSISTANT_CONVERSATION_SUMMARY | DW_BUS_DT | ~1.5–6M rows |
| COLLEAGUE_KNOWLEDGE_ASSISTANT_MESSAGE_DETAIL | DW_BUS_DATE | ~150K–600K rows |
| COLLEAGUE_KNOWLEDGE_ASSISTANT_FEEDBACK_DETAIL | DW_BUS_DATE | ~30K–150K rows |

**SCD2 table (`AGENT_SCHEDULE_TYPE`)** does NOT use tranche processing — it is low volume and loaded via standard full-compare SCD2 logic.

### Tranche Size Guidance

- Default tranche: **1 calendar month** (recommended for most tables)
- Large tables (INTERACTION_DETAIL, AGENT_METRIC): Consider **2-week tranches** if monthly exceeds memory limits
- Small tables (CKA_FEEDBACK_DETAIL): Can use **3-month tranches** if preferred for fewer invocations

---

## ER Studio Logical Model Reference

Maintained in: `ChannelsDataProduct-Logical_Model_v12 (4).DM1`

**Physical Models**:
- PhysicalModelPhase3A — Contact Centre core tables (AGENT_METRIC, INTERACTION_ANALYTICS, INTERACTION_DETAIL, SESSION_SUMMARY, DEMAND_SUMMARY, AGENT_SCHEDULE_TYPE, CATEGORY_CATALOG)
- Physical Model CC_CKA_v10 — CKA tables (MESSAGE_DETAIL, FEEDBACK_DETAIL)
- PhysicalModelPhase3B — Digital Assistant tables (CONVERSATION_DETAIL, CONVERSATION_SUMMARY)

**Submodels** (Logical):
- ContactCentre CDP (submodel 3)
- ContactCentre REALTIME BDP (submodel 4)
- Digital Assistant BDP (submodel 5)
- ContactCentre BDP (submodel 6)

Entity/attribute details stored as numeric IDs in ER Studio's internal format — refer to the .DM1 file for column-level detail when building mapping documents.

---

## Scheduling and Orchestration Hints

> **Note:** Scheduling details are domain-specific and should be confirmed with the Contact Centre data team. The hints below are defaults based on typical patterns.

### General Pattern (all Contact Centre tables)
- **Schedule type**: [UNKNOWN — resolve at /gen-dag time. Likely `business_calendar` for NonTransactional tables, `cron` for Transactional/BDP tables]
- **Bank holiday skip**: [UNKNOWN — confirm with domain team]
- **Sequential processing**: false
- **External dependencies**: BASE layer GCPR (DynamoDB) — source tables from `e_uk_chnlcc_db` must complete before DAG triggers
