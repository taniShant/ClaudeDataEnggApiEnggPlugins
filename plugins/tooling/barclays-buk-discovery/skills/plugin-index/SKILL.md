---
name: plugin-index
description: >
    Complete index of all BUK marketplace plugins. Lists every plugin by group,
    its purpose, entry point agent, typical problems it solves, and required inputs.
    Used by the discover agent to match a problem to the right plugin.
user-invocable: false
---

<!-- Source: barclays-buk-discovery/skills/plugin-index/SKILL.md -->
<!-- Owner: BUK PE -->
<!-- Review trigger: When a new plugin is added to or removed from the marketplace -->
<!-- Status: Draft -->

## Quick Start

Load this skill via `barclays-buk-discovery:plugin-index` in `discover-agent`. Read the routing table below, match the developer's problem to the "Solves" column, and output a ready-to-run invocation. Do not pre-load all 17 standards skills — select only those relevant to the matched task.

---

This is the authoritative routing table for the BUK plugin marketplace.
Each entry describes what problem a plugin solves, not just what it is.

## Plugin Groups

---

### Discovery — upstream product delivery

Problems: defining requirements, designing journeys, writing copy, architecture, security design.

| Plugin | Solves | Entry point | Key inputs | Status |
|---|---|---|---|---|
| `barclays-buk-product-manager` | "I need to turn a problem statement into requirements, acceptance criteria, or a Consumer Duty artefact" | `product-manager-agent` | Problem statement, initiative name | Draft |
| `barclays-buk-ux-designer` | "I need journey options, UX wireframes, or a copy brief for a new feature" | `ux-designer-agent` | PM requirements, customer problem | Draft |
| `barclays-buk-copywriter` | "I need customer-facing or UI copy that is clear, accessible, and Consumer Duty compliant" | `copywriter-agent` | UX brief, channel (app/web/letter/SMS) | Draft |
| `barclays-buk-solution-architect` | "I need architecture diagrams, NFRs, or technical guardrails for a solution" | `solution-architect-agent` | PM requirements, existing system context | Draft |
| `barclays-buk-security-architect` | "I need a threat model, security review, or compliance validation" | `security-architect-agent` | Solution design, codebase path | Draft |

---

### Frontend — UI screen generation

Problems: generating screens, components, ViewModels, navigation from Figma or descriptions.

| Plugin | Solves | Entry point | Key inputs | Status |
|---|---|---|---|---|
| `barclays-buk-ui-engineer` | "I need to build UI screens and don't know which platform plugin to use" — auto-detects from project | `ui-engineer-agent` | `PROJECT_PATH`, `FIGMA_URL` or description, `JIRA_ID` | Available |
| `barclays-buk-ui-engineer-sdf` | "I need screens for a Chameleon/React Native SDF journey (`@barclays/chameleon-blueprint`)" | `ui-engineer-sdf-screen-composer-agent` | `PROJECT_PATH`, `FIGMA_URL`, `JIRA_ID` | Available |
| `barclays-buk-ui-engineer-ios` | "I need SwiftUI screens for a Barclays iOS app using BarclaysBlueprint" | `ui-engineer-ios-screen-composer-agent` | `PROJECT_PATH`, `FIGMA_URL`, `JIRA_ID` | Available |
| `barclays-buk-ui-engineer-android` | "I need Jetpack Compose screens for a generic Barclays Android app" | `ui-engineer-android-screen-composer-agent` | `PROJECT_PATH`, `FIGMA_URL`, `JIRA_ID` | Available |
| `barclays-buk-ui-engineer-android-tba` | "I need screens or journey steps inside the BMB monorepo (The Barclays App)" | `ui-engineer-android-tba-worker-agent` | `PROJECT_PATH`, `FIGMA_URL`, `JIRA_ID`, `PLATFORM_OPTIONS` with `package` and `teamScope` | Available |
| `barclays-buk-ui-engineer-web` | "I need React pages for Online Banking web using `@barclays/blueprint-react`" | `ui-engineer-web-worker-agent` | `PROJECT_PATH`, `FIGMA_URL`, `JIRA_ID` | Available |

**When platform is unknown or ambiguous:** use `barclays-buk-ui-engineer` (`ui-engineer-agent`) — it auto-detects and routes to the correct specialist. **When platform is already known** (from project inspection or explicit problem description): route directly to the platform-specific plugin to avoid an unnecessary dispatcher hop.

#### How the ui-engineer family works

**Dispatcher → specialist model.** `ui-engineer-agent` is a dispatcher, not a generator. It inspects the project, detects the platform, runs Figma screen discovery, pre-fetches design context, then outputs a ready-to-paste input block for the user to run in the correct specialist agent. It does not invoke specialists as subagents.

**Why the user must run the specialist themselves.** Figma MCP connections are session-scoped — they do not propagate to subagents. Screen discovery (calling `figma-local / get_design_context`) must happen in the user's own Claude session. The dispatcher runs this step, writes the results to `{PROJECT_PATH}/.claude/preview/`, then hands off.

**Feedback loop — validation → auto-fix → continue.** After screen generation, the pipeline runs a validation agent (platform-specific red-flag checks). If validation returns REJECTED, the agent attempts auto-fixes and re-validates. Issues it cannot fix are surfaced as flags but do not halt the pipeline — test and mutation phases run independently. The full SDF pipeline order is: `screen-composer` → `validation` → `api` → `test` → `mutation`. Non-SDF platforms (iOS, Android, Web) run: `screen-composer` → `validation` → `test`.

**ViewModel and navigation are not auto-chained** on non-SDF platforms — they require OAS spec and route topology decisions that need a human. The pipeline flags them as manual next steps after validation passes.

**Visual preview with `agent-device` (SDF only).** After screen generation, the SDF pipeline runs a visual validation step using `agent-device` — a CLI tool that controls an iOS simulator. It starts Metro, opens the shell app, captures a screenshot, and inspects the React DevTools component tree to verify typography mapping (e.g. catches `size="md"` resolving to 18px Medium when body text should be 16px Regular). It then does a structured visual diff against the Figma reference screenshot. This step is a **hard stop** — if `agent-device` is not installed the agent will refuse to declare success, since structural checks alone cannot catch layout drift or missing components. Install once with `npm install -g agent-device@latest` and ensure a simulator is running before invoking the SDF pipeline.

---

### Backend — API and data services

Problems: building DAF API endpoints, data pipelines, migrations, modelling.

| Plugin | Solves | Entry point | Key inputs | Status |
|---|---|---|---|---|
| `barclays-buk-api-engineer` | "I need to define a DAF API contract, build endpoints, or generate OpenAPI documentation" | `api-engineer-agent` | OAS spec or problem description, `PROJECT_PATH` | Draft |
| `barclays-buk-data-engineer` | "I need to build a data pipeline, model a schema, migrate a database, profile PII, or assess data technology" | `data-engineer-agent` | Requirement description, source system details, target platform | Available |

---

### Quality — testing, auditing, reliability

Problems: writing tests, auditing accessibility, reviewing code quality, managing incidents.

| Plugin | Solves | Entry point | Key inputs | Status |
|---|---|---|---|---|
| `barclays-buk-quality-engineer` | "I need unit tests, integration tests, or a test strategy for a feature" | `quality-engineer-agent` | `PROJECT_PATH`, feature description | Draft |
| `barclays-buk-accessibility-auditor` | "I need to audit a screen or journey for WCAG 2.2 AA / Barclays accessibility compliance" | `accessibility-auditor-agent` | Screen file path or description | Draft |
| `barclays-buk-reliability-engineer` | "I need observability coverage, OTel instrumentation, or an SLO review" | `reliability-engineer-agent` | `PROJECT_PATH`, service name | Available |
| `barclays-buk-incident-manager` | "I need to manage or document a live incident" | `incident-manager-agent` | Incident description, severity | Draft |

---

### Tooling — platform utilities

Problems: fixing vulnerabilities, reading Confluence, scaffolding new repos, generating specs.

| Plugin | Solves | Entry point | Key inputs | Status |
|---|---|---|---|---|
| `barclays-buk-detox` | "I have Wiz SAST or SCA findings to remediate" | `detox-orchestrator-agent` | Wiz report path, `PROJECT_PATH` | Available |
| `barclays-buk-confluence` | "I need to search, read, or ask questions against internal Confluence documentation" | `confluence-agent` | `OPERATION`, `QUERY` | Available |
| `barclays-buk-scaffold` | "I need to create a new SDF journey repository from an approved template" | `scaffold-agent` | Journey name, team, platform | Available |
| `barclays-buk-reverse-spec-generator` | "I need to generate BDD specifications from existing code" | `reverse-spec-generator-agent` | `PROJECT_PATH`, feature scope | Available |
| `barclays-buk-plugin-testing-toolkit` | "I need to test or validate a plugin I've built" | `plugin-tester` | Plugin path | Available |

---

### Migration — one-off migration jobs

Problems: upgrading Java versions, migrating between MCA generations, SDK upgrades.

| Plugin | Solves | Entry point | Key inputs | Status |
|---|---|---|---|---|
| `barclays-buk-sdk3-migration` | "I need to migrate a Barclays iAPI service from SDK2 (Java 8) to SDK3 (Java 21)" | `/sdk3-migrate` command | `PROJECT_PATH` | Available |
| `barclays-buk-mca-jdk-upgrade` | "I need to upgrade an MCA1 or MCA2 service from Java 8 to Java 21" | `/mca1-jdk-upgrade` or `/mca2-jdk-upgrade` command | `PROJECT_PATH` | Available |
| `barclays-buk-mca1-ui-mca2-migration` | "I need to migrate MCA1 JMVC/BDL UI to MCA2 React" | `mca1-transform-agent` | `PROJECT_PATH` | Available |
| `barclays-buk-mts-migrate-toolkit` | "I need to migrate an MTS Spring Boot application" | `mts-migrate-agent` | `PROJECT_PATH`, MTS service details | Available |

---

### Standards — cross-cutting (loaded dynamically, not invoked directly)

The `barclays-buk-standards` plugin provides 17 skills loaded by all other plugins. Users do not invoke it directly — the discover agent loads relevant skills automatically based on the task.

| Skill | Relevant when |
|---|---|
| `accessibility` | Any UI generation or audit task |
| `security` | Any code generation, API design, or security review |
| `consumer-duty` | Any customer-facing product, journey, or communication |
| `vulnerable-customers` | Any customer journey or communication design |
| `customer-engagement` | Any customer communication (app, email, SMS, letter) |
| `api-design` | Any DAF service or API contract work |
| `daf` | Any DAF Java service implementation |
| `testing` | Any test generation or coverage review |
| `ux` | Any journey design or wireframing task |
| `brand` | Any customer-facing copy or visual design |
| `governance` | Any governance artefact, RAID log, or change control |
| `tads-lean-control` | Any TADS artefact, Risk Story, or release gate |
| `observability` | Any logging, tracing, or telemetry implementation |
| `performance` | Any NFR definition or latency/load testing work |
| `data` | Any data model, schema, or PII handling task |
| `mobile` | Any iOS or Android feature implementation |
| `infrastructure` | Any deployment pipeline or infrastructure config |
| `adr` | Any architectural decision that needs recording |

---

## Agent Self-Check

Before using this index to route:

- [ ] Have I read the full "Solves" column for candidate plugins, not just the plugin name?
- [ ] If the problem mentions a specific platform (iOS/Android/SDF/Web), have I routed to the platform-specific plugin rather than the dispatcher?
- [ ] If the plugin I am recommending is marked Draft or Planned, have I stated that in the Flags section of my output?
- [ ] Have I selected only the `barclays-buk-standards` skills that genuinely apply — not all 17?
- [ ] If the problem spans two plugin groups, have I asked one clarifying question rather than guessing?
- [ ] Is the workflow position I have described accurate (what comes before, what comes after)?
