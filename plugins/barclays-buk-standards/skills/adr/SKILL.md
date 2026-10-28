---
name: adr
description: BUK Architecture Decision Record standards. Covers ADR format, when to write one, status lifecycle, storage conventions, and review/approval process. Use when recording, reviewing, or referencing architectural decisions.
user-invocable: false
---

# BUK Architecture Decision Record (ADR) Standards

> **Placeholder — owned by BUK Architecture Practice.**
> This skill needs content derived from BUK ADR conventions and the enterprise architecture governance process.
> See `docs/shared-standards-approach.md` for context on how this skill fits into the shared standards architecture.

---

## Areas to Cover

### When to Write an ADR
- Criteria for what constitutes an architectural decision requiring an ADR
- Examples: technology selection, significant structural changes, cross-team conventions, security control choices
- What does NOT need an ADR (implementation detail, reversible choice)

### ADR Format

Standard sections:

| Section | Content |
|---|---|
| **Title** | Short imperative phrase: "Use DAF for all BUK digital APIs" |
| **Status** | Proposed → Accepted / Rejected / Superseded |
| **Context** | The problem or situation that prompted the decision |
| **Decision** | The choice made and why |
| **Consequences** | Positive outcomes, trade-offs, follow-on actions |
| **Alternatives Considered** | Options evaluated and why they were rejected |
| **Reviewers** | Who approved the decision and when |

### Status Lifecycle
- `Proposed` — drafted, under review
- `Accepted` — approved and in effect
- `Rejected` — evaluated but not adopted (keep for record)
- `Superseded` — replaced by a later ADR (link to successor)
- `Deprecated` — no longer applicable but not replaced

### Storage and Numbering
- Location: `docs/adr/` in the relevant repository (or central architecture repo for cross-team decisions)
- Naming: `NNN-short-title.md` where NNN is zero-padded sequence
- Cross-team / enterprise ADRs: stored in the Barclays architecture ADR repository

### Review and Approval
- Who must review (Principal Engineer, Security Architect, Solution Architect)
- MR/PR review process for ADR changes
- Link ADRs to the relevant Jira epic or governance item

### Referencing ADRs
- How to reference an ADR from code (comment with ADR number and title)
- How to reference from plugin agents (cite ADR number in output)

---

## How to Contribute

Raise the source documents with BUK Architecture Practice. Suggested inputs:

- BUK ADR template and conventions document
- Enterprise architecture governance process
- Examples of accepted ADRs from existing BUK services
