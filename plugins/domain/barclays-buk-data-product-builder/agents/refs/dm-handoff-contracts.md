---
description: "Quality gate definitions for validating BRA and Data Modeller outputs — MUST-HAVE, SHOULD-HAVE, and NICE-TO-HAVE checks used by dm-validation-agent to issue APPROVED or REJECTED verdicts."
owner: "Satish Khanna <satish.khanna@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-09
---

# DM Handoff Contracts

Quality gate checks for validating BRA and Data Modeller outputs. Used by `/dm-validate` and the `dm-validation-agent`.

---

## BRA Output Contract

### MUST-HAVE (Failure = REJECTED)

| # | Check | Description |
|---|-------|-------------|
| BRA-M1 | **Data points ≥ 1** | Section 3 (Data Points Needed) contains at least 1 DP-XX entry |
| BRA-M2 | **Business rules ≥ 1** | Section 4 (Business Rules) contains at least 1 BR-XX entry |
| BRA-M3 | **Grain defined** | Section 1 (Formalised Requirement) specifies subject grain |
| BRA-M4 | **Temporal need stated** | Section 1 specifies historical need (snapshot / SCD / current state) |
| BRA-M5 | **Formalised statement present** | Section 1 contains a rewritten, testable objective statement |
| BRA-M6 | **All 9 sections present** | Document contains all 9 sections of the Fixed Output Template |
| BRA-M7 | **Data points have MoSCoW** | Every DP-XX has a MoSCoW priority (Must / Should / Could) |
| BRA-M8 | **Business rules have logic** | Every BR-XX has plain English logic (IF/WHEN/THEN pattern) |

### SHOULD-HAVE (Failure = WARNING, not rejection)

| # | Check | Description |
|---|-------|-------------|
| BRA-S1 | **Acceptance criteria present** | Section 5 contains at least 1 AC-XX in GIVEN/WHEN/THEN format |
| BRA-S2 | **Regulatory relevance populated** | Section 8 maps at least 1 regulation to the requirement |
| BRA-S3 | **Data quality expectations** | Section 9 (Handoff Notes) mentions data quality expectations |
| BRA-S4 | **Sensitivity classified** | Data points in Section 3 have sensitivity levels (PII / Confidential / Internal) |
| BRA-S5 | **Assumptions documented** | Section 6 contains at least 1 assumption with confidence level |
| BRA-S6 | **Gaps identified** | Section 7 contains at least 1 gap (or explicit statement that no gaps exist) |
| BRA-S7 | **Classification stated** | Section 1 contains a classification (Strategic Ask / Feature Request / Data Request / Regulatory Mandate / Change Request) |
| BRA-S8 | **Handoff notes for modeller** | Section 9 contains key relationships, cardinality, and temporal considerations |

---

## Data Model Output Contract

### MUST-HAVE (Failure = REJECTED)

| # | Check | Description |
|---|-------|-------------|
| DM-M1 | **Entities ≥ 1** | At least 1 table definition with grain statement |
| DM-M2 | **Primary keys defined** | Every table has an explicit composite business key (no surrogates) |
| DM-M3 | **Foreign keys defined** | Cross-table relationships have explicit FK declarations |
| DM-M4 | **Data types assigned** | Every column has a data type with precision/scale where applicable |
| DM-M5 | **Column definitions present** | Every column has a 1-3 line business description |
| DM-M6 | **ER diagram present** | At least 1 Mermaid ER diagram showing entities and relationships |
| DM-M7 | **Dimension audit columns** | Non-fact tables have all 5: `eff_start_date`, `eff_end_date`, `dw_lod_tmp`, `dw_upd_lod_tmp`, `active` |
| DM-M8 | **Fact audit columns** | Fact tables have both: `dw_lod_tmp`, `dw_bus_dt` |
| DM-M9 | **No surrogate keys** | Zero `*_id AUTO_INCREMENT`, `*_KEY` surrogate primary keys |
| DM-M10 | **UPPER_SNAKE_CASE** | All table and column names use UPPER_SNAKE_CASE |
| DM-M11 | **FDP alignment attempted** | FDP discovery was performed (scan of `data/source-domains/`); if folder absent, documented as skipped |
| DM-M12 | **Entity classification present** | Every dimension table classified as Logical Only or Physical with rationale |

### SHOULD-HAVE (Failure = WARNING, not rejection)

| # | Check | Description |
|---|-------|-------------|
| DM-S1 | **SCD strategy documented** | Explicit statement of SCD Type 2 for dimensions, immutable for facts |
| DM-S2 | **Assumptions documented** | At least 1 design assumption with rationale |
| DM-S3 | **Audit columns correct type** | `TIMESTAMP_NTZ` not `TIMESTAMP`, `CHAR(1)` not `BOOLEAN` |
| DM-S4 | **No abbreviations** | Full business terminology (`customer_identifier` not `cust_id`) |
| DM-S5 | **Class words applied** | `*_identifier`, `*_amount`, `*_date`, `is_*_indicator`, `*_status_code` |
| DM-S6 | **Grain-reflective names** | Table and column names reflect actual grain entity |
| DM-S7 | **KPI pattern (if applicable)** | If KPIs in requirement, two-table normalized structure with generic numbered columns (`measure_value_1/2`, `measure_volume_1/2`) and metric register with `measure_description_value_1/2`, `measure_description_volume_1/2` |
| DM-S8 | **Mermaid clean** | ER diagrams contain only names — no descriptions or data types; yellow background on Logical Only entities |
| DM-S9 | **Nullability justified** | NOT NULL / nullable documented with rationale |
| DM-S10 | **Open questions listed** | At least 1 open question for downstream validation |
| DM-S11 | **FDP alignment summary present** | FDP Discovery Results, Matched FDP Entities table, Net-New Entities table, Attribute Sourcing Summary, and FDP Deviations documented |
| DM-S12 | **Entity classification documented** | Every dimension classified as Logical Only (≥70% FDP reuse) or Physical; Logical Only entities have simplified output; Physical have full DDL |
| DM-S13 | **Table consolidation applied** | Same-grain fact tables consolidated using `reporting_period_type_code`; rationale documented if kept separate |
| DM-S14 | **Change Impact Summary (Update Mode)** | If Update Mode: Summary of Changes table, New/Modified/Unchanged entities, Conflict Register (CF-XX entries), baseline entity/column/relationship counts |
| DM-S15 | **Conflict Register complete (Update Mode)** | If Update Mode: Every conflict has CF-ID, entity, column, conflict type, existing value, BRD requirement, recommendation, PENDING status |
| DM-S16 | **Pre-Flight Checklist passed** | Completeness, standards compliance, grain-reflective naming, FDP alignment, deliverable format, and escalation sections all checked |

---

## Verdict Rules

### APPROVED

All MUST-HAVE checks pass. Any number of SHOULD-HAVE warnings is acceptable.

### REJECTED

One or more MUST-HAVE checks fail. The verdict lists all failed checks with specific findings and recommended fixes.

---

## Verdict Output Format

```markdown
## DM Validation Verdict

**Document:** [path]
**Type:** BRA | Data Model
**Verdict:** ✅ APPROVED | ❌ REJECTED

### MUST-HAVE Results

| # | Check | Result | Finding |
|---|-------|--------|---------|
| M1 | [Check name] | ✅ PASS / ❌ FAIL | [Detail if FAIL] |

### SHOULD-HAVE Results

| # | Check | Result | Finding |
|---|-------|--------|---------|
| S1 | [Check name] | ✅ PASS / ⚠️ WARNING | [Detail if WARNING] |

### Summary

- **MUST-HAVE:** X/Y passed
- **SHOULD-HAVE:** X/Y passed
- **Overall:** APPROVED / REJECTED

### Recommended Actions (if REJECTED)

1. [Specific fix for failed check]
2. [Specific fix for failed check]
```
