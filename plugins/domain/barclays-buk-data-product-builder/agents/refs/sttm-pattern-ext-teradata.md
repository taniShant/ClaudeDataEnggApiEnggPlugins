---
description: "Conditional STTM extension for Teradata-specific transformation patterns — covers QUALIFY clause for dedup/ranking, ZEROIFNULL/NULLIFZERO functions, and other Teradata SQL constructs."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Teradata-Specific Transformation Patterns (Extension)

> **Loaded conditionally** — only when Teradata dialect is detected.

## 18. Teradata-Specific Patterns

**Applies when:** SQL dialect is detected as Teradata (see sttm-sql-lineage-agent "SQL Dialect Detection and Parsing" section).

### 18a. QUALIFY (Dedup/Ranking Filter)

**Detection:** QUALIFY clause following window function in SELECT.

**Template Output:**
- Business Logic: Include the full QUALIFY expression as a filter condition. In structured format, add as a Driver Condition: `[QUALIFY ROW_NUMBER() OVER (PARTITION BY alias.col ORDER BY alias.col DESC) = 1]`
- Transformation Type: `Derived`
- Additional Context: "Teradata QUALIFY clause — dedup: keep latest record per {partition_key}"

**Example:**
- Source SQL: `SELECT a.account_id, a.balance FROM db.account a QUALIFY ROW_NUMBER() OVER (PARTITION BY a.account_id ORDER BY a.mod_date DESC) = 1`
- Business Logic (structured): `Driver Table: account (a)\nDriver Conditions: [QUALIFY ROW_NUMBER() OVER (PARTITION BY a.account_id ORDER BY a.mod_date DESC) = 1]\nValue: a.balance`

### 18b. ZEROIFNULL / NULLIFZERO

**Detection:** ZEROIFNULL() or NULLIFZERO() function calls.

**Template Output:**
- Business Logic: Translate to standard SQL equivalent: `COALESCE(col, 0)` for ZEROIFNULL, `NULLIF(col, 0)` for NULLIFZERO
- Transformation Type: `Derived`
- Default Value: `0` (for ZEROIFNULL only — populate column N)
- Additional Context: "Teradata ZEROIFNULL → COALESCE(col, 0)" or "Teradata NULLIFZERO → NULLIF(col, 0)"

**Example:**
- Source: `ZEROIFNULL(outstanding_balance)` → Business Logic: `COALESCE(outstanding_balance, 0)`

### 18c. OREPLACE / OTRANSLATE

**Detection:** OREPLACE() or OTRANSLATE() function calls.

**Template Output:**
- Business Logic: Translate to standard: `REPLACE(col, old, new)` for OREPLACE, `TRANSLATE(col, from, to)` for OTRANSLATE
- Transformation Type: `Derived`
- Additional Context: "Teradata OREPLACE → REPLACE" or "Teradata OTRANSLATE → TRANSLATE"

**Example:**
- Source: `OREPLACE(customer_name, ' ', '_')` → Business Logic: `REPLACE(customer_name, ' ', '_')`

### 18d. STRTOK (String Tokenization)

**Detection:** STRTOK() function call.

**Template Output:**
- Business Logic: Note as string extraction; translate to `SPLIT_PART(col, delim, n)` or equivalent
- Transformation Type: `Derived`
- Additional Context: "Teradata STRTOK → SPLIT_PART (extract nth token)"

**Example:**
- Source: `STRTOK(address_line, ',', 1)` → Business Logic: `SPLIT_PART(address_line, ',', 1)`

### 18e. DECODE

**Detection:** DECODE(col, val1, res1, val2, res2, ..., default) function call.

**Template Output:**
- Business Logic: Translate to CASE WHEN equivalent: `CASE WHEN col = val1 THEN res1 WHEN col = val2 THEN res2 ... ELSE default END`
- Transformation Type: `Derived`
- Signal: `["case", "decode"]`
- Additional Context: "Teradata DECODE → CASE WHEN equivalent"

### 18f. NORMALIZE ON

**Detection:** NORMALIZE ON clause operating on PERIOD data types.

**Template Output:**
- Business Logic: Note as period normalization — merges overlapping PERIOD ranges
- Transformation Type: `Derived`
- Signal: `["teradata", "normalize"]`
- Additional Context: "Teradata NORMALIZE ON — merges overlapping PERIOD ranges. Note grain change."

### 18g. EXPAND ON

**Detection:** EXPAND ON clause converting PERIOD to individual rows.

**Template Output:**
- Business Logic: Note as period expansion — converts PERIOD to individual rows
- Transformation Type: `Derived`
- Signal: `["teradata", "expand"]`
- Additional Context: "Teradata EXPAND ON — converts PERIOD to individual rows. Route to guided Q11 for grain."

### 18h. HASHROW

**Detection:** HASHROW(col1, col2, ...) function call.

**Template Output:**
- Business Logic: `HASHROW(col1, col2, ...)` — list ALL input columns
- Source Column: ALL input columns listed comma-separated
- Transformation Type: `Derived`
- Signal: `["teradata", "hash"]`
- Additional Context: "Teradata HASHROW — hash of multiple columns"

### 18i. PERIOD Data Type Operations

**Detection:** P_INTERSECT, P_NORMALIZE, or other PERIOD-specific operations.

**Template Output:**
- Route to guided mode for confirmation of PERIOD semantics
- Transformation Type: `Derived`
- Additional Context: "Teradata PERIOD operation — flag for guided mode"
