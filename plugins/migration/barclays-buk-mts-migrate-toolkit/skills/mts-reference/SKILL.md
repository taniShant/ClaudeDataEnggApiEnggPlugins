---
name: mts-reference
description: "Domain knowledge for documenting and migrating BUK Spring Boot applications that integrate with mainframe services. Use this skill whenever you encounter any of: doService() calls, EBS/EGS framework classes, WMID/WMOD parameters, TDL table mappings, mainframe-mq / soap-stub / soap-eao / cmod-odwek transport patterns, compiled JAR extraction, service migration from MTS to ODS APIs, API replacement candidate scoring, or any work involving the /mts-documentation, /api-replacement-match, or /mts-migrate commands."
owner: MCA Core Engineering (mcaplatform@barclays.com)
review-trigger: On new transport pattern discovery or ODS API catalogue expansion
---

## Agent Self-Check

Before using this skill's reference data, verify:
- [ ] PROJECT_PATH is set and points to a valid BUK Spring Boot project
- [ ] Gradle cache is populated (EBS/EGS JARs accessible)
- [ ] Transport pattern matches one of the 15 documented categories

# MTS Documentation Reference

Domain knowledge for documenting and migrating BUK Spring Boot applications that integrate with mainframe services. **Use this skill whenever you encounter any of:** `doService()` calls, `EBS`/`EGS` framework classes, WMID/WMOD parameters, TDL table mappings, mainframe-mq / soap-stub / soap-eao / cmod-odwek transport patterns, compiled JAR extraction, service migration from MTS to ODS APIs, API replacement candidate scoring, or any work involving the `/mts-documentation`, `/api-replacement-match`, or `/mts-migrate` commands. Do not skip this skill for any BUK mainframe service documentation or migration task — it contains the canonical WMID-TDL mappings, Backstage catalogue, and transport pattern logic that make these tasks tractable.

## Three-Stage Migration Pipeline

```
/mts-documentation  ->  /api-replacement-match  ->  /mts-migrate
(document service)     (find replacement API)      (generate code changes)
```

1. **`/mts-documentation`** -- Scans codebase, documents MTS service calls, TDL tables, DataGroups, field mappings
2. **`/api-replacement-match`** -- Searches Confluence for replacement APIs, scores candidates, produces match report
3. **`/mts-migrate`** -- Reads match report, generates flag-based dual-path code (MTS + API), converters, tests

## Supported Transport Patterns

| # | Pattern | Transport | Approx. Count |
|---|---------|-----------|---------------|
| 1 | `mainframe-mq` | IBM MQ -> CICS mainframe | ~35 services |
| 2 | `oracle-db-direct` | JDBC -> Oracle reference DB | ~3 services |
| 3 | `db2-reference` | JDBC -> DB2 | ~1 service |
| 4 | `soap-stub` | AXIS2 SOAP via StubConnector | ~25 services |
| 5 | `soap-eao` | SOAP via SoapBindingStub/Eao | Multiple |
| 6 | `cmod-odwek` | HTTP POST via CMOD classes | ~6 (other repos) |
| 7 | `tcv-hybrid` | Dual-path MQ+REST with feature flag | ~3 services |
| 8 | `scv` | SOAP to SingleCustomerView | ~1 service |
| 9 | `soap-webservice` | SOAP to non-CICS backend (ILP/Hogan) | ~2 services |
| 10 | `itsu-oracle` | JDBC via ITSU framework to Oracle | ~1 service |
| 11 | `als-backend` | ALS proprietary protocol | ~1 service |
| 12 | `already-api-rest` | Already REST (out of scope) | ~88 services |
| 13 | `already-api-direct-http` | Already HTTP (out of scope) | Various |
| 14 | `reference-data-only` | Local reference data lookup (no backend) | ~3 services |
| 15 | `framework` | Framework/ITSU session service (no tables) | ~1 service |

## What This Skill Provides

This skill contains reference material used by the `/mts-documentation` command and its agents. It is NOT executable on its own — it provides the domain knowledge that agents consult during documentation generation.

**Note:** Reference material is **embedded directly** in each agent's `.md` file. Each agent only receives the subset of reference data it needs, avoiding redundant file reads. The `reference/` directory remains the **canonical source** for all reference data — when updating domain knowledge, edit the reference files here first, then update the embedded snippets in the relevant agent files.

## Bundled Scripts

Use these instead of writing one-off code. All scripts are in `skills/mts-reference/scripts/` and require only stdlib.

| Script | Purpose | When to use |
|--------|---------|-------------|
| `extract_jar.py <jar>` | **Full orchestrator** — runs Tiers 1+2+3, merges, assigns confidence | First choice for any compiled JAR extraction task |
| `jar_constant_pool.py <jar>` | Tier 1: constant pool parser | When you only need WMID/WMOD string lists quickly |
| `jar_rop_rip.py <jar>` | Tier 2: ROP/RIP parser — authoritative field types + lengths | When checking if `riprop/` directory is present |
| `jar_javap.py <jar>` | Tier 3: exact program/version codes + DataGroup mappings | When javap is available and conditional gating matters |
| `backstage_lookup.py "<query>"` | Layer 1 API candidate search — static catalogue fallback | Replace loading backstage_catalogue_index.md into context (used when live clone fails) |

**Key usage pattern — always run `extract_jar.py` rather than reading the prose reference files:**
```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/mts-reference/scripts/extract_jar.py /path/to/egs-compiled.jar --json
python "${CLAUDE_PLUGIN_ROOT}/skills/mts-reference/scripts/backstage_lookup.py "customer retrieve" --api-type pAPI --top 5
```

## Reference Files

| File | Content | Embedded In |
|------|---------|-------------|
| `reference/wmid_tdl_mappings.md` | 29-entry WMID parameter to TDL table mapping | discovery-agent, data-lineage-agent |
| `reference/datagroup_enums.md` | DataGroup enum types and their gateway methods | (canonical source only) |
| `reference/mainframe_programs.md` | Mainframe program codes, transaction names, transaction classes | discovery-agent, service-inventory-agent |
| `reference/ebs_egs_conventions.md` | JAR naming, class hierarchy, Gradle cache paths | architecture-agent, service-inventory-agent |
| `reference/call_flow_patterns.md` | 11 call flow patterns | architecture-agent, code-journeys-agent, service-catalogue-agent |
| `reference/doservice_patterns.md` | 6 doService call patterns and resolution strategy | discovery-agent |
| `reference/service_categories.md` | 15 service categories with classification algorithm | discovery-agent, service-catalogue-agent |
| `reference/soap_eao_patterns.md` | SOAP stub/EAO detection, extraction, known services | discovery-agent, per-service-doc-agent |
| `reference/cmod_odwek_patterns.md` | CMOD/ODWEK EAO classes, ODWEK paths, document types | discovery-agent, per-service-doc-agent |
| `reference/hybrid_service_patterns.md` | TCV hybrid, SCV, oracle-db-direct, db2-reference patterns | discovery-agent, per-service-doc-agent, api-match-agent |
| `reference/backstage_catalogue_index.md` | Static Backstage catalogue index (fallback when live clone fails) | api-replacement-match (Layer 1B fallback) |
| `reference/api_search_strategy.md` | 3-layer API candidate search strategy | api-replacement-match (Step 2) |
| `reference/discovery_output_format.md` | `## SECTION:` header specs for discovery output | discovery-agent |
| `reference/single_service_mode.md` | Single-service steps S.1-S.10 | mts-documentation command |
| `reference/compiled_jar_extraction.md` | 3-tier compiled JAR fallback extraction overview | discovery-agent, single-service mode |
| `reference/compiled-jar-constant-pool.md` | Tier 1: constant pool parser code + patterns | discovery-agent |
| `reference/compiled-jar-rop-rip.md` | Tier 2: ROP/RIP file parser + cross-validation | discovery-agent |
| `reference/compiled-jar-javap.md` | Tier 3: javap bytecode disassembly parsers | discovery-agent |

## Template Files

| File | Content | Used By |
|------|---------|---------|
| `templates/per_service_doc.md` | Required section structure for per-service docs | per-service-doc-agent |
| `templates/output_sections.md` | Section templates for overview docs | (canonical source only) |

## Key Concepts

### doService Pattern
The central integration point between BUK applications and mainframe services:
```
serviceManager.doService(SERVICE_NAME, "methodName", requestEdo)
```
All mainframe data access flows through this pattern.

### EBS/EGS Architecture
- **EBS (Enterprise Business Service):** Contains business logic, command classes, service interfaces
- **EGS (Enterprise Gateway Service):** Contains gateway classes that communicate with mainframe
- **EGS ODS MF:** Contains transaction classes with WMID parameter mappings to TDL tables

### WMID to TDL Mapping
Each mainframe data request uses WMID parameters that map to TDL (Transaction Data Layer) tables. The convention `WMID-XXXX-PRM` maps to `TDLXXXX`. See `reference/wmid_tdl_mappings.md` for the complete 29-entry mapping.

### Mainframe Transaction Names
Transaction names follow the pattern: `T` + system code + version code + program code. For the Customer System (system code `DL`): `TDL` + version code + program code. Examples: program `CU` version `Q` -> `TDLQCU`; program `CM` version `L` -> `TDLLCM`. See `reference/mainframe_programs.md` for the full reference.
