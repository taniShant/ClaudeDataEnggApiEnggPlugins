---
description: "Data modelling rules and quality gates for BUK target data model design — denormalization policy, composite key standards, audit column requirements, SCD2 temporal conventions, and naming rules enforced by the DM agents."
user-invocable: false
owner: "Satish Khanna <satish.khanna@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-21
---

**Source:** Tom Franklin | **Owner:** tom.franklin@barclays.com | **Review:** Quarterly | **Last reviewed:** N/A

# DM Modelling Standards

Data modelling rules, naming conventions, and quality gates for BUK target data model design.

---

## Rule 1: Denormalize

Embed related dimensions into core tables; minimize JOINs.

- Merge 1:1 related attributes into the parent table (no separate ACCOUNT table when PRODUCT_HOLDING already has account grain)
- Trade-off: Slightly larger rows ↔ dramatically faster queries (fewer JOINs)
- **Guideline**: When a 1:1 relationship exists and attributes are always queried together, merge them
- Document rationale if keeping a separate table despite 1:1 relationship

---

## Rule 2: Composite Keys (NO Surrogates)

All primary keys must be business keys — never surrogates.

**✅ Correct:**
```sql
PRIMARY KEY (customer_identifier, product_identifier, account_identifier, eff_start_date)
```

**❌ Forbidden:**
```sql
holding_id BIGINT PRIMARY KEY AUTO_INCREMENT
assessment_id BIGINT PRIMARY KEY
flag_id SERIAL
```

**Rationale:** Full data lineage, regulatory auditability, self-documenting schema.

---

## Rule 3: Dimension Audit Columns (5 Required)

All non-fact tables MUST include these 5 columns:

| Column | Data Type | Purpose |
|--------|-----------|---------|
| `eff_start_date` | DATE | SCD Type 2 — record effective from |
| `eff_end_date` | DATE | SCD Type 2 — record effective until (NULL = current) |
| `dw_lod_tmp` | TIMESTAMP_NTZ | Data warehouse load timestamp |
| `dw_upd_lod_tmp` | TIMESTAMP_NTZ | Data warehouse update timestamp |
| `active` | CHAR(1) | '1' = current record, '0' = historical |

**❌ Forbidden:** `created_at`, `updated_at` (old pattern, replaced by new standards)

---

## Rule 4: Fact Audit Columns (2 Required)

All fact/event tables MUST include these 2 columns:

| Column | Data Type | Purpose |
|--------|-----------|---------|
| `dw_lod_tmp` | TIMESTAMP_NTZ | Data warehouse load timestamp |
| `dw_bus_dt` | DATE | Immutable business date (assessment date, transaction date, event date) |

**❌ Forbidden on fact tables:** `eff_end_date`, `updated_at`, `created_at`, or any dimension-style tracking. Facts are immutable — no history tracking.

---

## Rule 5: KPI Normalized Pattern

All KPI/metric aggregations MUST use a two-table normalized structure producing **TALL tables, not WIDE tables**. The `measure_identifier` makes the fact table tall (one ROW per measure per grain) rather than wide (one COLUMN per measure).

### A. Fact Table (KPI values — generic numbered columns)

```sql
CREATE TABLE FACT_*_KPI (
    reporting_period_end_date    DATE NOT NULL,
    reporting_period_type_code   VARCHAR(20) NOT NULL,
    customer_segment_code        VARCHAR(20) NOT NULL,
    measure_identifier           VARCHAR(50) NOT NULL,    -- FK to metric registry
    measure_value_1              NUMERIC(19,6),            -- Generic value slot 1 (meaning defined in metric register)
    measure_value_2              NUMERIC(19,6),            -- Generic value slot 2 (meaning defined in metric register)
    measure_volume_1             INTEGER,                   -- Generic volume slot 1 (meaning defined in metric register)
    measure_volume_2             INTEGER,                   -- Generic volume slot 2 (meaning defined in metric register)
    dw_lod_tmp                   TIMESTAMP_NTZ NOT NULL,
    dw_bus_dt                    DATE NOT NULL,
    PRIMARY KEY (reporting_period_end_date, reporting_period_type_code,
                 customer_segment_code, measure_identifier),
    FOREIGN KEY (measure_identifier) REFERENCES DIM_*_METRIC_REGISTER(measure_identifier)
);
```

### B. Metric Register Dimension (SCD Type 2)

```sql
CREATE TABLE DIM_*_METRIC_REGISTER (
    measure_identifier           VARCHAR(50) NOT NULL,
    eff_start_date               DATE NOT NULL,
    measure_name                 VARCHAR(200),
    measure_description          VARCHAR(500),
    measure_unit_name            VARCHAR(50),              -- 'Count', 'Percentage', 'Ratio', 'Amount'
    measure_description_value_1  VARCHAR(200),              -- What measure_value_1 holds for this measure
    measure_description_value_2  VARCHAR(200),              -- What measure_value_2 holds for this measure
    measure_description_volume_1 VARCHAR(200),              -- What measure_volume_1 holds for this measure
    measure_description_volume_2 VARCHAR(200),              -- What measure_volume_2 holds for this measure
    active                       CHAR(1) NOT NULL DEFAULT '1',
    eff_end_date                 DATE,
    dw_lod_tmp                   TIMESTAMP_NTZ NOT NULL,
    dw_upd_lod_tmp               TIMESTAMP_NTZ NOT NULL,
    PRIMARY KEY (measure_identifier, eff_start_date)
);
```

**❌ Forbidden:** Wide denormalized KPI tables with hardcoded metric columns (e.g., `live_customer_count`, `digital_30day_active_count` as individual columns). Also forbidden: `measure_value` (singular) — must use numbered: `measure_value_1`.

**Why:** New KPIs = new rows (not schema changes), centralised metric metadata, SCD Type 2 tracks definition changes, scales indefinitely.

---

## Entity Classification: Logical Only vs. Physical

After FDP discovery, classify every dimension table:

| Condition | Classification | Output Treatment |
|---|---|---|
| 1:1 grain match with single FDP table AND ≥80% attributes reused | **Logical Only** | Simplified — no data type, nullability, PK/FK detail |
| ≥70% FDP reuse (even with 5-6 derived attributes) | **Logical Only** | Derived attrs embedded in fact or thin derived dimension |
| Multiple FDP entities merged (denormalization) | **Physical** | Full DDL-style definition |
| FDP entity extended with >20% derived attributes | **Physical** | Full DDL-style definition |
| No FDP match — entirely new concept | **Physical** | Full DDL-style definition |
| KPI fact table or metric register | **Physical** | Full DDL-style definition |

**Derived attribute handling for Logical Only entities:**
- **Option A (Preferred):** Embed derived attributes in fact tables that use them
- **Option B:** Create a thin derived dimension (SCD Type 2) with ONLY calculated columns + audit columns

---

## Table Consolidation by Reporting Grain

**PRINCIPLE:** Minimize table count by consolidating fact tables that share the same dimensional key structure but differ only in reporting frequency.

**Rule:** Use `reporting_period_type_code` ('D', 'W', 'M', 'Q') and `reporting_period_end_date` to distinguish frequencies within a single table.

**Consolidate when:**
- Same dimensional structure (same product, segment, customer keys)
- Different reporting frequencies (daily, weekly, monthly, quarterly)
- Shared business concepts

**Do NOT consolidate when:**
- Different dimensional structures
- Fundamentally different purposes
- Contradictory business logic

---

## Naming Conventions

### Case

All table and column names: **UPPER_SNAKE_CASE**

### No Abbreviations

Use complete business terminology. No abbreviations unless enterprise-standard.

| ❌ Avoid | ✅ Use |
|----------|--------|
| `cust_id` | `customer_identifier` |
| `app_rcvd_dt` | `application_received_date` |
| `prd_sts_cd` | `product_status_code` |
| `txn_ts` | `transaction_datetime` |

### Grain-Reflective Naming

Table names must reflect the grain entity. Column names must explicitly reflect which grain entity they belong to.

- Table at account grain: `CUSTOMER_ACCOUNT_HOLDING` (not `PRODUCT_HOLDING` when account_id is in PK)
- Column from product master at account grain: `account_product_status` (not `product_status`)

**When to Prefix Columns:**
- Grain is per **account** but column is from **product** master → `account_product_status`
- Grain is per **customer** but column is from **account** master → `customer_account_status`
- Grain is per **account** and column IS about account → `account_status` (no extra prefix)

### Table Name Patterns

| Pattern | Example | Usage |
|---------|---------|-------|
| Single-entity grain | `CUSTOMER_PROFILE` | Per customer |
| Multi-entity grain | `CUSTOMER_ACCOUNT_HOLDING` | Per customer + account |
| Fact tables | `TRANSACTION_FACTS` | Per transaction |
| Reference data | `ELIGIBILITY_RULE_REFERENCE` | Lookup table |
| Metric register | `DIM_*_METRIC_REGISTER` | KPI definitions |

---

## Class Words

Every attribute must use the appropriate class word:

| Business Meaning | Class Word | Example | ❌ Avoid |
|------------------|------------|---------|----------|
| Unique identifier | `*_identifier` | `customer_identifier` | `cust_id` |
| Name/description | `*_name` | `broker_name` | `broker_nm` |
| Status/state | `*_status_code` | `account_status_code` | `status` |
| Category/type | `*_type_code` | `product_type_code` | `product_type` |
| Binary yes/no | `is_*_indicator` | `is_joint_account_indicator` | `flag`, `yn` |
| Monetary amount | `*_amount` | `fee_amount` | `fee` |
| Date | `*_date` | `completion_date` | `completion_dt` |
| Timestamp | `*_datetime` | `transaction_datetime` | `txn_ts` |
| Percentage/rate | `*_rate` | `interest_rate` | `int_pct` |
| Sequence/version | `*_number` | `version_number` | `version_id` |

**Critical:** Boolean attributes MUST use `is_*_indicator`, never `flag`, `yn`, or `status`.

---

## Data Types

| Business Concept | Data Type | Precision/Scale | Notes |
|------------------|-----------|-----------------|-------|
| Monetary amounts | NUMERIC | (19,6) | GBP — 6 decimal places |
| Percentages/rates | NUMERIC | (8,3) | Precise rate values |
| Counts | INTEGER or BIGINT | — | Never use for identifiers |
| Dates | DATE | — | No time component |
| Timestamps | TIMESTAMP_NTZ | — | Point-in-time; UTC only |
| Text | VARCHAR(length) | — | Names, codes, descriptions |
| Binary flags | CHAR(1) | — | '0' or '1' only |

---

## Mermaid ER Diagram Rules

Mermaid diagrams contain **ONLY table and column names** — **NO descriptions, definitions, data types, or comments**.

**❌ Wrong:**
```
CUSTOMER_PROFILE {
    string customer_id PK "Unique customer identifier"
}
```

**✅ Correct:**
```
CUSTOMER_PROFILE {
    string customer_id PK
}
```

All business descriptions belong in the Table Definitions section, not in diagram code.

---

## Key Identifier Types

| Identifier | Meaning | Data Type |
|------------|---------|-----------|
| `CUSTOMER_IDENTIFIER` | Unique customer in BUK | BIGINT |
| `ACCOUNT_IDENTIFIER` | Unique account for a customer | BIGINT |
| `APPLICATION_IDENTIFIER` | Unique application/product request | BIGINT |
| `TRANSACTION_IDENTIFIER` | Unique transaction/event | BIGINT |

---

## Agent Self-Check

Before delivering a data model, verify:

- [ ] **Rule 1 — Denormalize**: No separate 1:1 tables without documented rationale
- [ ] **Rule 2 — Composite Keys**: Zero surrogate keys (`*_id AUTO_INCREMENT`, `*_KEY`)
- [ ] **Rule 3 — Dimension Audit Columns**: All non-fact tables have exactly 5 audit columns (`eff_start_date`, `eff_end_date`, `dw_lod_tmp`, `dw_upd_lod_tmp`, `active`)
- [ ] **Rule 4 — Fact Audit Columns**: All fact tables have exactly 2 audit columns (`dw_lod_tmp`, `dw_bus_dt`)
- [ ] **Rule 5 — KPI Pattern**: If KPIs present, two-table normalized structure exists (fact + metric register)
- [ ] **UPPER_SNAKE_CASE**: All table and column names
- [ ] **No abbreviations**: Full business terminology throughout
- [ ] **Grain-reflective names**: Table and column names reflect actual grain entity
- [ ] **Class words applied**: `*_identifier`, `*_amount`, `*_date`, `is_*_indicator`, `*_status_code`, `*_type_code`
- [ ] **Data types correct**: NUMERIC(19,6) for money, DATE for dates, TIMESTAMP_NTZ for timestamps, CHAR(1) for flags
- [ ] **Mermaid clean**: Diagrams contain only names — no descriptions, definitions, or data types
- [ ] **Mermaid yellow background**: Logical Only entities have `#FFFFCC` background
- [ ] **Every data point assigned**: All DP-XX entries mapped to a table/column
- [ ] **Every business rule mapped**: All BR-XX entries represented in model (or metric register if KPI)
- [ ] **Relationships documented**: Explicit cardinality (1:1, 1:M, M:M) with join conditions
- [ ] **SCD strategy stated**: Type 2 for dimensions, immutable for facts
- [ ] **FDP alignment**: FDP entities scanned, matched entities reuse grain and attributes, deviations documented
- [ ] **Entity classification**: Every dimension classified as Logical Only (≥70% FDP reuse) or Physical
- [ ] **Table consolidation**: Same-grain fact tables consolidated using `reporting_period_type_code`
- [ ] **No unnecessary Physical tables**: No Physical classification when ≥70% FDP attribute reuse
