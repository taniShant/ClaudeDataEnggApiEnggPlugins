---
name: data-products
description: "Data product classification rules: when to create a Foundational (FDP), Consolidated (CDP), or Business (BDP) data product, their tier specifications, and layer promotion rules. Use when determining DP type, validating source-layer dependencies, or routing artefact generation."
user-invocable: false
owner: "tom.franklin@barclays.com"
review_cadence: quarterly
last_reviewed: 2026-08-18
---

**Source:** Tom Franklin | **Owner:** tom.franklin@barclays.com | **Review:** Quarterly | **Last reviewed:** 2026-08-18

# Data Product Types — Decision Framework & Specifications

## Decision Framework

### When to Choose FDP vs CDP vs BDP

**FDP (Foundational Data Product):**
- Single domain, source-neutral, cleansed/enriched atomic data
- Single domain ownership (no overlap)
- Consumed directly without additional copies
- Examples: Mortgages, Customer, Lending, Collections, Digital

**CDP (Consolidated Data Product):**
- Cross-domain aggregation for enterprise reuse
- Derived from FDPs and/or other CDPs (BASE sourcing allowed in exceptional cases with warning)
- Consumed by multiple use cases
- Represents core business entities requiring consistency
- Examples: Retail Account, Product Eligibility, Acquisition Journey

**BDP (Business Data Product):**
- Consumer-owned aggregated metrics/KPIs for domain-specific use
- Can source from FDPs/CDPs only (NOT BASE, NOT other BDPs)
- Narrow scope, high specificity
- Expected to change frequently
- Examples: Complaints BSL, Collections Triage, Channel Performance

### Anti-Patterns (NEVER Do This)

- BDP sourcing BASE layer directly
- BDP sourcing other BDPs
- CDP sourcing BASE layer directly — **exception**: allowed in exceptional cases when mapping-specified; plugin logs a WARNING but does not halt
- Chaining BDPs as enterprise asset (promote to CDP instead)

---

## Three-Tier Data Product Classification

### Tier 1 — Foundational Data Product (FDP)

**Purpose**: Single-domain, source-agnostic, cleansed and enriched atomic data

**Characteristics**:
- Source-neutral data model aligned to Functional Domain
- Atomic, granular, cleansed data ready for downstream consumption
- Single domain ownership — no overlap between FDPs
- Can be directly consumed without additional copies
- Examples: Mortgages, Customer, Lending, Collections, Digital

| Property | Value |
|---|---|
| Data Product Type | `FDP` |
| Database Prefix | `fdp_` |
| AWS Account | DDA (Datalake Domain Account) |
| State Machine | DDA |

> **Shared variant:** `shared_fdp_` — same routing as FDP. Use when the database is designated as a shared asset across domains.

---

### Tier 2 — Consolidated Data Product (CDP)

**Purpose**: Cross-domain aggregation and transformation for enterprise reuse

**Characteristics**:
- Derived from Foundational Data Products
- Consumed by multiple cross-domain use cases
- Represents core business entities requiring consistency
- No need to duplicate atomic data from FDPs
- Examples: Retail Account, Product Eligibility, Acquisition Journey

| Property | Value |
|---|---|
| Data Product Type | `CDP` |
| Database Prefix | `cdp_` |
| AWS Account | DDA (Datalake Domain Account) |
| State Machine | DDA |

> **Shared variant:** `shared_cdp_` — same routing as CDP. Use when the database is designated as a shared asset across domains.

**When to Choose CDP** (Decision Signals):
- Data asset supports multiple business use cases
- Transformation logic is stable and broadly applicable
- Reduces duplication across downstream solutions
- Represents reusable enterprise foundation

---

### Tier 3 — Business Data Product (BDP)

**Purpose**: Consumer-owned aggregated metrics and KPIs for domain-specific use

**Characteristics**:
- Created by individual business domains for their own use
- NOT subject to enterprise governance
- Can source from FDPs and/or CDPs only
- Cannot source from other BDPs
- Can be directly consumed by BI tools, reports, dashboards
- Examples: Complaints BSL, Collections Triage, Channel Performance

| Property | Value |
|---|---|
| Data Product Type | `BDP` |
| Database Prefix | `bdp_` |
| AWS Account | BCA (Business Consumption Account) |
| State Machine | BCA |

> **Shared variant:** `shared_bdp_` — same routing as BDP. Use when the database is designated as a shared asset across domains.

**When to Choose BDP** (Decision Signals):
- Narrow scope with high specificity for targeted outcome
- Bespoke logic and filters unique to one use case
- Expected to change frequently for single consumer
- Premature standardisation as CDP would be overhead

### Data Layer Hierarchy

```
BASE (Raw/Source Layer)
  -> (cleaned to)
FDP (Foundational Data Product)
  -> (aggregated to)
CDP (Consolidated Data Product)
  -> (shaped to)
BDP (Business Data Product)
```

### Layer Promotion Rules

**Critical Rule: No Layer Skipping**

- BDP may NOT directly reference Base layer
- BDP may NOT directly reference other BDPs
- CDP should NOT directly reference Base layer — **exception**: allowed in exceptional cases when mapping-specified (plugin logs WARNING)
- Chaining BDPs as enterprise asset (promote to CDP instead)

**Why**:
- Enforces clean separation of concerns
- Each layer has single responsibility
- Makes DQ (Data Quality) gates enforceable
- Prevents cross-layer coupling

**Source Layer Validation**:
1. Check table prefixes (`fdp_*`, `shared_fdp_*`, `cdp_*`, `shared_cdp_*`, `bdp_*`, `shared_bdp_*`, `e_*`, `bas_*`)
2. BASE layer includes both `e_*` and `bas_*` prefixed tables (synonyms)
3. For FDP targets — sources allowed: `e_*`, `bas_*` (BASE), `fdp_*`, `shared_fdp_*`, `cdp_*`, `shared_cdp_*` (never `bdp_*`, `shared_bdp_*`)
4. For CDP targets — sources allowed: `fdp_*`, `shared_fdp_*`, `cdp_*`, `shared_cdp_*` primarily; `e_*`, `bas_*` (BASE) allowed in exceptional cases when mapping-specified (WARNING logged, not blocked); never `bdp_*`, `shared_bdp_*`
5. For BDP targets — sources allowed: `fdp_*`, `shared_fdp_*`, `cdp_*`, `shared_cdp_*` only (never BASE, never other `bdp_*`, `shared_bdp_*`)

## Agent Self-Check

Before using this skill's data, verify:

- [ ] **Check 1**: DP type derived from prefix
- [ ] **Check 2**: source layer validated
- [ ] **Check 3**: layer promotion rules enforced
- [ ] **Check 4**: no layer skipping
