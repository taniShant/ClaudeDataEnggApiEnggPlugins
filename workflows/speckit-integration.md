# BUK Plugins × Spec-Kit Integration Guide

This guide explains how BUK Claude Code plugins integrate with [Spec-Kit](https://github.com/github/spec-kit) (Spec-Driven Development). Spec-Kit provides a 7-step SDD workflow that turns specifications into working implementations. BUK plugins inject Barclays-specific domain knowledge and code-generation capabilities into that workflow.

**BUK agents are reusable capability units** — they have explicit inputs and outputs and work standalone regardless of what framework surrounds them. They don't need to know about Spec-Kit, and Spec-Kit doesn't need to know about them. This guide is the wiring layer that surfaces BUK capabilities at the right point in Spec-Kit's workflow. The agents themselves remain framework-agnostic.

In practice: `barclays-buk-standards` skills are injected automatically by a preset at the relevant steps. BUK agents (`barclays-buk-product-manager`, `barclays-buk-solution-architect`, etc.) are available to call directly at any step — the guide and preset make it easy to remember when and how.

---

## Three-layer model

Barclays's SDD implementation uses three distinct layers:

```
Spec-Kit
  ↓ generic 7-step SDD framework (specify / plan / tasks / implement / converge)

barclays-sdd  (git@...barclays/sdd)
  ↓ Barclays SDD implementation built on Spec-Kit
    - Spec-Kit presets for Barclays-specific workflows
    - Chameleon project scaffolding (figma-to-code, DAF extensions)
    - Constitution enforcing Barclays standards for each project
    - Speckit commands that call BUK agents at delegation points

BUK plugins  (this repo)
  ↓ Domain knowledge and generation capability
    - barclays-buk-standards: single source of truth for all shared standards
    - Generation agents: product-manager, solution-architect, api-engineer,
      ui-engineer-sdf, quality-engineer, accessibility-auditor, security-architect
```

**barclays-sdd** is the integration layer. It wires Spec-Kit's workflow steps to BUK agents at the right delegation points. It owns the Barclays SDD workflow sequence. It does not own domain knowledge — that lives in BUK plugins.

**BUK plugins** are the capability layer. They own all domain standards and generation logic. They can be called from barclays-sdd, from BMAD, from a standalone session, or directly — the agents don't care.

If you are starting a new Barclays feature with SDD, use **barclays-sdd** — not this guide directly. The preset and constitution in barclays-sdd handle the Spec-Kit wiring for you. This guide documents the BUK side of the integration for plugin authors and platform engineers.

---

## How they fit together

| Layer | Owned by | Examples |
|---|---|---|
| Spec-driven workflow (7 steps) | Spec-Kit | specify → plan → tasks → implement → converge |
| Barclays SDD implementation | barclays-sdd | speckit.* commands, Chameleon scaffold, figma-to-code extension, DAF extension |
| BUK agent delegation | barclays-sdd commands | `barclays-buk-product-manager:product-manager-agent` at specify, `barclays-buk-security-architect:security-architect-agent` at plan |
| Domain knowledge and standards | BUK plugins | `barclays-buk-standards`, generation agents |

Spec-Kit sequences the work. barclays-sdd applies Barclays-specific workflow rules and delegates to BUK agents. BUK plugins provide the knowledge and generation capability. No layer duplicates the responsibility of another.

---

## How barclays-sdd delegates to BUK

Each speckit command in barclays-sdd contains explicit agent delegation points. At runtime, the command invokes BUK agents via `subagent_type`. Here is the mapping:

| speckit command | Delegation point | BUK agent |
|---|---|---|
| `speckit.specify` | Product spec review | `barclays-buk-product-manager:product-manager-agent` |
| `speckit.specify` | Accessibility brief | `barclays-buk-accessibility-auditor:accessibility-auditor-agent` |
| `speckit.plan` | Technical research | `barclays-buk-solution-architect:solution-architect-agent` |
| `speckit.plan` | Security review of data model + contracts | `barclays-buk-security-architect:security-architect-agent` |
| `speckit.plan` | Spec gaps | `barclays-buk-product-manager:product-manager-agent` |
| `speckit.tasks` | (phase completion) | `barclays-buk-quality-engineer:quality-engineer-agent` |
| `speckit.implement` | Screen and UI component creation | `barclays-buk-ui-engineer-sdf:ui-engineer-sdf-worker-agent` |
| `speckit.implement` | Visual validation | `ui-visual-validator` |
| `speckit.implement` | Accessibility audit (post-screen) | `barclays-buk-accessibility-auditor:accessibility-auditor-agent` |
| `speckit.implement` | Test writing | `barclays-buk-quality-engineer:quality-engineer-agent` |
| `speckit.implement` | Phase completion review | `barclays-buk-quality-engineer:quality-engineer-agent` |
| `speckit.implement` | Security review (final) | `barclays-buk-security-architect:security-architect-agent` |
| `speckit.implement` | Dependency audit | `dependency-auditor` |
| `speckit.implement` | Performance analysis | `performance-analyst` |

The delegation uses Claude Code's `subagent_type` mechanism. The speckit command is the workflow owner (Principle 7); the BUK agents are independently invocable capability units (Principle 4).

---

## BUK standards → Spec-Kit step mapping

| Spec-Kit step | What happens | BUK standards injected |
|---|---|---|
| `speckit.specify` | Write the feature spec (requirements, ACs) | consumer-duty, vulnerable-customers, customer-engagement, governance |
| `speckit.plan` | Technical implementation strategy | api-design, security, adr |
| `speckit.tasks` | Generate task list | testing, accessibility |
| `speckit.implement` | Build the feature | Platform routing → barclays-buk-ui-engineer-sdf, barclays-buk-api-engineer |

---

## Starting a Barclays SDD project

### 1. Install barclays-sdd

barclays-sdd is a Spec-Kit implementation. Install it as your SDD layer:

```bash
pip install specify-cli
specify init <project> --integration claude-code
# then add barclays-sdd as your preset source
specify preset add git@...barclays/sdd --dev
```

barclays-sdd includes the Chameleon constitution, figma-to-code scripts, DAF extension, and all speckit.* command overrides. The BUK agent wiring is already in place.

### 2. Install BUK plugins

The speckit commands in barclays-sdd call BUK agents by `subagent_type`. Those agents must be installed:

```bash
/plugin marketplace add git@app.gitlab.barcapint.com:barclays/claude/marketplace/cio/buk.git
/plugin install barclays-buk-standards@barclays-cio-buk
/plugin install barclays-buk-product-manager@barclays-cio-buk
/plugin install barclays-buk-solution-architect@barclays-cio-buk
/plugin install barclays-buk-security-architect@barclays-cio-buk
/plugin install barclays-buk-ui-engineer-sdf@barclays-cio-buk      # Chameleon / React Native projects
/plugin install barclays-buk-api-engineer@barclays-cio-buk
/plugin install barclays-buk-quality-engineer@barclays-cio-buk
/plugin install barclays-buk-accessibility-auditor@barclays-cio-buk
```

### 3. Run the SDD workflow

```bash
/speckit.specify   # spec + Consumer Duty assessment + product-manager review
/speckit.plan      # tech plan + research + security review of contracts
/speckit.tasks     # task list with testing and accessibility tasks
/speckit.implement # build — screens delegated to ui-engineer-sdf, APIs to api-engineer
```

---

## Using the BUK preset standalone (without barclays-sdd)

If you are not using barclays-sdd (e.g. a non-Barclays project using Spec-Kit), the BUK preset at `workflows/speckit-buk-preset/` adds BUK standards checks to Spec-Kit commands via the `prepend` strategy:

```bash
specify preset add ./workflows/speckit-buk-preset --dev
```

The preset injects:
- `speckit.specify` — Consumer Duty, vulnerable customers, governance flags
- `speckit.plan` — API design, STRIDE threat model, ADR requirements
- `speckit.tasks` — 90% test coverage tasks, WCAG 2.1 AA accessibility audit, security review

This is a lighter integration than barclays-sdd. It applies BUK standards as checklist prompts but does not include Chameleon scaffolding, figma-to-code, or DAF extensions.

---

## Flags and transparency

Every BUK agent produces a `## Flags` section in its output covering:
- Placeholder skills (checks skipped)
- Missing inputs (assumptions made)
- Decisions made under uncertainty

When using Spec-Kit's `speckit.converge` step to assess the codebase against the spec, BUK Flags should surface in the convergence report as gaps — not silently ignored.

---

## Quick reference: BUK plugins by Spec-Kit step

| Spec-Kit step | BUK plugin | BUK agent |
|---|---|---|
| specify | `barclays-buk-product-manager` | `product-manager-agent` |
| specify | `barclays-buk-accessibility-auditor` | `accessibility-auditor-agent` |
| plan | `barclays-buk-solution-architect` | `solution-architect-agent` |
| plan | `barclays-buk-security-architect` | `security-architect-agent` |
| tasks | `barclays-buk-quality-engineer` | `quality-engineer-agent` |
| implement | `barclays-buk-ui-engineer-sdf` | `ui-engineer-sdf-worker-agent` (Chameleon/RN) |
| implement | `barclays-buk-api-engineer` | `api-engineer-agent` |
| implement | `barclays-buk-quality-engineer` | `quality-engineer-agent` |
| implement | `barclays-buk-accessibility-auditor` | `accessibility-auditor-agent` |
| implement | `barclays-buk-security-architect` | `security-architect-agent` |
