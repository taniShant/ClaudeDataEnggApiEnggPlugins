---
name: data
description: BUK data standards. Covers data classification tiers, retention and deletion policies, PII/PCI masking rules, schema conventions, and data quality requirements. Use when designing data models, schema migrations, or reviewing data handling.
user-invocable: false
---

# BUK Data Standards

> **Placeholder — owned by BUK Data Practice / Chief Data Office.**
> This skill needs content derived from Barclays data classification policy, retention standards, and BUK data governance guidelines.
> See `docs/shared-standards-approach.md` for context on how this skill fits into the shared standards architecture.

---

## Areas to Cover

### Data Classification
- Classification tiers (e.g. Public, Internal, Confidential, Restricted)
- Examples of data types at each tier
- Controls required per classification level
- Customer data handling requirements (PII, financial data, biometrics)

### Retention and Deletion
- Retention periods per data type and regulatory basis
- Right to erasure (GDPR Article 17) — what must be deletable and how
- Archival vs. deletion policies
- Audit trail retention requirements

### PII and PCI Masking
- What constitutes PII and PCI in the BUK context
- Masking rules for logs, exports, and non-production environments
- Approved anonymisation and pseudonymisation techniques
- Data minimisation principle — collect only what is needed

### Schema Conventions
- Naming conventions for tables, columns, indexes
- Primary key strategy (surrogate vs. natural keys)
- Timestamp columns — created_at, updated_at, deleted_at conventions
- Soft delete vs. hard delete guidance

### Data Quality
- Required validation rules at ingestion
- Null handling and default value conventions
- Referential integrity requirements
- Data quality gate criteria for schema changes

### Migration Standards
- Migration script conventions (idempotency, rollback strategy)
- Blue/green schema migration patterns
- Coordination with downstream consumers before breaking schema changes

---

## How to Contribute

Raise the source documents with BUK Data Practice. Suggested inputs:

- Barclays data classification policy
- BUK data retention schedule
- GDPR / data subject rights implementation guide
- BUK data quality standards document
