---
name: tads-lean-control
description: TADS (Technology Application Development Standard) and Lean Control Process knowledge. Covers TADS objectives, control framework, Lean Control Process, guild engagement, Risk Stories, Business Outcomes, release governance, mandatory artefacts, UEQ and maturity assessment.
user-invocable: false
owner: BUK Technology Governance
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
authoritative_sources:
  - id: POLICY_HUB
    description: Authoritative source for latest TADS/TCMS/CDMS versions
    url: https://barclays.clausematch.com/portal/dashboard/documents?searchQuery=technology+application+development+standard
  - id: TADS_WELCOME
    description: TADS and Lean Control landing page
    url: https://confluence.barcapint.com/spaces/AgileControl/pages/538450554/Welcome+to+TADS+and+Lean+Control
---

# TADS and Lean Control Process

## Framework Position

TADS forms part of the Enterprise Risk Management Framework (ERMF), specifically the Operational Risk Framework (ORF). It implements control objectives from the Technology Risk Policy (TRP).

## TADS Primary Objectives

1. Specify minimum controls implementing Technology Risk Policy (TRP) Control Objectives
2. Document control requirements mitigating identified risks aligned to TRP
3. Enforce a framework of engagement with Control SMEs for internally developed applications
4. Promote an agile methodology

## Scope

TADS applies to planned technology application-development changes arising from business requirements, delivered to Production (PROD) or Disaster Recovery (DR) environments.

## Complementary Standards

| Standard | Purpose |
|---|---|
| Technology Application Development Standard (TADS) | Minimum controls for internally developed application changes |
| Change Delivery Management Standard (CDMS) | Minimum controls for governance of change portfolios and managing delivery |
| Technology Change Management Standard (TCMS) | Controlled promotion of technology changes to production environment |

Always verify latest versions in Policy Hub. Known discovery versions (TADS v9.2, CDMS v14.0, TCMS v13.0) were marked Expired — treat as discovery evidence only, not authoritative.

## Lean Control Process (LCP)

The Lean Control Process provides a framework for managing continuous interaction between the Product Delivery Team and their Risk/Control SMEs throughout iterative delivery. Controls are a mix of preventative and detective.

### LCP Roles

| Role | Responsibility |
|---|---|
| Product Owner | Business outcome ownership, requirement completeness |
| Architecture Owner | Architectural alignment, technology decisions |
| Agile Team Lead | Delivery execution, Risk Story management |
| Service Owner | Operational readiness, service introduction |
| Control Guild/SME | Risk identification, control engagement, evidence review |

### LCP Key Concepts

#### Business Outcome
The planned change initiative registered in LCT. Links to Risk Stories, releases and evidence. Created before development begins.

#### Risk Stories
Work items representing potential risks identified through guild engagement. Managed through testing into PROD/DR releases. Lifecycle: identified -> created -> in progress -> tested -> closed (risk mitigated OR dispensation approved).

#### Unified Engagement Questionnaire (UEQ)
Determines which guilds (mandatory and elective) must be engaged based on change characteristics. Submitted at Business Outcome creation.

#### Releases
The vehicle for promoting changes to PROD/DR. Release sign-off requires all conditions met. Blocked by: unresolved Risk Stories, missing mandatory artefacts, incomplete guild engagement, failed control checks.

## Lean Control Tool (LCT)

LCT is the in-house tool implementing LCP. It enforces TADS controls and tracks:
- Products/Services and their lifecycle
- Business Outcomes and their status
- Risk Stories and their resolution
- Guild engagements and SME interactions
- Mandatory artefacts and evidence
- Change Requests and ServiceFirst integration
- Releases and sign-off conditions
- Engagement health metrics

### LCT URL
https://leancontrol.pr1.apaas4.barclays.intranet/buk.datalake.warehouse

### Rules for LCT Interaction
- Never infer an LCT status — always read from the system
- Never mark a control complete without system evidence
- Never bypass LCT process steps
- Business Outcome must exist before Risk Stories can be created
- Risk Stories must link to testable acceptance criteria
- Release sign-off requires all blocking conditions resolved

## Guild Structure

### Mandatory Guilds
Engagement required for all technology application development changes:
- Enterprise Architecture
- Security
- Service Transition
- Data Architecture (relevant to all data engineering changes)

### Elective Guilds
Engaged based on UEQ responses and change characteristics:
- Data Privacy
- Fraud
- Accessibility
- Financial Crime
- Compliance

### Guild Engagement Process
1. Submit UEQ to determine applicable guilds
2. Mandatory guilds auto-engaged; elective guilds engaged per UEQ
3. Guild Lead assigns Guild Members
4. Continuous engagement throughout delivery (not just at gate points)
5. Risks identified -> Risk Stories created
6. Risk Stories managed through testing
7. Guild provides evidence/sign-off for release

## TADS Controls

Controls are loaded from the TADS Controls Confluence page. Each control has:
- Control ID and description
- Control objective (linked to TRP)
- Control type: preventative or detective
- Engagement requirement (which SME/guild)
- Evidence expectations
- Severity: blocking or advisory

### Common Control Areas
- Architecture alignment
- Security controls (access, encryption, secrets)
- Data privacy and PII handling
- Testing adequacy (unit, integration, performance)
- Operational readiness (monitoring, alerting, runbooks)
- Change management (deployment, rollback)
- Service introduction (documentation, support)

## Mandatory Artefacts

Each TADS initiative must maintain an artefact register. Per artefact:
- Artefact name and description
- Owner (named person)
- Target completion date
- Repository/URL link
- Status: not started | in progress | complete | reviewed
- Reviewer (named person)
- Validation evidence link
- Last updated date

### Common Mandatory Artefacts
- Architecture Decision Records
- Security assessment / threat model
- Test strategy and evidence
- Operational runbook
- Deployment and rollback plan
- Performance baseline and acceptance criteria

## TADS Maturity Checklist

Products are assessed against TADS maturity. Covers:
- Control engagement completeness
- Artefact completeness and quality
- Risk Story resolution rate
- Guild satisfaction/engagement health
- Evidence traceability
- Operational readiness

## Release Governance

### Conditions Blocking Release Sign-off
- Unresolved blocking Risk Stories
- Missing mandatory artefacts
- Incomplete mandatory guild engagement
- Failed control checks
- Missing Change Request in ServiceFirst
- Unapproved architecture decisions
- Outstanding security findings

### Release Warnings (non-blocking)
- Overdue elective guild engagement
- Incomplete optional artefacts
- Advisory control findings
- Missing non-critical documentation

## TADS Governance

### BUK-Specific Governance
- TADS Governance: BUK meetings track compliance, escalations, actions
- Meeting minutes maintained in Confluence (page ID: 3696457478)
- Escalation path: Guild Lead -> TADS Team -> Head of Governance

### TADS Roadmap 2026
Current roadmap available at page ID 3712075932. Check for upcoming control changes, new mandatory artefacts, or process updates before planning.

## TADS Exemptions

Exemptions from specific controls require:
- Formal request with justification
- Risk assessment and acceptance
- Named approver at appropriate authority level
- Time-bound validity
- Conditions for review/renewal
- Documented in LCT and TADS Operational Guide

Never recommend an exemption without current criteria and formal approval steps.

## Worker Obligations

### Before Code Generation (Stages 0-4)
1. Verify access to LCT and source register pages
2. Determine TADS applicability from current authoritative content
3. Identify applicable guilds via UEQ criteria
4. Check for existing Business Outcome in LCT
5. Identify required Control SME engagements
6. Review TADS mandatory artefact list
7. Check TADS Maturity Checklist applicability

### During Engineering (Stages 5-6)
1. Link every artefact to its TADS mandatory artefact entry
2. Track Risk Stories identified during development
3. Maintain guild engagement evidence
4. Ensure traceability: requirement -> control/Risk Story -> code -> test -> evidence
5. Generate artefacts that satisfy mandatory requirements

### Before Release (Stages 7-8)
1. Verify all TADS mandatory artefacts complete with evidence
2. Check LCT for unresolved blocking Risk Stories
3. Verify all mandatory guild engagements complete
4. Check release sign-off conditions
5. Never claim release readiness without LCT system evidence
6. Record any exemptions with formal approval evidence

## Key Rules

- TADS compliance status comes from LCT system evidence, never inference
- Policy Hub is authoritative for standard versions, not Confluence copies
- Draft/expired standards cannot support compliance claims
- Guild engagement is continuous, not a one-time gate
- Risk Stories are tracked work items, not just documentation
- Mandatory artefacts need named owners and reviewers
- Release sign-off requires all blocking conditions resolved in LCT
- Exemptions require formal approval at appropriate authority level
- The TADS ML Artefact Analysis Bot may assess artefacts automatically — ensure artefacts are accessible to it where required

## TADS Team Contacts

| Name | Role |
|---|---|
| Fabrizio Calisti | Group Head of Tech Governance & Change |
| Ilona Chauhan | TADS / EUDA PMO |
| Diptesh Sarnaik | Product Owner - Lean Control Tool |
| Deborah Lees | Head of TADS Controls Maturity |
| Nichola N'di-Orduh | Head of Risk & Thematics |
| Krishna Sajja | Head of Governance & Assurance |
| Paul Winstanley | Head of TADS Data Insight & Reporting |
