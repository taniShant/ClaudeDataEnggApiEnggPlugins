# Known Limitations

This document records the current known limitations of the `barclays-buk-data-engineer` plugin as of version 1.0.0. These are acknowledged gaps that are expected to be addressed in future iterations. They are recorded here to set accurate expectations for users and to prevent compliance findings from being treated as unexpected failures.

---

## 1. Standards Skills are Placeholders

The standards skills in `barclays-buk-standards` (covering security, data, governance, architecture, and related domains) are currently placeholders. The standard IDs, version references, and ownership fields are defined, but the controls within those standards have not yet been validated against actual Barclays policy documents.

**Impact:** Agents that assess compliance against these standards will produce `PASS_WITH_WARNINGS` or `NEEDS_HUMAN_REVIEW` outputs rather than `PASS`. The `validate-standards-provenance` hook will surface `review_status: placeholder` warnings on all affected standards.

**Resolution path:** Standards validation against actual Barclays policy documents is planned as a follow-on activity for the BUK Data Engineering Practice in collaboration with the relevant standard owners.

---

## 2. MCP Servers Not Yet Built

The MCP servers required for schema introspection (connecting to Databricks Unity Catalog, Snowflake, etc.) and Confluence access are not yet implemented. Agents that depend on these sources will be unable to retrieve live schema metadata or Confluence documentation.

**Impact:** Schema introspection agents will fall back to user-provided context or produce findings with `state: unknown` in the evidence ledger. Confluence-based context retrieval is unavailable.

**Resolution path:** MCP server implementations are planned as separate infrastructure deliverables. The source register entries are defined as approved access points pending implementation.

---

## 3. Platform Plugins Not Yet Separated

Platform-specific capability for AWS Data Platform, Databricks, and streaming infrastructure currently exists as skills embedded within this plugin rather than as separate plugin dependencies. This is an architectural compromise for the initial release.

**Impact:** All platform skills are loaded for every agent invocation regardless of the target platform, which may produce irrelevant suggestions for non-matching platforms.

**Resolution path:** Platform capability will be extracted into separate `barclays-buk-aws-data-platform`, `barclays-buk-databricks-platform`, and `barclays-buk-streaming-platform` plugins in a future release, using the extension point mechanism documented in `docs/extension-guide.md`.

---

## 4. No Live Integration with LCT, BDP, Alation, or Data Marketplace

The source register includes entries for LCT (Lifecycle Tracking), BDP (Business Data Platform), Alation (data catalogue), and the Barclays Data Marketplace. These are planned access points. No live integration exists in version 1.0.0.

**Impact:** Agents cannot retrieve live LCT status, existing data catalogue entries, or marketplace registrations. LCT artefact entries in result manifests are prepared for manual submission rather than automated integration. Alation and marketplace lookups fall back to user-provided context.

**Resolution path:** Live integrations are dependent on the relevant platform teams providing MCP-compatible interfaces or approved API access.

---

## 5. PII Discovery Uses Heuristics Only

PII classification in the data profiling and security assessment agents uses heuristic and pattern-based methods (column name matching, value pattern matching, metadata analysis). Approved ML-based PII classifiers are not yet integrated.

**Impact:** PII classification results may have false positives (fields incorrectly flagged as PII) or false negatives (PII fields not detected). All PII findings must be reviewed by a human before being used for compliance decisions.

**Resolution path:** Integration with approved ML-based PII classifiers is planned pending procurement and approval of appropriate tooling.

---

## 6. Test Generator and Cost Estimator Agents Are Deferred

Two agents listed as in-scope in `operating-contract.md` — `test-generator` and `cost-estimator` — are not present in this version of the plugin. They are intentionally deferred, not missing by accident.

- `test-generator`: planned to produce test definitions, test case specifications, and example test code as a standalone artefact. The `pipeline-generator` agent currently generates test stubs inline with pipeline code, which partially covers this need.
- `cost-estimator`: planned to produce indicative cost estimates for cloud data platform resources based on documented pricing models.

**Impact:** The quality gate in the TADS workflow (stage 7) cannot be fully automated without `test-generator`. The `operating-contract.md` scope item "Cost estimation for cloud data platform resources" is not available.

**Resolution path:** Both agents are planned for a future minor release. They will be added as new agents and commands using the extension point mechanism rather than modifying the base plugin.

---

## 7. Lineage Analysis is Code-Based Only

Lineage analysis by the `lineage-analyst` agent operates on source code, configuration files, and SQL definitions. It does not integrate with live metadata platforms (Alation, Collibra, Unity Catalog lineage APIs) to retrieve or update runtime lineage graphs.

**Impact:** Lineage documentation reflects what can be inferred from code analysis. Runtime lineage (actual data flows observed in the platform) is not captured. Lineage findings may be incomplete for complex multi-hop pipelines with dynamic table references.

**Resolution path:** Live metadata platform integration is dependent on the MCP server implementations referenced in limitation 2.

---

## 8. SAS Skill Is Available for Comprehension Only

The `sas` skill covers SAS comprehension and migration assistance. It is available as a skill but is not wired into any agent by default. Agents that encounter SAS code in an MR review or migration context should load it explicitly via their `skills:` reference.

**Impact:** SAS-to-Spark migration analysis is possible but requires manual skill composition.

**Resolution path:** When a dedicated SAS-migration agent or command is added (likely as an extension plugin), the `sas` skill will be wired to it directly.

---

## 9. Cost Estimation Not Yet Implemented

Live cloud cost estimation is not yet available. See limitation 6 for details.
