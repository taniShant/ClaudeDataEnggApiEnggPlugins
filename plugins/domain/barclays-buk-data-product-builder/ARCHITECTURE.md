# Data Product Builder — Architecture

Internal architecture reference for plugin developers and maintainers. For user-facing documentation, see [README.md](./README.md).

---

## Intentional Design Choices

### Workflow Enforcement via Safety HALTs

This plugin intentionally enforces generation ordering through hard HALTs (blocking gates). While this tensions with Plugin Principles 4 (independent invocability) and 7 (agents should not enforce workflow), the HALTs exist for safety reasons:

| HALT | Protects Against |
|------|-----------------|
| `identify-intent` requires `classify-sources` | Wrong table_type → wrong schema, audit columns, partition strategy |
| `gen-wrapper` requires `gen-config` content | Missing S3 paths, broken DTX-BYOC plumbing |
| `gen-driver` requires config + transform | Schema mismatches, runtime execution failures |
| `classify-sources` halts on unclassified tables | Wrong source type corrupts ALL transformation logic |
| `gen-transform` requires `gen-config` | Filter duplication, class name mismatches |
| `gen-dag` requires `gen-bundle` (Databricks) or `gen-dtxog` (Glue) | Missing job YAMLs, broken cross-artefact references |
| `dv-generate` requires `dv-init` | Missing engine selection, no DV session state → broken SQL output paths |
| `dv-report --results` requires `dv-generate` | No validation plans to interpret results against |

**Design rationale**: Producing deployable-looking but silently broken artefacts is worse than blocking progress. The `/validate` command serves as the final quality gate, but upstream HALTs prevent generating artefacts that are fundamentally unsound. Data correctness outweighs strict principle adherence.

Agents are still independently invocable for their core logic (each processes one table, accepts direct inputs), but the command layer enforces data dependency ordering when running the full pipeline.

---

## Agent Model Tiering

The plugin uses 29 agents with model assignments optimised by task complexity:

| Tier | Model | Agents | Use Case |
|------|-------|--------|----------|
| Reasoning | Opus | 4 + 2 DM + 2 STTM + 1 DV | Intent identification, transform generation, code review, auto-decisions + **BRA, Data Modeller** + **SQL lineage extraction, row generation** + **DV validation plan** |
| Moderate | Sonnet | 4 + 1 DM + 3 STTM + 1 validation + 3 DV | Mapping parsing (crypto regex), test generation (90% coverage), Databricks artefact generation, **DAG generation**, **Databricks validation** + **DM validation** + **scenario classification, STTM validation, provenance tracking** + **DV Athena renderer, DV Databricks renderer, DV result interpreter** |
| Mechanical | Haiku | 8 | Template rendering, validation orchestration, routing, git operations |

**DV Agent Model Assignments:**

| Agent | Model | Justification |
|-------|-------|--------------|
| dv-validation-plan-agent | Opus | Column-level mapping reasoning, SCD2 temporal invariant logic, NOT_EVALUATED decisions |
| dv-athena-renderer-agent | Sonnet | Mechanical Athena SQL rendering from fully-specified plans |
| dv-databricks-renderer-agent | Sonnet | Mechanical Databricks SQL rendering from fully-specified plans |
| dv-result-interpreter-agent | Sonnet | Count-based verdict mapping, report generation |

> **Minimum session model**: `sonnet-default` recommended. The `/init` command involves multi-step reasoning (JSON write-verify, conditional branching, Python detection) that `haiku-default` cannot reliably execute on first attempt. Subagents specify their own model overrides — haiku is used for lightweight leaf agents only.

---

## Skills (Reference Data)

Reference data is split into 11 targeted skills — each agent loads only what it needs:

| Skill | Scope |
|-------|-------|
| `aws-tenancy` | Feature team registry (Glue), BTB owners, datasetType, Mesh metadata |
| `databricks-tenancy` | Databricks tenancy infrastructure registry (catalogs, workspaces, SPs, policies per env) |
| `tenancy-summary` | Lightweight tenancy lookup — Glue + Databricks combined (no infra details) |
| `aws-data-products` | Account IDs, S3 bucket patterns, Iceberg SparkConf |
| `conventions` | Naming conventions, file structure rules, artefact patterns |
| `data-products` | FDP/CDP/BDP framework, layer promotion rules. Shared data products (`shared_fdp_*`, `shared_cdp_*`, `shared_bdp_*`) resolve to the same parent type (FDP/CDP/BDP). |
| `database-naming-standards` | Naming, partitions, Protegrity DEs, crypto secrets |
| `service-management` | ITSI/Netcool codes, versions, known issues |
| `dm-banking-standards` | FCA Consumer Duty, GDPR, PSD2, PROD rules, Vulnerability Framework |
| `dm-modelling-standards` | 5 data modelling rules, naming conventions, class words, audit columns |
| `sttm-domain-knowledge` | STTM 16 mapping columns, 10 volumetrics columns, 4-axis classification, evidence precedence, design constraints |

All 11 skills are bundled locally within this plugin (see `skills/` directory). `plugin.json` declares `"dependencies": ["barclays-buk-confluence", "barclays-buk-jira"]` — the Confluence plugin is required for `/dm-bra` Confluence page and attachment fetching; the JIRA plugin is required for `/dm-bra` JIRA ticket fetching and `/push` JIRA comment updates.

---

## FORGE Compliance

Fully compliant with FORGE Standard v1.0.0 — 13/13 patterns.

---

## Plugin Source Structure

The plugin's internal source layout (installed under `${CLAUDE_PLUGIN_ROOT}/`):

```
barclays-buk-data-product-builder/
│
├── README.md                             # Plugin overview; quick-start; gate flow summary
├── ARCHITECTURE.md                       # This file — internal architecture reference
│
├── .claude/
│   └── settings.local.json               # Plugin permissions; allowed tools; hook registrations
│
├── docs/
│   ├── per_environment_resolution.md     # Per-environment config resolution strategy
│   └── structured-transformation-logic.md # Structured format for complex join transformations
│
├── schemas/
│   ├── mapping_excel.schema.json         # 16-column Excel schema; structured_transformation; crypto_flags
│   ├── mesh_json.schema.json
│   ├── dtxog_config.schema.json          # Full dtxog structure; crypto_dpaas conditional
│   ├── intent_identification.schema.json # 6 intent fields; load_type + identification_source enums
│   ├── intent_overrides.schema.json      # User-supplied override fields for unresolved intent (Priority 0)
│   ├── source_table_metadata.schema.json # Source table type classification
│   ├── iceberg_ddl_rules.json            # Iceberg DDL validation rules
│   ├── dag_spec.schema.json              # DAG specification (schedule, dependencies, platform config per table)
│   ├── session_state.schema.json         # Full session state incl. crypto_flags, routing fields, domain_knowledge_text, auto_chain, chain_checkpoints
│   ├── dm_tracking.schema.json           # DM session tracking schema (dm-session/tracking.json)
│   ├── sttm_input_contract.schema.json  # STTM input contract schema
│   ├── sttm_session_state.schema.json  # STTM session state tracking schema
│   ├── dv_validation_contract.schema.json  # DV validation contract schema
│   ├── dv_validation_plan.schema.json      # DV validation plan schema
│   ├── dv_session_state.schema.json        # DV session state tracking schema
│   └── dv_validation_results.schema.json   # DV validation results schema
│
├── templates/
│   ├── glue/
│   │   ├── mesh_json.template.json
│   │   ├── transform_day0.template.py    # {{table_name}}_transform_day0 class — full load
│   │   ├── transform_day1.template.py    # {{table_name}}_transform_day1 class — incremental/BAU
│   │   ├── wrapper_py_per_table.template.py
│   │   ├── config_single_data_flow.template.json      # table-level data config (single data flow system)
│   │   ├── config_multiple_data_flow.template.json    # table-level data config (multiple data flow — nested, for combined/UNION mode)
│   │   ├── generic_components/
│   │   │   ├── __init__.py
│   │   │   ├── reader.py                 # SourceReader class
│   │   │   ├── writer.py                 # TargetWriter class
│   │   │   └── date_control.py           # Date control utilities
│   │   ├── dtxog_config_byoc_single_data_flow.template.json           # BYOC; single data flow
│   │   ├── dtxog_config_byoc_multiple_data_flow.template.json         # BYOC; multiple data flow
│   │   ├── dtxog_config_byoc_crypto_single_data_flow.template.json    # crypto_dpaas; single data flow
│   │   └── dtxog_config_byoc_crypto_multiple_data_flow.template.json  # crypto_dpaas; multiple data flow
│   ├── databricks/
│   │   ├── transform_day0.template.py    # Day0 transform class (full load) — Databricks notebook
│   │   ├── transform_day1.template.py    # Day1 transform class (incremental/BAU) — Databricks notebook
│   │   ├── driver.template.py            # Driver notebook (env resolution, config loading, orchestration)
│   │   ├── config_single_data_flow_multi_env.template.yml  # Multi-env config (dev, preprd, prd, uat) — also used per-source-system when source_system declared
│   │   ├── databricks.yml.template       # DABs bundle with compute tiers (small/medium/large/xlarge)
│   │   ├── iceberg_ddl.template.sql      # CREATE TABLE IF NOT EXISTS; USING iceberg; Unity Catalog
│   │   ├── generic_components/
│   │   │   ├── __init__.py
│   │   │   ├── source_reader.py          # Databricks SourceReader class
│   │   │   └── target_writer.py          # Databricks TargetWriter class
│   │   ├── jobs/
│   │   │   ├── job.template.yml                              # Per-table pipeline job (compute tier variable)
│   │   │   ├── table_creation_utility_job.template.yml       # Table creation utility job
│   │   │   ├── date_control_insert_utility_job.template.yml  # Date control insert utility job
│   │   │   ├── daily_date_control_update_utility_job.template.yml
│   │   │   └── volume_creation_utility_job.template.yml      # Volume creation (conditional)
│   │   └── utilities/
│   │       ├── table_creation_utility.template.py            # DDL accumulator (all tables)
│   │       ├── date_control_insert_utility.template.py       # Process list accumulator (all tables)
│   │       ├── daily_date_control_update_utility.template.py
│   │       └── volume_creation_utility.template.py           # Volume setup (conditional)
│   ├── dags/
│   │   ├── skeletons/                                # Platform × schedule skeleton templates (6)
│   │   │   ├── databricks_cron.template.py
│   │   │   ├── databricks_business_cal.template.py
│   │   │   ├── databricks_adhoc.template.py
│   │   │   ├── glue_cron.template.py
│   │   │   ├── glue_business_cal.template.py
│   │   │   └── glue_adhoc.template.py
│   │   └── blocks/                                   # Composable building blocks (21)
│   │       ├── imports_core.py, imports_databricks.py, imports_glue.py, ...
│   │       ├── date_control.py, date_control_adhoc.py
│   │       ├── holiday_check.py, bank_holidays_data.py
│   │       ├── taskgroup_databricks.py, taskgroup_glue.py
│   │       ├── dag_wiring_glue.py, dag_wiring_with_deps.py
│   │       ├── dynamodb_sensor.py, cross_deployment_sensor.py
│   │       └── ... (21 blocks total — assembled per dag_spec)
│   └── tests/
│       ├── conftest.template.py
│       ├── pytest_ini.template
│       ├── test_wrapper.template.py
│       ├── test_transform_nontransactional.template.py
│       ├── test_transform_transactional.template.py
│       ├── test_driver.template.py
│       └── test_dag.template.py                      # DAG validation tests
│   └── sttm/
│       └── mapping_spec.md               # STTM mapping output template
│
├── commands/
│   ├── init.md
│   ├── parse-mapping.md
│   ├── classify-sources.md               # Source table type classification
│   ├── identify-intent.md
│   ├── gen-mesh.md                       # Glue only
│   ├── gen-config.md                     # Both platforms; config-first (runs BEFORE transform)
│   ├── gen-transform.md
│   ├── gen-wrapper.md                    # Glue only
│   ├── gen-dtxog.md                      # Glue only
│   ├── gen-driver.md                     # Databricks only
│   ├── gen-ddl.md                        # Databricks only (DDL embedded in table_creation_utility.py)
│   ├── gen-bundle.md                     # Databricks only (DABs bundle: databricks.yml + job YAMLs)
│   ├── gen-dag.md                        # Both platforms; Airflow DAG generation (scheduling, deps, orchestration)
│   ├── gen-tests.md                      # Both platforms; >90% coverage + syntax check + optional test execution
│   ├── run-tests.md                      # Standalone pytest re-execution (requires Python); non-blocking
│   ├── review.md                         # Post-generation code review; both platforms
│   ├── validate.md
│   ├── push.md                           # Push to remote; quality gates (syntax + tests + validation)
│   ├── status.md
│   ├── resume.md                         # Resume auto-chain from halt point; applies intent overrides
│   ├── dm-bra.md                         # DM: Business Requirements Analyst command
│   ├── dm-model.md                       # DM: Data Modeller command
│   ├── dm-validate.md                    # DM: Quality gate validation command
│   ├── dm-status.md                      # DM: Progress display command
│   ├── sttm-init.md                      # STTM: Initialize workspace
│   ├── sttm-classify.md                  # STTM: 4-axis classification
│   ├── sttm-parse-sql.md                 # STTM: SQL/PySpark lineage extraction
│   ├── sttm-generate.md                  # STTM: Full 8-step generation pipeline
│   ├── sttm-resolve.md                   # STTM: Interactive field resolution
│   ├── sttm-validate.md                  # STTM: Validation (102 checks)
│   ├── sttm-export.md                    # STTM: JSON → Excel export
│   ├── dv-init.md                        # DV: Initialize session (engine selection, prerequisites)
│   ├── dv-generate.md                    # DV: Generate validation SQL (contracts, plans, rendered SQL)
│   ├── dv-report.md                      # DV: Generate validation report
│   └── refs/                             # Externalized reference docs (read by commands)
│       ├── chain-checkpoint-pattern.md   # Chain checkpoint and resume logic
│       ├── chain-mode-compression.md     # Context compression for full-automation chains
│       ├── init-full-automation.md       # Full-automation mode execution protocol
│       ├── init-recovery.md              # Git-based session recovery fallback protocol
│       └── sttm-guided-mode-questions.md # STTM: 38 guided-mode interview questions
│
├── configs/
│   ├── plugin.config.json
│   ├── domain_knowledge/                 # Per-domain Domain Knowledge MD files
│   │   └── <tenancy>_knowledge.md        # e.g. fdpmortgage_knowledge.md
│   └── sttm/                             # STTM configuration files (9 YAMLs)
│       ├── template_spec.yaml            # Mapping output column spec
│       ├── scenarios.yaml                # 4-axis classification definitions
│       ├── validation_rules.yaml         # 102 validation check definitions
│       ├── audit_columns.yaml            # Audit columns by table type
│       ├── precedence.yaml               # Evidence precedence hierarchy
│       ├── naming_conventions.yaml       # Database prefix patterns
│       ├── interview_questionnaire.yaml  # Guided-mode question catalog
│       ├── example_index.yaml            # Classification → example selection
│       └── crypto_registry.yaml          # Crypto DE registry
│   └── dv/                               # DV configuration files
│       ├── validation_checks.yaml        # DV validation check definitions
│       └── sql_safety_rules.yaml         # DV SQL safety rule definitions
│
├── agents/
│   ├── mapping-parser-agent.md
│   ├── data-product-type-router.md
│   ├── domain-knowledge-loader.md
│   ├── intent-identifier-agent.md        # 6-field intent; extended priority chain (0→0.5→1→1.5→2→3)
│   ├── transform-generator-agent.md      # Includes crypto UDF generation logic
│   ├── glue-mesh-agent.md                # Mesh JSON generation (skills: conventions, tenancy)
│   ├── glue-wrapper-agent.md             # Wrapper + config generation (skills: conventions, tenancy, aws)
│   ├── glue-dtxog-agent.md               # DTXOG config generation (skills: conventions, tenancy, aws, ops)
│   ├── databricks-artefact-agent.md
│   ├── dag-generator-agent.md            # Airflow DAG generation (template-based, both platforms)
│   ├── test-generator-agent.md
│   ├── code-review-agent.md              # Post-generation review; both platforms; read-only
│   ├── auto-decision-agent.md            # Full-automation mode: resolves autonomously when possible; asks user when needed
│   ├── push-agent.md                     # Quality gates + GitLab MR creation
│   ├── glue-validation-agent.md          # Glue-specific validators (invoked via /validate in 7-batch mode)
│   ├── databricks-validation-agent.md    # Databricks-specific validators (invoked via /validate in 7-batch mode)
│   ├── dm-bra-agent.md                   # DM Business Requirements Analyst (Marcus) — opus-default
│   ├── dm-data-modeller-agent.md         # DM Data Modeller (Elena) — opus-default
│   ├── dm-validation-agent.md            # DM output validation — sonnet-default
│   ├── sttm-scenario-classifier-agent.md # STTM 4-axis classification — sonnet-default
│   ├── sttm-sql-lineage-agent.md         # STTM SQL/PySpark lineage extraction — opus-default
│   ├── sttm-row-generator-agent.md       # STTM mapping row generation (16 cols) — opus-default
│   ├── sttm-validation-agent.md          # STTM 102-check validation — sonnet-default
│   ├── sttm-provenance-agent.md          # STTM per-field provenance tracking — sonnet-default
│   ├── dv-validation-plan-agent.md       # DV validation plan generation — opus-default
│   ├── dv-athena-renderer-agent.md       # DV Athena SQL rendering — sonnet-default
│   ├── dv-databricks-renderer-agent.md   # DV Databricks SQL rendering — sonnet-default
│   ├── dv-result-interpreter-agent.md    # DV result interpretation and reporting — sonnet-default
│   └── refs/                             # Externalized reference docs (read by agents conditionally)
│       ├── anti-hallucination-core.md          # Universal anti-hallucination rules
│       ├── crypto-refusal-protocol.md          # Crypto information refusal rules
│       ├── dm-data-source-policy.md            # DM agent data source policy (no simulated data)
│       ├── dm-handoff-contracts.md             # DM MUST-HAVE/SHOULD-HAVE validation checks
│       ├── multiple-data-flow-system.md        # Multiple data flow system config patterns
│       ├── standalone-invocation.md            # Standalone agent invocation patterns
│       ├── sttm-lineage-ext-multi-step-etl.md  # STTM multi-step ETL lineage capture
│       ├── sttm-lineage-ext-pyspark-handling.md # STTM PySpark DataFrame → SQL mapping
│       ├── sttm-lineage-ext-teradata-dialect.md # STTM Teradata dialect handling
│       ├── sttm-pattern-ext-crypto.md          # STTM crypto patterns (tokenize/detokenize/both)
│       ├── sttm-pattern-ext-multi-step.md      # STTM multi-step ETL chain pattern
│       ├── sttm-pattern-ext-teradata.md        # STTM Teradata-specific patterns
│       ├── sttm-provenance-instructions.md     # STTM provenance tracking instructions
│       ├── sttm-rowgen-ext-multi-step-rendering.md # STTM multi-step rendering rules
│       ├── sttm-rowgen-ext-union-merge-format.md   # STTM UNION/MERGE structured format
│       ├── sttm-scenario-rules.md              # STTM 4-axis scenario rules (per-axis generation context)
│       ├── sttm-system-context.md              # STTM system context (output format, columns, constraints)
│       ├── sttm-transformation-patterns.md     # STTM 26+ transformation pattern definitions
│       ├── sttm-validation-checklist.md        # STTM validation checks (S/M/SC/A/F categories)
│       ├── dv-validation-patterns.md           # DV validation check patterns and invariants
│       ├── dv-athena-sql-patterns.md           # DV Athena SQL dialect patterns
│       ├── dv-databricks-sql-patterns.md       # DV Databricks SQL dialect patterns
│       ├── dv-sql-safety-rules.md              # Pointer → configs/dv/sql_safety_rules.yaml + validators/dv-sql-safety-validator.md
│       ├── template-first-rule.md              # Template-first generation rule
│       ├── tool-invocation-patterns.md         # Tool call patterns for auto-chain mode
│       ├── transform-component-boundaries.md
│       ├── transform-config-contract.md        # Config-first contract (filter suppression rules)
│       ├── transform-crypto-udf-rules.md       # Loaded only if crypto_flags.has_crypto == true
│       ├── transform-domain-knowledge-examples.md  # Loaded only if scoped_domain_knowledge != null
│       ├── transform-locked-predicates.md      # Locked predicate preservation rules
│       ├── transform-nl-interpretation-rules.md    # Natural language → PySpark interpretation rules
│       ├── transform-platform-databricks.md    # Databricks TargetWriter / SourceReader patterns
│       ├── transform-platform-glue.md          # Glue TargetWriter / SourceReader / CDC config
│       ├── transform-pyspark-guardrails.md
│       ├── transform-source-column-allowlist.md # Source column allowlist enforcement
│       ├── transform-temporal-stitching-reference.md  # SCD2 temporal stitching patterns
│       ├── transform-volumetric-optimization.md # Volumetric optimization patterns
│       └── uncertainty-disclosure.md           # Uncertainty disclosure rules
│
├── hooks/
│   ├── pre-generate-gate.hook.md
│   ├── post-generate-validate.hook.md
│   ├── platform-lock-check.hook.md
│   ├── session-state-persist.hook.md
│   ├── mapping-change-detector.hook.md
│   ├── crypto-flag-propagate.hook.md
│   ├── post-review-regenerate.hook.md    # Retry logic for Critical/High findings
│   └── pycache-cleanup.hook.md           # __pycache__ cleanup after test execution
│
├── validators/
│   ├── cdc-presence-assertion-validator.md    # CDC config block presence for NonTransactional tables
│   ├── code-quality-validator.md            # PySpark linting + crypto UDF syntax
│   ├── config-transform-alias-validator.md  # Config-transform alias consistency
│   ├── consistency-validator.md             # Platform consistency + naming prefix + source layer rules
│   ├── contract-reconciliation-validator.md # Mapping ↔ config contract fidelity
│   ├── crypto-indicator-detector.md
│   ├── dag-validation-validator.md          # DAG structure, placeholders, retries, timezone, cross-artefact
│   ├── dtxog-structure-validator.md
│   ├── excel-column-validator.md
│   ├── foundation-library-validator.md      # Databricks Foundation Library usage patterns
│   ├── iceberg-ddl-validator.md             # Iceberg DDL syntax validation
│   ├── infrastructure-validator.md          # S3 location + cross-environment value detection
│   ├── join-predicate-fidelity-validator.md # Join predicate fidelity against mapping
│   ├── literal-value-fidelity-validator.md  # Literal value fidelity against mapping
│   ├── mesh-json-completeness-validator.md
│   ├── name-origin-validator.md             # Column name origin validation
│   ├── notebook-format-validator.md         # Databricks notebook format compliance
│   ├── pk-null-risk-validator.md            # Primary key nullable risk detection
│   ├── placeholder-auto-resolver.helper.md
│   ├── placeholder-completeness-validator.md
│   ├── python-import-validator.md           # Import statement validation
│   ├── scd1-structural-validator.md         # SCD1 config structural compliance
│   ├── source-attribution-validator.md      # Source column attribution correctness
│   ├── source-column-existence-validator.md # Validates F.col() refs against mapping (anti-hallucination)
│   ├── source-table-type-consistency-validator.md
│   ├── template-landmark-preservation-validator.md
│   ├── test-coverage-validator.md           # Test coverage threshold enforcement
│   ├── unity-catalog-validator.md           # Unity Catalog naming + catalog resolution
│   └── dv-sql-safety-validator.md           # DV SQL safety validator (SAFETY-01 – SAFETY-10)
│
├── examples/
│   ├── sttm/                              # STTM input/output example pairs (27 JSON files) — loaded by row-generator-agent
│   │   ├── fdp_transactional_input.json / fdp_transactional_output.json
│   │   ├── bdp_aggregated_input.json / bdp_aggregated_output.json
│   │   ├── cdp_multisource_input.json / cdp_multisource_output.json
│   │   └── ... (+ crypto, union, merge, pyspark, teradata, CTE, multi-step examples)
│
├── prompts/
│   ├── gating-questions.md
│   ├── infrastructure-questionnaire.md   # DEPRECATED — see platform-specific variants
│   ├── infrastructure-questionnaire-glue.md        # Glue/AWS infrastructure questionnaire
│   ├── infrastructure-questionnaire-databricks.md  # Databricks infrastructure questionnaire
│   └── missing-info-prompts.md
│
├── scripts/
│   ├── validate_column_refs.py           # Source column existence validator (Python CLI)
│   ├── validate_join_predicates.py       # Join predicate fidelity checker
│   ├── validate_pk_null_risk.py          # Primary key null risk checker (Python CLI)
│   └── hooks/                            # Bash hook scripts
│       ├── automation-gate.sh
│       ├── platform-lock-check.sh
│       ├── post-generate-validate.sh
│       ├── pycache-cleanup.sh
│       └── session-state-persist.sh
│
├── skills/
│   ├── conventions/SKILL.md              # Naming conventions, file structure rules, artefact patterns
│   ├── aws-data-products/SKILL.md        # Infrastructure constants: account IDs, S3 naming patterns, glue.id
│   ├── aws-tenancy/SKILL.md              # Glue tenancy: team → database / bucket-shortname / BTB owner
│   ├── databricks-tenancy/SKILL.md       # Databricks tenancy: service principals, AD groups, catalogs
│   ├── tenancy-summary/SKILL.md          # Lightweight tenancy lookup — Glue + Databricks tables (no infra details)
│   ├── data-products/SKILL.md            # Data product taxonomy and metadata standards
│   ├── database-naming-standards/SKILL.md # Database naming conventions across platforms
│   ├── service-management/SKILL.md       # Runtime: ITSI codes, tool versions, state machines, known issues
│   ├── dm-banking-standards/SKILL.md     # FCA Consumer Duty, GDPR, PSD2, PROD rules, Vulnerability Framework
│   ├── dm-modelling-standards/SKILL.md   # 5 data modelling rules, naming conventions, class words, audit columns
│   └── sttm-domain-knowledge/SKILL.md   # STTM: 16 mapping cols, 10 volumetrics cols, 4-axis classification, constraints
│
├── session/                              # → See README "Output Structure" for runtime contents
├── generated/                            # → See README "Output Structure" for generated artefacts
├── dm-session/                           # → DM command tracking (runtime, not committed)
└── dm-output/                            # → DM command outputs (runtime, not committed)
```

> **Note**: `session/` and `generated/` are project-local directories created at runtime in the user's working directory. See the README [Output Structure](./README.md#output-structure) section for their full layout.

---

## Stage 4 Architecture — Data Validation

### Architecture Flow

```
mapping_parsed.json ──┐
                      ├──▶ /dv-init ──▶ dv_session_state.json
intent_identification.json ─┘              │
                                           ▼
databricks-tenancy skill ──┐  ┌──▶ catalog resolution (--env, Databricks only)
audit_columns.yaml ─────────┤  │         │
validation_checks.yaml ─────┤  │         ▼
                             ├──▶ /dv-generate ──▶ dv_validation_contract_{table}.json
dv-validation-patterns.md ───┘    │              │ (with resolved catalog names)
                                  │              ▼
                                  │    dv-athena-renderer ──▶ {db}_{table}_validation.sql
                                  │         OR                {db}_{table}_results_summary.sql
                                  │    dv-databricks-renderer ──▶ (same files, Spark SQL)
                                  │              │
                                  │              ▼
                                  │    dv-sql-safety-validator ──▶ PASS/FAIL
                                  │              │
                                  ▼              ▼
                       user runs SQL ──▶ /dv-report ──▶ dv_validation_report.md
                           externally         │          dv_validation_report.json
                                             ▼
                                    dv-result-interpreter ──▶ PASS/FAIL/NOT_EVALUATED
```

### Component Independence

The DV stage is **fully independent** from Stage 3 (Code Generation):
- Reads from mapping artifacts (Stage 2 output), not generated code (Stage 3 output)
- Can run before, after, or without Stage 3
- Does not modify any Stage 3 artifacts
- Uses its own session state (`dv_session_state.json`) separate from the main `session_state.json`
- In dependent mode, `/dv-generate` optionally reads `session_state.env_config` (from DE pipeline) to resolve Databricks target catalogs. This is a **read-only** cross-stage dependency — DV never modifies Stage 3 artifacts

### Dialect-Neutral Plan Design

Semantic validation logic is separated from SQL rendering:
1. **Plan agent** (Opus) — determines WHAT to validate: which checks, which columns, what parameters, what NOT_EVALUATED conditions
2. **Renderer agents** (Sonnet) — determine HOW to render: dialect-specific SQL syntax, function names, parameterization

This separation means:
- Adding a new SQL dialect requires only a new renderer, not changes to validation logic
- Check definitions are maintained in one place (`validation_checks.yaml`)
- The plan is testable independently of SQL generation

### NOT_EVALUATED Semantics

NOT_EVALUATED is not a failure — it is an explicit acknowledgment that the validation cannot be performed due to missing information. The plan agent tracks specific reasons:
- Missing source precision metadata
- Source table not accessible from validation engine
- Floating-point column without documented cast
- Business logic absent or ambiguous

### Security Boundaries and Trust Model

1. **Generation boundary**: The plugin generates SQL but never executes it
2. **Data boundary**: Only aggregated counts enter the report pipeline — no row-level data, business keys, or PII
3. **Safety boundary**: All generated SQL passes through the safety validator (10 rules) before being written
4. **Excel boundary**: User-provided result files undergo 4 structural validation checks before parsing

---

### Architecture Decisions — Data Validation

**ADR-DV-01: Mapping document is the validation source of truth**
The mapping document (not generated PySpark code) drives all validation logic. This ensures validation is independent of any code generation bugs and verifies the data against the original specification.

**ADR-DV-02: Validation is independent from transformation code generation**
DV can run before, after, or without Stage 3. This allows validation SQL to be generated even when code generation is incomplete or unnecessary.

**ADR-DV-03: Exact matching required — no tolerances**
All reconciliation checks use zero tolerance. PASS requires all mismatch/violation counts to be exactly zero. This is intentional — any data discrepancy must be investigated.

**ADR-DV-04: SCD temporal logic lives in the dialect-neutral plan, not in SQL renderers**
Temporal invariant reasoning (overlap detection formulas, gap policy evaluation, boundary stitching rules) is determined by the Opus-tier plan agent. Renderers only translate the plan's check definitions into SQL syntax.

**ADR-DV-05: SQL generation only — no execution**
Users run generated SQL through their own Athena/Databricks interfaces. This is consistent with how `/gen-transform` generates PySpark but does not execute it, and avoids connection management complexity and security boundary issues.

**ADR-DV-06: Missing mapping metadata → NOT_EVALUATED, never guessed logic**
When the plan agent cannot determine exact validation semantics (missing precision, ambiguous boundary convention, absent business logic), the check is marked NOT_EVALUATED with a specific reason rather than generating potentially incorrect validation SQL.

**ADR-DV-07: BUK CDAO inclusive date convention used**
SCD2 temporal checks use the BUK CDAO convention where `eff_end_date` is inclusive: `prev.eff_end_date = next.eff_start_date` for temporal continuity. Sentinel value: `'3499-12-31'`.

**ADR-DV-08: Temporal gap severity is mapping-driven**
Gaps in SCD2 history may be legitimate (entity inactive, source data non-continuous, period collapsing with gap-aware logic). Gap checks use `severity: blocker` only when the mapping explicitly requires continuous history; `severity: warning` when policy is undocumented; the check is omitted when gaps are explicitly permitted. This prevents false failures for valid business scenarios.

**ADR-DV-09: Databricks catalog names are resolved at generation time, not parameterized**
DV SQL is standalone — users paste it into a Databricks SQL editor. There is no runtime driver to resolve placeholders. Embedding actual catalog names via `--env` makes SQL immediately runnable. The DE pipeline uses a different approach (config.yml + driver resolution at runtime) because it has a driver to resolve placeholders — DV does not. Source catalogs are fixed per environment; target catalogs are resolved from the tenancy registry with fallback to user prompt.
