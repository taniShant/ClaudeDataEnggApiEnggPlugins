---
name: database-naming-standards
description: "Data engineering naming and security standards: database/table snake_case conventions, partition strategy (dw_bus_dt for transactional, active flag for SCD2), mandatory audit columns, Protegrity Data Element (DE) tokenization patterns for PII/PCI masking, and crypto secret naming. Use when generating DDL, defining table schemas, selecting partition columns, or implementing tokenization."
user-invocable: false
owner: "tom.franklin@barclays.com"
review_cadence: quarterly
last_reviewed: 2026-08-18
---

**Source:** Tom Franklin | **Owner:** tom.franklin@barclays.com | **Review:** Quarterly | **Last reviewed:** 2026-08-18

# Standards — Naming, Partitioning, Crypto

## Database & Table Naming

### Database Prefixes

| DP Type | Prefix | Example |
|---|---|---|
| FDP | `fdp_` | `fdp_uk_customer_db` |
| CDP | `cdp_` | `cdp_uk_customer_db` |
| BDP | `bdp_` | `bdp_uk_marketing_db` |
| Shared FDP | `shared_fdp_` | `shared_fdp_uk_customer_db` |
| Shared CDP | `shared_cdp_` | `shared_cdp_uk_customer_db` |
| Shared BDP | `shared_bdp_` | `shared_bdp_uk_analytics_db` |

> **Note:** Shared data products resolve to their parent type (FDP/CDP/BDP) for all routing, account, and source layer decisions.

### Table Naming Conventions

- Use snake_case (lowercase with underscores)
- Example: `customer_account`, `transaction_detail`, `complaints_summary`
- Never use CamelCase or spaces

### Iceberg Suffix Convention

- **Where to KEEP `_iceberg`** (logical references): Hive metastore database name, CREATE TABLE statements, Iceberg catalog references
- **Where to STRIP `_iceberg`** (S3 path components): S3 bucket paths, physical storage locations
- **Derivation**: `database_name_base = database_name.removesuffix('_iceberg')`
- Use `database_name_base` for ALL S3 path construction

### Partition Strategy

| Table Type | Partition Column | Purpose |
|---|---|---|
| Transactional (Append-only) | `dw_bus_dt` | Business date partition |
| Non-Transactional (SCD2) | `active` | Active/inactive rows (Y/N) |
| Non-Transactional (SCD1) | `dw_lod_tmp` | No active column (SCD1 overwrites); load timestamp provides temporal partitioning |

### Partition Strategy Rationale

| Table Type | Partition Column | Rationale |
|---|---|---|
| Transactional (Append-only) | `dw_bus_dt` | Business date drives query patterns; daily partition pruning for append-only tables |
| Non-Transactional (SCD2) | `active` | Binary partition enables fast "current state" queries via `active='1'` partition pruning |
| Non-Transactional (SCD1) | `dw_lod_tmp` | No active column (SCD1 overwrites in place); load timestamp provides temporal access pattern |

### Audit Columns

**Transactional Tables:**
```sql
dw_bus_dt --Business date partition
dw_lod_tmp TIMESTAMP  -- Load timestamp
```

**Non-Transactional Tables (SCD2):**
```sql
eff_start_date DATE         -- Effective start 
eff_end_date DATE           -- Effective end (SCD2 high-end: 3499-12-31)
dw_lod_tmp TIMESTAMP        -- Load timestamp
dw_upd_lod_tmp TIMESTAMP    -- Update load timestamp
active STRING               -- Y/N flag (partition column)
```

### Constants (Single Source of Truth)

| Constant | Value | Type | Purpose |
|----------|-------|------|---------|
| SCD2 high-end date | `3499-12-31` | DATE | Open-ended effective period sentinel |
| Active flag (current) | `'1'` | STRING | Currently active SCD2 row |
| Active flag (expired) | `'0'` | STRING | Historically expired SCD2 row |

These values are also declared in `configs/plugin.config.json` under `scd2_defaults`.
Agents MUST reference this skill rather than hardcoding these values inline.

---

## Protegrity Data Elements

### DE Naming Pattern

```
<Region>_TOK_<FuncAbbrev>_<Behavior>_<DataTypeRef>_DE
```

Example: `UK_TOK_ACCT_L0R0_NUM_DE` = UK + Account + Full Mask (L0R0) + Numeric

### Regions

- `UK` — UK deployment
- `US` — US deployment
- `APAC` — Asia-Pacific deployment

### Common PII/PCI Elements

| Element | FuncAbbrev | DataTypeRef | Common Behaviors |
|---|---|---|---|
| Name | NAME | ALN | L0R0, L6R4 |
| Address | ADDR | ALN | L0R0, L6R4 |
| Email | EML | ALN | L0R0, L4R0 |
| Phone | PHN | NUM | L0R0, L6R4 |
| Account Number | ACCT | NUM | L0R0, L6R4 |
| Card Number | CRD | NUM | L0R0, L6R4 |
| Date of Birth | DOB | DT | L0R0, L6R4 |

### Behavior Patterns (Masking)

- `L0R0` — Full mask (token covers entire value)
- `L4R0` — First 4 clear, rest masked
- `L6R4` — First 6 + last 4 clear, middle masked
- `L0R4` — First portion masked, last 4 clear

### DataType References

- `UNC` — Unclassified (mixed case)
- `ALN` — Alphanumeric
- `DEC` — Decimal/numeric
- `NUM` — Numeric (integers)
- `CC` — Credit card
- `EML` — Email address
- `DT` — Date/timestamp

### Free Text Variants

- `FTGEN2_ALN` — Alphanumeric free text (recommended for most cases)
- Restrict clear text to 1000 characters for Unicode data
- Validate storage capacity (tokens can be 4x source length)

### DE Validation & Implementation Best Practices

| Practice | Guideline |
|---|---|
| **DE Name Validation** | Always match extracted DE names against the pattern `(UK\|US\|APAC)_TOK_*_(L\d+R\d+)_(UNC\|ALN\|DEC\|NUM\|CC\|EML\|DT)_DE` |
| **Region Selection** | Choose DE based on deployment region (UK, US, or APAC) |
| **Behavior Pattern** | Select L{n}R{n} based on masking requirement (L0R0 = full mask, L6R4 = first 6 + last 4) |
| **Data Type Accuracy** | Match Data_Type_Ref to actual data (UNC for mixed, ALN for alphanumeric, NUM for digits, CC for cards) |
| **Free Text Handling** | Use `FTGEN2_ALN` variant for alphanumeric-only free text (recommended); avoid deprecated `FT` |
| **Performance** | For FTGEN2 Unicode, restrict clear text to 1000 characters; test volumetrically |
| **Token Value Length** | Note that tokens can be up to 4x the source length for Unicode data; validate storage capacity |

---

## Crypto & Secrets

### Secret Naming Pattern

```
sms-crypto-<tenancy_short_name>
```

Examples:
- `sms-crypto-customer`
- `sms-crypto-fdpmortgage`
- `sms-crypto-cdpcmplnts`
- `sms-crypto-bdpukmarketing`

### Tokenization vs Detokenization

**Tokenization (Protect/Encrypt):**
- Input: clear text
- Output: token (masked representation)
- Used in: Day 0 transformation (full load)
- UDF pattern: `cloud_api_udf_{{DE_NAME}}_protect(column_name)`

**Detokenization (Unprotect/Decrypt):**
- Input: token
- Output: clear text (for processing)
- Used in: transform logic when clear value needed
- UDF pattern: `cloud_api_udf_{{DE_NAME}}_unprotect(token_column)`

### Crypto Configuration

- Crypto is optional per table (controlled by crypto_flags)
- Select crypto template variant if crypto flagged
- ProtectorTools package path: see aws skill Pattern 4
- AWS Secrets Manager: secret name from pattern above
- API endpoint URL: see ops skill (Crypto API Endpoints table — varies by environment only)

## Agent Self-Check

Before using this skill's data, verify:

- [ ] **Check 1**: snake_case enforced
- [ ] **Check 2**: partition strategy matches table type
- [ ] **Check 3**: audit columns complete
- [ ] **Check 4**: Protegrity DE patterns valid
- [ ] **Check 5**: no abbreviations
