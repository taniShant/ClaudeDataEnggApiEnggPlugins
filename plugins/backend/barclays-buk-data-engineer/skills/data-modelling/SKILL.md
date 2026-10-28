---
name: data-modelling
description: Data modelling knowledge covering dimensional, relational, Data Vault 2.0, Data Product patterns, temporal modelling, and naming conventions
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# Data Modelling Skill

## Model Hierarchy

Data models are developed at three levels of abstraction:

| Level | Purpose | Audience | Tools |
|---|---|---|---|
| Conceptual | Business entities and relationships; technology-agnostic | Business stakeholders, architects | Entity-relationship diagrams, domain maps |
| Logical | Normalised entity definitions, attributes, keys, and relationships; technology-agnostic | Data architects, engineers | ER notation, logical data model tools |
| Physical | Platform-specific implementation: table definitions, indexes, partitioning, data types, constraints | Engineers | DDL, dbt models, Terraform |

Always build from conceptual to logical to physical. Do not jump directly to physical DDL without a validated logical model for non-trivial domains.

---

## Dimensional Modelling

Dimensional modelling is used for analytical and reporting workloads. It optimises for query performance and business user comprehension.

### Star Schema
A central fact table surrounded by denormalised dimension tables.

```
         DIM_DATE
            |
DIM_ACCOUNT -- FACT_TRANSACTION -- DIM_CUSTOMER
            |
         DIM_CHANNEL
```

- **Fact table**: stores measurable business events. Contains foreign keys to dimensions and additive numeric measures. Typically large.
- **Dimension table**: stores descriptive context about the event. Contains surrogate key, natural key, and descriptive attributes. Denormalised for query performance.

```sql
-- Fact table
CREATE TABLE fact_transaction (
    transaction_sk   BIGINT        NOT NULL,  -- surrogate key
    account_sk       BIGINT        NOT NULL,  -- FK to dim_account
    customer_sk      BIGINT        NOT NULL,  -- FK to dim_customer
    date_sk          INT           NOT NULL,  -- FK to dim_date
    channel_sk       BIGINT        NOT NULL,  -- FK to dim_channel
    amount           DECIMAL(18,2) NOT NULL,
    transaction_nk   VARCHAR(50)   NOT NULL,  -- natural/business key
    created_at       TIMESTAMP     NOT NULL
);

-- Dimension table
CREATE TABLE dim_account (
    account_sk       BIGINT        NOT NULL,
    account_nk       VARCHAR(50)   NOT NULL,
    account_type     VARCHAR(30),
    sort_code        CHAR(6),
    opened_date      DATE,
    status           VARCHAR(20),
    row_effective_dt DATE          NOT NULL,
    row_expiry_dt    DATE,
    is_current       BOOLEAN       NOT NULL
);
```

### Snowflake Schema
Normalise dimension tables into sub-dimensions. Use when dimension tables are very large or when normalisation of shared reference data is required. Avoid over-normalisation; the query cost of additional joins often outweighs storage savings in analytics platforms.

### Conformed Dimensions
A conformed dimension is shared across multiple fact tables and subject areas (e.g. `dim_date`, `dim_customer`). Conformed dimensions enable cross-subject-area analysis without data integration effort at query time.

### Slowly Changing Dimensions (SCD)

| Type | Description | Use When |
|---|---|---|
| SCD Type 0 | Attributes never change (retain original) | Reference data that must not change |
| SCD Type 1 | Overwrite with current value; no history | History not required; correct errors |
| SCD Type 2 | Add new row; expire old row; surrogate key required | Full history required |
| SCD Type 3 | Add previous-value column | Only one prior value required |
| SCD Type 4 | Current row in main table; history in separate history table | High-volatility attributes |
| SCD Type 6 | Combination of Type 1, 2, and 3 | Current and prior values visible on all rows |

SCD Type 2 is the most common. Implementation:

```sql
-- Expire the current row
UPDATE dim_account
SET
    row_expiry_dt = :effective_date - INTERVAL '1 day',
    is_current    = FALSE
WHERE account_nk = :account_nk AND is_current = TRUE;

-- Insert new version
INSERT INTO dim_account (account_sk, account_nk, account_type, sort_code, row_effective_dt, row_expiry_dt, is_current)
VALUES (nextval('dim_account_sk_seq'), :account_nk, :account_type, :sort_code, :effective_date, '9999-12-31', TRUE);
```

### Factless Fact Tables
A fact table with no numeric measures. Records the occurrence of an event or the relationship between dimensions.

```sql
-- Records that a customer was eligible for a product on a given date
CREATE TABLE fact_eligibility (
    customer_sk  BIGINT NOT NULL,
    product_sk   BIGINT NOT NULL,
    date_sk      INT    NOT NULL
);
```

### Bridge Tables
A bridge table resolves many-to-many relationships between a fact table and a multi-valued dimension.

```sql
-- A transaction can have multiple tags
CREATE TABLE bridge_transaction_tag (
    transaction_sk  BIGINT NOT NULL,
    tag_sk          BIGINT NOT NULL,
    PRIMARY KEY (transaction_sk, tag_sk)
);
```

### Degenerate Dimensions
Dimension attributes stored directly on the fact table because the dimension has only one attribute (typically a transaction or order number).

```sql
-- transaction_ref is a degenerate dimension — no separate dimension table needed
CREATE TABLE fact_payment (
    payment_sk      BIGINT,
    transaction_ref VARCHAR(50),  -- degenerate dimension
    account_sk      BIGINT,
    amount          DECIMAL(18,2)
);
```

---

## Relational Modelling

### Third Normal Form (3NF)
Data is in 3NF when:
1. It is in 2NF (no partial dependencies on a composite key).
2. Every non-key attribute is directly dependent on the primary key (no transitive dependencies).

Use 3NF for operational/transactional systems (OLTP). 3NF minimises redundancy and update anomalies.

### Boyce-Codd Normal Form (BCNF)
A stricter form of 3NF. Every determinant is a candidate key. Decompose tables where a non-key attribute determines part of the key.

### When to Denormalise
Denormalise in analytical/reporting models when:
- Join cost outweighs storage redundancy.
- Query performance requirements cannot be met with a normalised schema.
- The access pattern is read-heavy with infrequent updates.

Document denormalisation decisions with rationale. Partial denormalisation (keeping 3NF for dimensions, star schema for facts) is the standard analytical pattern.

---

## Data Vault 2.0

Data Vault 2.0 (DV2) is a methodology for building auditable, scalable, and flexible data warehouses. It separates structure (raw vault) from business rules (business vault).

### Core Constructs

**Hub**: stores unique business keys. One row per unique key value.
```sql
CREATE TABLE hub_account (
    hub_account_hk    CHAR(32)     NOT NULL PRIMARY KEY,  -- MD5/SHA-256 of business key
    load_dt           TIMESTAMP    NOT NULL,
    record_source     VARCHAR(100) NOT NULL,
    account_nk        VARCHAR(50)  NOT NULL               -- business/natural key
);
```

**Link**: stores relationships between hubs (many-to-many).
```sql
CREATE TABLE link_account_customer (
    lnk_account_customer_hk  CHAR(32)  NOT NULL PRIMARY KEY,
    load_dt                  TIMESTAMP NOT NULL,
    record_source            VARCHAR(100) NOT NULL,
    hub_account_hk           CHAR(32)  NOT NULL,
    hub_customer_hk          CHAR(32)  NOT NULL
);
```

**Satellite**: stores descriptive attributes and their history. Attached to a hub or link.
```sql
CREATE TABLE sat_account_details (
    hub_account_hk    CHAR(32)     NOT NULL,
    load_dt           TIMESTAMP    NOT NULL,
    load_end_dt       TIMESTAMP,
    record_source     VARCHAR(100) NOT NULL,
    hash_diff         CHAR(32)     NOT NULL,  -- hash of all attributes to detect changes
    account_type      VARCHAR(30),
    status            VARCHAR(20),
    sort_code         CHAR(6),
    PRIMARY KEY (hub_account_hk, load_dt)
);
```

### Business Vault
Applies business rules on top of the raw vault. Business vault constructs include:
- **Point-in-time (PIT) tables**: snapshot of satellite versions at specific timestamps to simplify querying across multiple satellites.
- **Bridge tables**: pre-join links and satellites to simplify access patterns.
- **Computed satellites**: derived or enriched attributes.

### Hash Key Generation
```python
import hashlib

def generate_hash_key(*args):
    combined = "||".join(str(a).upper().strip() if a is not None else "^^" for a in args)
    return hashlib.md5(combined.encode()).hexdigest().upper()
```

Always use a consistent, documented hashing algorithm across all DV constructs. MD5 is acceptable for non-security purposes; SHA-256 for higher collision resistance.

---

## Data Product Patterns

### Bounded Context
Define each data product within a bounded context: the domain owns its data model and exposes it via a well-defined interface. Consumers should not access internal tables directly.

### Data Contracts
A data contract defines the interface between a data producer and its consumers:
- Schema (column names, types, nullable flags).
- Semantics (what each field means).
- Quality guarantees (SLA, completeness, accuracy).
- Versioning and deprecation policy.

Store contracts as machine-readable artefacts (e.g. JSON Schema, Protobuf `.proto`, dbt model contracts) in version control.

### Schema-First Design
Define the schema before implementation. Schema changes must go through a change process and be communicated to consumers. Use semantic versioning for data contracts: `MAJOR.MINOR.PATCH`.

### Versioning
- **Non-breaking changes** (add nullable column, add optional field): increment MINOR version.
- **Breaking changes** (rename column, change type, drop column): increment MAJOR version and provide migration path.
- **Deprecated fields**: mark with metadata; retain for at least one deprecation cycle before removal.

### Consumer-Driven Contracts
Consumers express their schema expectations as tests. Producers must not break passing consumer contract tests. Implement consumer contract tests in the producer's CI pipeline.

---

## Entity-Relationship Notation

Use Crow's Foot notation for physical and logical ER diagrams:

| Symbol | Meaning |
|---|---|
| `|` (perpendicular line) | Exactly one (mandatory) |
| `o` (circle) | Zero (optional) |
| `<` (crow's foot) | Many |

Common cardinalities: one-to-one, one-to-many (most common), many-to-many (resolve with a junction/link table).

---

## Naming Conventions

### Physical Names (snake_case)
- Tables: `{subject_area}_{entity}` e.g. `dim_account`, `fact_transaction`, `hub_customer`
- Columns: `{attribute_name}` e.g. `account_id`, `transaction_ts`, `created_at`
- Surrogate keys: `{entity}_sk` e.g. `account_sk`
- Natural/business keys: `{entity}_nk` or `{entity}_id` e.g. `account_nk`, `customer_id`
- Hash keys (DV2): `{entity}_hk` e.g. `hub_account_hk`
- Foreign keys: `{referenced_entity}_sk` or `{referenced_entity}_id`
- Timestamp columns: suffix `_ts` for datetime e.g. `created_ts`, `event_ts`
- Date columns: suffix `_dt` or `_date` e.g. `effective_dt`, `birth_date`
- Boolean columns: prefix `is_` or `has_` e.g. `is_current`, `has_consent`

### Logical Names
Use full business terminology in logical models. Avoid abbreviations.

---

## Surrogate vs Natural Keys

| Aspect | Surrogate Key | Natural Key |
|---|---|---|
| Definition | System-generated (sequence, UUID) | Business-assigned identifier |
| Join performance | Numeric integer joins are faster | String/composite joins are slower |
| Stability | Stable; does not change if business key changes | Changes if business key is reassigned or corrected |
| PII risk | No | Possible (e.g. NI number, account number) |
| Recommendation | Preferred for dimension and hub tables | Use as lookup key; store alongside surrogate key |

Use surrogate keys as primary keys on dimension and hub tables. Always retain the natural key as a non-nullable column for traceability.

---

## Temporal Modelling

### Valid-Time (Fact History)
Records when a fact was true in the real world. Modelled as `valid_from_dt` and `valid_to_dt` columns.

### Transaction-Time (Audit History)
Records when a row was inserted or updated in the database. Modelled as `created_at` and `updated_at` columns. Enables complete audit trail.

### Bi-Temporal
Combines valid-time and transaction-time. Enables answering "what did we know at time T about facts that were true at time V?"

```sql
CREATE TABLE account_status_history (
    account_id        BIGINT    NOT NULL,
    status            VARCHAR(20) NOT NULL,
    -- Valid time
    valid_from_dt     DATE      NOT NULL,
    valid_to_dt       DATE      NOT NULL DEFAULT '9999-12-31',
    -- Transaction time
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at        TIMESTAMP,
    PRIMARY KEY (account_id, valid_from_dt, created_at)
);
```

---

## Hierarchy Modelling

| Pattern | Description | Pros | Cons |
|---|---|---|---|
| Adjacency list | Each row stores `parent_id` | Simple; easy to write | Recursive queries needed for tree traversal |
| Nested set | Stores `lft` and `rgt` integer bounds | Fast subtree reads | Expensive inserts/updates |
| Materialised path | Stores full path as a string | Simple tree traversal; human-readable | Path maintenance on restructure |
| Closure table | Separate table with all ancestor-descendant pairs | Fast queries; no recursion needed | Larger storage; synchronisation overhead |

For most use cases, use an **adjacency list** with recursive CTE queries. Use a **closure table** for deep, frequently-queried hierarchies.

---

## Audit Columns

Every physical table must include standard audit columns:

```sql
created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at    TIMESTAMP,
deleted_at    TIMESTAMP,   -- null = active; set = soft deleted
created_by    VARCHAR(100),
updated_by    VARCHAR(100)
```

## Soft Delete vs Hard Delete

| Approach | When to Use |
|---|---|
| Soft delete (set `deleted_at`) | Default for most business data. Preserves history. Allows recovery. Required for audit trails. |
| Hard delete | Only for data subject to erasure (GDPR right to erasure on PII). Must be documented and approved. |

Implement soft delete as the default. Add a standard filter `WHERE deleted_at IS NULL` to all views and default query patterns. For GDPR erasure, implement a documented hard delete or anonymisation procedure with an audit log of the deletion event.

---

## Polymorphism Patterns

For entities that share common attributes but have type-specific attributes, choose one of:

- **Single table inheritance**: one table with all attributes; type-specific columns are nullable. Simple; wastes storage; sparse columns.
- **Class table inheritance**: one table for common attributes; separate tables for type-specific attributes; joined by shared primary key.
- **Concrete table inheritance**: one table per subtype; no shared table. No joins required; common attribute changes must be applied to all tables.

Class table inheritance is generally preferred in data warehousing for clarity and maintainability.
