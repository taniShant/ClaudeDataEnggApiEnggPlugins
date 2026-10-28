# barclays-buk-data-engineer

> **Status: Draft** | **Version: 1.0.0** | **Owner: BUK Data Engineering Practice**

Data Engineer AI Worker. Turns explicit data-engineering inputs into reviewable engineering artefacts, evidence, validation results and hand-off packs. Supports the full data engineering lifecycle: requirement interpretation, source discovery, profiling, mapping, modelling, technology assessment, ETL/ELT design, DB change, migration, DQ validation, lineage/metadata and MR advice.

## Design Principles

1. One source of truth for standards and domain knowledge (dependency-based, never copied)
2. Knowledge is framework-neutral and lives in skills
3. Extension is additive/overriding, never by forking the base
4. Every agent is useful when invoked independently
5. Unknowns and unavailable evidence are explicit
6. Every standards skill has an owner and review trigger/cadence
7. Agents suggest next steps but never enforce workflow sequencing

## Dependencies

| Plugin | Skills Used |
|---|---|
| `barclays-buk-standards` | security, data, governance, infrastructure, observability, testing |

## Agents

| Agent | Purpose |
|---|---|
| `data-engineer-worker` | Front-door agent: routes requests, consolidates outputs, exposes uncertainty |
| `requirement-assessor` | Extracts FRs, NFRs, ambiguities and gaps from requirements |
| `context-resolver` | Resolves and classifies context sources with authority/freshness |
| `source-profiler` | Profiles authorised data with statistical aggregates, redacts sensitive values |
| `mapping-assistant` | Creates/validates source-to-target mappings with lineage |
| `logical-data-modeller` | Platform-independent logical model from requirements/mappings |
| `physical-data-modeller` | Platform-specific physical model with DDL draft |
| `technology-option-adviser` | Neutral technology comparison producing ADR draft |
| `pipeline-generator` | ETL/ELT pipeline code from approved mappings |
| `data-quality-engineer` | DQ rule catalogue and executable checks |
| `database-change-adviser` | Schema change assessment with forward/rollback DDL drafts |
| `migration-planner` | Same-engine upgrade and cross-engine migration plans |
| `lineage-impact-analyst` | Technical lineage graphs and blast-radius analysis |
| `metadata-publisher` | Alation/metadata payload generation (publishing separate) |
| `performance-engineer` | Evidence-based performance analysis and recommendations |
| `streaming-design-adviser` | Batch vs streaming assessment and streaming design |
| `pii-discovery-adviser` | PII/PCI classification without exposing sensitive values |
| `merge-request-adviser` | Multi-dimension MR review (never approves/merges) |
| `validation-and-handoff-agent` | Deterministic validation and handoff pack production |
| `ab-initio-discovery-agent` | Discovers Ab Initio pipelines, extracts attribute-level lineage, produces workbooks + dashboards + OpenLineage events |

## Commands

| Command | Purpose |
|---|---|
| `/assess` | Assess requirements |
| `/resolve-context` | Resolve context sources |
| `/profile` | Profile data sources |
| `/map` | Create/validate mappings |
| `/model-logical` | Produce logical model |
| `/model-physical` | Produce physical model |
| `/tech-choice` | Technology comparison ADR |
| `/generate-pipeline` | Generate pipeline code |
| `/generate-dq` | Generate DQ rules/checks |
| `/db-change` | Assess schema changes |
| `/plan-migration` | Plan migrations |
| `/lineage-impact` | Lineage and blast radius |
| `/metadata` | Generate metadata payloads |
| `/performance` | Performance analysis |
| `/streaming-design` | Streaming design |
| `/pii-discovery` | PII/PCI discovery |
| `/review-mr` | Review merge requests |
| `/validate` | Validate artefacts |
| `/handoff` | Produce handoff pack |
| `/run` | Full manifest routing |
| `/status` | Summarise prior result |
| `/discover-abinitio-lineage` | Scan any Ab Initio sandbox, extract lineage, optionally publish to Marquez |

## Skills

### Worker Behaviour
- `worker-operating-contract` — Mission, boundaries, input policy, standards enforcement
- `evidence-and-uncertainty` — Evidence states, transparency rules, result statuses
- `artefact-traceability` — End-to-end traceability chain requirements
- `technology-decision-method` — Neutral technology decision ADR method

### Engineering
- `pyspark` — PySpark DataFrame API, performance, testing patterns
- `sql` — ANSI SQL, dialect awareness, parameterised queries, anti-patterns
- `aws-data-services` — Athena, Glue, S3, Lake Formation, Step Functions
- `databricks` — Unity Catalog, Delta Lake, Workflows, DLT, Structured Streaming
- `data-modelling` — Dimensional, relational, Data Vault, Data Product patterns
- `streaming` — Kafka, Flink, event processing, delivery semantics
- `sas` — SAS comprehension and migration assistance (loaded by migration-planner; not for code generation)
- `performance-engineering` — Query plans, indexing, partitioning, optimisation
- `pii-discovery` — PII/PCI detection methods, classification, data minimisation
- `database-migration` — Upgrade/cross-engine migration, reconciliation, cutover
- `ab-initio-lineage-discovery` — Ab Initio sandbox auto-discovery, DML/graph/XFR/PSET parsing, RES/TWS dependency walking, OpenLineage event generation

## TADS Compliance

This plugin enforces TADS (Technology Application Development Standard) and Lean Control Process compliance through an 8-stage workflow. See `docs/operating-contract.md` for the full workflow.

## Mandatory Source Register

The plugin maintains references to mandatory internal sources (LCT, BDP, Alation, Data Marketplace, BUK Data Products, and TADS/LCP Confluence pages). Access is validated at runtime; inaccessible sources become visible blockers in the evidence ledger.

## Known Limitations

Standards skills are currently placeholders; MCP server integrations are not yet built; platform skills (AWS, Databricks) are embedded rather than separated into platform plugins; and two in-scope agents (`test-generator`, `cost-estimator`) are deferred to a future release. See `docs/known-limitations.md` for the full list.

## Extension Points

context_resolvers, profiling_adapters, model_patterns, technology_candidates, code_generators, dq_rule_compilers, metadata_publishers, lineage_publishers, validators, handoff_renderers

## Quick Start

```bash
# Assess a requirement
/assess --input ./requirements/story-123.md

# Profile a source
/profile --source ./schemas/source_db.sql --tables customers,orders

# Generate a mapping
/map --mode generate --source-schema ./schemas/source.sql --target-schema ./schemas/target.sql --requirements ./output/assessment/assessment.json

# Full manifest run
/run --manifest ./input-manifest.yaml
```
