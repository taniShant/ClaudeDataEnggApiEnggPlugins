# BUK Plugins × BMAD Integration Guide

This guide explains how BUK Claude Code plugins integrate with the [BMAD Method](https://docs.bmad-method.org/) framework. BMAD provides workflow sequencing and agent orchestration. BUK plugins provide Barclays-specific domain knowledge, standards enforcement, and code generation.

**BUK agents are reusable capability units** — they have explicit inputs and outputs and work standalone regardless of what framework surrounds them. They don't need to know about BMAD, and BMAD doesn't need to know about them. This guide is the wiring layer that surfaces BUK capabilities at the right point in BMAD's workflow. The agents themselves remain framework-agnostic.

---

## How they fit together

| Layer | Owned by | Examples |
|---|---|---|
| Workflow sequencing | BMAD | Phases, handoffs, PRD → Architecture → Build |
| Agent orchestration | BMAD | Spawning agents, managing context, party mode |
| Domain knowledge | BUK plugins | Consumer Duty, Blueprint component rules, Secure Coding |
| Standards enforcement | BUK plugins | WCAG 2.1 AA, Barclays API design, governance triggers |
| Code generation | BUK plugins | SDF screens, Jetpack Compose, OpenAPI specs |

BMAD's agents become Barclays-aware by loading BUK skills via `skills:` in agent frontmatter and `persistent_facts` in BMAD agent config.

---

## BUK plugin → BMAD agent mapping

BMAD has 6 default agents. BUK adds 2 custom agents (QA, Security) via `config.toml`.

| BMAD phase | BMAD agent | BMAD agent code | BUK plugin | BUK agent |
|---|---|---|---|---|
| Analysis | Analyst (Mary) | `bmad-agent-analyst` | `barclays-buk-product-manager` | `product-manager-agent` |
| Planning / UX | UX Designer (Sally) | `bmad-agent-ux-designer` | `barclays-buk-ux-designer` | `ux-designer-agent` |
| Planning / UX | UX Designer (Sally) | `bmad-agent-ux-designer` | `barclays-buk-copywriter` | `copywriter-agent` |
| Solutioning | Architect (Winston) | `bmad-agent-architect` | `barclays-buk-solution-architect` | `solution-architect-agent` |
| Solutioning | Technical Writer (Paige) | `bmad-agent-tech-writer` | `barclays-buk-solution-architect` | `solution-architect-agent` (docs) |
| Solutioning | Security _(BUK custom)_ | `barclays-buk-security` | `barclays-buk-security-architect` | `security-architect-agent` |
| Implementation | Developer (Amelia) | `bmad-agent-dev` | `barclays-buk-ui-engineer` | `ui-engineer-agent` (dispatcher) |
| Implementation | Developer (Amelia) | `bmad-agent-dev` | `barclays-buk-ui-engineer-sdf` | via `/ui-engineer-sdf` command |
| Implementation | Developer (Amelia) | `bmad-agent-dev` | `barclays-buk-ui-engineer-ios` | `ui-engineer-ios-worker-agent` |
| Implementation | Developer (Amelia) | `bmad-agent-dev` | `barclays-buk-ui-engineer-android` | `ui-engineer-android-worker-agent` |
| Implementation | Developer (Amelia) | `bmad-agent-dev` | `barclays-buk-api-engineer` | `api-engineer-agent` |
| Implementation | Developer (Amelia) | `bmad-agent-dev` | `barclays-buk-data-engineer` | `data-engineer-agent` |
| Implementation | QA _(BUK custom)_ | `barclays-buk-qa` | `barclays-buk-quality-engineer` | `quality-engineer-agent` |
| Implementation | QA _(BUK custom)_ | `barclays-buk-qa` | `barclays-buk-accessibility-auditor` | `accessibility-auditor-agent` |
| Live / Feedback | _(no BMAD default)_ | — | `barclays-buk-reliability-engineer` | `reliability-engineer-agent` |
| Live / Feedback | _(no BMAD default)_ | — | `barclays-buk-incident-manager` | `incident-manager-agent` |

---

## Installation

### 1. Install BMAD in your project

Follow the [BMAD installation guide](https://docs.bmad-method.org/). This creates `_bmad/` in your project root.

### 2. Register the BUK marketplace

```bash
/plugin marketplace add git@app.gitlab.barcapint.com:barclays/claude/marketplace/cio/buk.git
```

### 3. Install the BUK plugins you need

```bash
# Install all delivery plugins
/plugin install barclays-buk-standards@barclays-cio-buk
/plugin install barclays-buk-product-manager@barclays-cio-buk
/plugin install barclays-buk-ux-designer@barclays-cio-buk
/plugin install barclays-buk-solution-architect@barclays-cio-buk
/plugin install barclays-buk-security-architect@barclays-cio-buk
/plugin install barclays-buk-ui-engineer@barclays-cio-buk
/plugin install barclays-buk-ui-engineer-sdf@barclays-cio-buk      # SDF / React Native projects
/plugin install barclays-buk-api-engineer@barclays-cio-buk
/plugin install barclays-buk-data-engineer@barclays-cio-buk
/plugin install barclays-buk-quality-engineer@barclays-cio-buk
/plugin install barclays-buk-accessibility-auditor@barclays-cio-buk
/plugin install barclays-buk-reliability-engineer@barclays-cio-buk
/plugin install barclays-buk-incident-manager@barclays-cio-buk
```

### 4. Apply the BUK BMAD module

Copy the template from `workflows/bmad-buk-template/` into your project's `_bmad/custom/`:

```bash
cp -r workflows/bmad-buk-template/_bmad/custom/* _bmad/custom/
```

This injects BUK `persistent_facts` and skill references into BMAD's standard agent roles.

---

## How BUK skills inject into BMAD agents

BMAD agents support `persistent_facts` — static domain knowledge kept in context throughout a session. The BUK module injects Barclays-specific facts into each relevant agent role.

Example: the Product Manager agent receives:

```toml
[persistent_facts]
consumer_duty = "All features must be assessed against FCA Consumer Duty (FG22/5). Apply barclays-buk-standards:consumer-duty for CUNA triggers, fair value, and vulnerable customer obligations."
governance = "All features require governance assessment. Apply barclays-buk-standards:governance for DRA/FRA, Change Control, and RAID."
customer_engagement = "All customer communications require CUNA/NAPA assessment. Apply barclays-buk-standards:customer-engagement."
```

This means the BMAD PM agent will apply BUK Consumer Duty checks without any additional prompting.

This is a further validation of the BUK plugin model. The knowledge referenced in `persistent_facts` lives entirely in `barclays-buk-standards` skills — there is no duplication. BMAD provides phase sequencing; BUK provides the domain standards; `barclays-buk-standards` remains the single source of truth (Principle 1). Each layer does only what it owns.

---

## Custom agents vs. default agent overrides

The template includes two types of integration, which behave differently:

### Default agent overrides (6 files)

`bmad-agent-pm.toml`, `bmad-agent-analyst.toml`, `bmad-agent-architect.toml`, `bmad-agent-dev.toml`, `bmad-agent-ux-designer.toml`, `bmad-agent-tech-writer.toml`

These inject `persistent_facts` and `[[menu]]` shortcuts into BMAD's built-in agents. They **participate fully in BMAD's phase sequencing** — the PM agent activates during Analysis, the Architect during Solutioning, etc. BUK domain knowledge is available automatically at the right phase without any extra prompting.

### Custom agent registrations (config.toml)

`barclays-buk-qa` and `barclays-buk-security` are registered as custom BUK agents because BMAD has no default QA or Security agent.

BMAD supports custom agents but they are **persona definitions, not workflow participants**. They can be invoked directly by name or appear in party-mode sessions, but they do not plug into BMAD's built-in phase sequencing. Teams must invoke them explicitly:

```
# Switch to the BUK QA agent
@barclays-cio-barclays-buk-qa run test plan for the current sprint
```

Or via the `[[menu]]` shortcuts defined in `bmad-agent-qa.toml` and `bmad-agent-security.toml`.

For teams where QA and Security are integral to every sprint, consider adding explicit invocation steps to your BMAD workflow definition rather than relying on automatic activation.

---

## Workflow: BUK delivery phases within BMAD

BUK maps onto BMAD's four phases:

### Phase 1 — Analysis
**BMAD activity:** Problem framing, product brief
**BUK agent:** `barclays-buk-product-manager:product-manager-agent`
**BUK standards applied:** consumer-duty, vulnerable-customers, customer-engagement, governance
**Handoff to Phase 2:** Requirements doc, Consumer Duty flags, governance triggers

### Phase 2 — Planning
**BMAD activity:** PRD, UX design
**BUK agents:** `barclays-buk-ux-designer:ux-designer-agent`, `barclays-buk-copywriter:copywriter-agent`
**BUK standards applied:** accessibility, consumer-duty, vulnerable-customers, brand, ux
**Handoff to Phase 3:** Journey map, UX design, copy brief

### Phase 3 — Solutioning
**BMAD activity:** Architecture, security review, epic/story breakdown
**BUK agents:** `barclays-buk-solution-architect:solution-architect-agent`, `barclays-buk-security-architect:security-architect-agent`
**BUK standards applied:** api-design, security, adr
**Handoff to Phase 4:** Architecture diagram, NFRs, threat model, security sign-off

### Phase 4 — Implementation
**BMAD activity:** Build cycle — UI, API, data, tests, validation
**BUK agents:** UI engineer (platform-specific), api-engineer, data-engineer, quality-engineer, accessibility-auditor, reliability-engineer
**BUK standards applied:** platform-specific Iron Rules, api-design, security, testing, accessibility
**Output:** Production-ready screens, API contracts, test suite, audit reports

---

## Handoff contracts

Every BUK agent declares explicit `## Your Inputs` and `## Your Outputs` sections. These map directly onto BMAD's handoff contract structure.

When handing off between BMAD phases, pass the BUK agent's output path as the next agent's input:

```
# Phase 1 → Phase 2 handoff
barclays-buk-product-manager OUTPUT_PATH → barclays-buk-ux-designer REQUIREMENTS_PATH

# Phase 2 → Phase 3 handoff
barclays-buk-ux-designer OUTPUT_PATH    → barclays-buk-solution-architect UX_DESIGN_PATH

# Phase 3 → Phase 4 handoff
barclays-buk-solution-architect OUTPUT_PATH → barclays-buk-ui-engineer ARCHITECTURE_PATH
barclays-buk-security-architect OUTPUT_PATH → barclays-buk-api-engineer SECURITY_REVIEW_PATH
```

All inputs default to `"none"` — BUK agents proceed without upstream artefacts (Principle 7). The handoff enriches the output; it does not gate progress.

---

## Flags and transparency

Every BUK agent produces a `## Flags` section in its output covering:
- Placeholder skills (checks skipped)
- Missing inputs (assumptions made)
- Decisions made under uncertainty

BMAD's escalation model should treat any BUK Flag as an escalation signal — surface it to the human reviewer at the end of each phase rather than silently carrying it forward.

---

## Quick reference: BUK skills by BMAD agent

| BMAD agent | BUK skills loaded |
|---|---|
| Analyst (Mary) — `bmad-agent-analyst` | consumer-duty, governance, customer-engagement |
| Product Manager (John) — `bmad-agent-pm` | consumer-duty, vulnerable-customers, customer-engagement, governance |
| UX Designer (Sally) — `bmad-agent-ux-designer` | accessibility, consumer-duty, vulnerable-customers, brand, ux |
| Architect (Winston) — `bmad-agent-architect` | api-design, security, adr |
| Developer (Amelia) — `bmad-agent-dev` | platform routing (SDF/iOS/Android/Web), api-design, security |
| Technical Writer (Paige) — `bmad-agent-tech-writer` | adr, api-design (documentation) |
| QA _(BUK custom)_ — `barclays-buk-qa` | testing, accessibility, security |
| Security _(BUK custom)_ — `barclays-buk-security` | security (STRIDE, OWASP, Barclays Secure Coding) |
