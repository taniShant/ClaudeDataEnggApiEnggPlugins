# BUK CIO Marketplace

Claude Code plugin marketplace for BUK (Barclays UK) CIO Area. This is a Tier 2b CIO Area Marketplace as defined in [DEVAITOOLING 011.00: Enterprise Claude Plugin Marketplace](https://app.gitlab.barcapint.com/barclays/dspe/architecture/-/blob/main/adr/ai-dev-tooling/011.00-claude-code-marketplace/README.md).

## Requirements

**Minimum Claude Code version: 2.1.110**

Plugin dependencies (`barclays-buk-standards` and others) are auto-installed on versions 2.1.110+. On older versions you must install dependencies manually in order.

Check your version with `/doctor`. Upgrade via:
```bash
brew upgrade claude-code   # Homebrew
# or
npm install -g @anthropic-ai/claude-code@latest
```

## Installation

```bash
# Register the marketplace
/marketplace add barclays-cio-buk git@app.gitlab.barcapint.com:barclays/claude/marketplace/cio/buk.git

# List available plugins
/marketplace browse barclays-cio-buk

# Install a specific plugin
/plugin install <plugin-name>@barclays-cio-buk
```

### Manual install order (Claude Code < 2.1.110 only)

Dependencies are not auto-installed on older versions. Install in this order:

```bash
/plugin install barclays-buk-standards@barclays-cio-buk
# then install whichever plugins you need, e.g.:
/plugin install barclays-buk-ui-engineer-sdf@barclays-cio-buk
/plugin install barclays-buk-ui-engineer-ios@barclays-cio-buk
/plugin install barclays-buk-ui-engineer-android@barclays-cio-buk
/plugin install barclays-buk-ui-engineer-android-tba@barclays-cio-buk
/plugin install barclays-buk-ui-engineer-web@barclays-cio-buk
/plugin install barclays-buk-ui-engineer@barclays-cio-buk
/plugin install barclays-buk-detox@barclays-cio-buk
```

## Quickstart — UI Engineer

The most common use case: generating screens from a Figma design into your project.

**1. Install the UI engineer plugins**

```bash
/plugin install barclays-buk-ui-engineer@barclays-cio-buk
/plugin install barclays-buk-ui-engineer-android-tba@barclays-cio-buk  # BMB Android (TBA)
/plugin install barclays-buk-ui-engineer-android@barclays-cio-buk       # generic Android
/plugin install barclays-buk-ui-engineer-ios@barclays-cio-buk           # iOS
/plugin install barclays-buk-ui-engineer-sdf@barclays-cio-buk           # SDF / React Native
/plugin install barclays-buk-ui-engineer-web@barclays-cio-buk           # Online Banking web
```

Install only what your platform needs. `barclays-buk-standards` is pulled in automatically as a dependency.

**2. Open Claude Code in your project**

```bash
cd /path/to/your/project
claude
```

**3. Invoke the UI engineer agent**

The dispatcher auto-detects your platform from project signals and routes to the right specialist. Provide at minimum a `PROJECT_PATH`, `JIRA_ID`, and either a Figma URL or a description.

```
PROJECT_PATH:     /path/to/your/project
JIRA_ID:          PLATENG-1234
FIGMA_URL:        https://www.figma.com/design/...
```

**Platform-specific examples:**

BMB Android TBA (auto-detected via `barclays.behaviourSdk` in `build.gradle`):
```
PROJECT_PATH:     /path/to/bmb/cardshubteam/lowlevel/cardshubinternal
JIRA_ID:          EMMCARDSFT-13436
FIGMA_URL:        https://www.figma.com/design/KSebbgxMYA38WxILZIV179/...?node-id=44826-21641
PLATFORM_OPTIONS: {"package": "com.barclays.bmb.features.cardshub.blueprint", "teamScope": "CardshubScope"}
```

iOS (auto-detected via `.xcodeproj` / `.xcworkspace` / `.podspec`):
```
PROJECT_PATH:     /path/to/ios/CardDetails
JIRA_ID:          UCG-5678
FIGMA_URL:        https://www.figma.com/design/...
```

SDF / React Native (auto-detected via `@barclays/chameleon-blueprint` in `package.json`):
```
PROJECT_PATH:     /path/to/sdf/card-details
JIRA_ID:          UCG-5678
FIGMA_URL:        https://www.figma.com/design/...
```

**4. Follow the generated next steps**

The agent writes files to your project and prints a completion report with suggested next steps — wiring ViewModels to an API spec, generating navigation, adding tests, running the quality gate. Each of those is a separate independently invocable agent you call in order.

---

## Available plugins

### Standards

Shared standards and domain knowledge. All other plugins depend on this.

| Plugin | Status | Description |
|---|---|---|
| [barclays-buk-standards](plugins/barclays-buk-standards/) | ✅ Available | Shared skills: accessibility, security, consumer-duty, vulnerable-customers, customer-engagement, api-design, testing, governance, ux, brand, performance, observability, data, mobile, infrastructure, adr |

### Discovery

Plugins covering the upstream product delivery phases — from problem statement through to technical design.

| Plugin | Status | Agent | Description |
|---|---|---|---|
| [barclays-buk-product-manager](plugins/discovery/barclays-buk-product-manager/) | 🚧 Draft | `product-manager-agent` | Requirements, AC, increment priority, success measures, governance flags |
| [barclays-buk-ux-designer](plugins/discovery/barclays-buk-ux-designer/) | 🚧 Draft | `ux-designer-agent` | Journey options, UX design, research insights |
| [barclays-buk-copywriter](plugins/discovery/barclays-buk-copywriter/) | 🚧 Draft | `copywriter-agent` | Customer-facing and UI copy for journeys and communications |
| [barclays-buk-solution-architect](plugins/discovery/barclays-buk-solution-architect/) | 🚧 Draft | `solution-architect-agent` | Architecture diagrams, NFRs, technical guardrails |
| [barclays-buk-security-architect](plugins/discovery/barclays-buk-security-architect/) | 🚧 Draft | `security-architect-agent` | Threat modelling, security review, compliance validation |

### Frontend

| Plugin | Status | Agent | Channel | Tech |
|---|---|---|---|---|
| [barclays-buk-ui-engineer](plugins/frontend/barclays-buk-ui-engineer/) | ✅ Available | `ui-engineer-agent` | All | Cross-platform dispatcher — auto-routes to platform specialist |
| [barclays-buk-ui-engineer-sdf](plugins/frontend/barclays-buk-ui-engineer-sdf/) | ✅ Available | `ui-engineer-sdf-worker-agent` | OB, Mobile | SDF / Blueprint React Native (`@barclays/chameleon-blueprint`) |
| [barclays-buk-ui-engineer-ios](plugins/frontend/barclays-buk-ui-engineer-ios/) | ✅ Available | `ui-engineer-ios-screen-composer-agent` | OB, Mobile | SwiftUI + BarclaysBlueprint |
| [barclays-buk-ui-engineer-android](plugins/frontend/barclays-buk-ui-engineer-android/) | 🚧 Draft | `ui-engineer-android-screen-composer-agent` | Mobile | Jetpack Compose / Blueprint Compose |
| [barclays-buk-ui-engineer-android-tba](plugins/frontend/barclays-buk-ui-engineer-android-tba/) | ✅ Available | `ui-engineer-android-tba-worker-agent` | Mobile | BMB TBA — Journey Framework, BarclaysActivity, Scopes |
| [barclays-buk-ui-engineer-web](plugins/frontend/barclays-buk-ui-engineer-web/) | 🚧 Draft | `ui-engineer-web-worker-agent` | Online Banking | Blueprint React (`@barclays/blueprint-react`) |
| [barclays-buk-ui-engineer-mca](plugins/frontend/barclays-buk-ui-engineer-mca/) | 🚧 Planned | — | FullServe, OB, MAE, Mobile web | MCA / `@barclays/blueprint-react` |

### Backend

| Plugin | Status | Agent | Description |
|---|---|---|---|
| [barclays-buk-api-engineer](plugins/backend/barclays-buk-api-engineer/) | 🚧 Draft | `api-engineer-agent` | API contracts, endpoint implementation, OpenAPI documentation |
| [barclays-buk-data-engineer](plugins/backend/barclays-buk-data-engineer/) | 🚧 Draft | `data-engineer-agent` | Data models, schema changes, migration scripts |

### Quality

| Plugin | Status | Agent | Description |
|---|---|---|---|
| [barclays-buk-quality-engineer](plugins/quality/barclays-buk-quality-engineer/) | 🚧 Draft | `quality-engineer-agent` | Test generation, coverage validation, edge cases |
| [barclays-buk-accessibility-auditor](plugins/quality/barclays-buk-accessibility-auditor/) | 🚧 Draft | `accessibility-auditor-agent` | WCAG 2.2 AA compliance auditing |
| [barclays-buk-reliability-engineer](plugins/quality/barclays-buk-reliability-engineer/) | 🚧 Draft | `reliability-engineer-agent` | Performance, observability, resilience, deployment readiness |
| [barclays-buk-incident-manager](plugins/quality/barclays-buk-incident-manager/) | 🚧 Draft | `incident-manager-agent` | Log analysis, incident investigation, RCA |

### Infrastructure

| Plugin | Status | Description |
|---|---|---|
| _None yet_ | — | Infrastructure automation plugins |

### Domain

| Plugin | Status | Description |
|---|---|---|
| [barclays-buk-data-product-builder](plugins/domain/barclays-buk-data-product-builder/) | 🚧 Draft | Data modelling, source-to-target mapping, PySpark pipeline generation (Glue/Databricks), and data validation SQL generation from Excel mappings |

### Tooling

| Plugin | Status | Description |
|---|---|---|
| [barclays-buk-plugin-testing-toolkit](plugins/tooling/barclays-buk-plugin-testing-toolkit/) | ✅ Available | Plugin testing, quality assurance, and validation toolkit |
| [barclays-buk-reverse-spec-generator](plugins/tooling/barclays-buk-reverse-spec-generator/) | ✅ Available | Generate BDD-style behavioral specifications from existing code |
| [barclays-buk-software-catalogue](plugins/tooling/barclays-buk-software-catalogue/) | 🚧 Draft | Navigate the Barclays Software Catalogue (Backstage) — domains, APIs, journeys, service owners, and architecture guidance |
| [barclays-buk-scaffold](plugins/tooling/barclays-buk-scaffold/) | 🚧 Planned | Template scaffolding for BUK journey repos |
| [barclays-buk-improve-tests](plugins/tooling/barclays-buk-improve-tests/) | 🚧 Planned | Test coverage improvement |
| [barclays-buk-observe-opal](plugins/tooling/barclays-buk-observe-opal/) | 🚧 Planned | OPAL query assistant and metric converter |
| [barclays-buk-vulnerability](plugins/tooling/barclays-buk-vulnerability/) | 🚧 Planned | Vulnerability scanning and remediation |

### Migration

| Plugin | Status     | Description |
|---|------------|---|
| [barclays-buk-smesh-api-maintainer](plugins/migration/barclays-buk-smesh-api-maintainer/) | 🚧 Planned | SDK2 to SDK3 migration toolkit and SDK3 to SDK4 uplift |
| [barclays-buk-mca-jdk-upgrade](plugins/migration/mca-plugins/barclays-buk-mca-jdk-upgrade/) | 🚧 Planned | Java 8 to 21 JDK upgrade |
| [barclays-buk-mca1-to-mca2-eps](plugins/migration/mca-plugins/barclays-buk-mca1-to-mca2-eps/) | 🚧 Planned | MCA1 to MCA2 EPS migration |
| [barclays-buk-mca1-ui-mca2-migration](plugins/migration/mca-plugins/barclays-buk-mca1-ui-mca2-migration/) | 🚧 Planned | MCA1 to MCA2 UI migration |
| [barclays-buk-oracle-to-postgres-app-migration](plugins/migration/barclays-buk-oracle-to-postgres-app-migration/) | 🚧 Planned | Oracle to PostgreSQL Spring Boot application migration |
| [barclays-buk-mts-migrate-toolkit](plugins/migration/barclays-buk-mts-migrate-toolkit/) | 🚧 Planned | MTS service discovery and migration |

## Status key

| Status | Meaning |
|---|---|
| ✅ Available | Installed and working |
| 🚧 Draft | Structure and agents built, not yet fully tested |
| 🚧 Planned | README only — not yet built |

## Keeping plugins up to date

```bash
/marketplace sync barclays-cio-buk
```

Plugins in this marketplace do not use explicit versioning. Every push to the plugin source is treated as a new version. Running the sync command gives you the latest.

## Naming convention

All plugins follow the `barclays-buk-<name>` convention per [ADR 011.00](https://app.gitlab.barcapint.com/barclays/dspe/architecture/-/blob/main/adr/ai-dev-tooling/011.00-claude-code-marketplace/README.md#plugin-naming-convention):

- Marketplace name: `barclays-cio-buk`
- Plugin name pattern: `barclays-buk-<name>` — e.g., `barclays-buk-api-engineer`
- Full install key: `barclays-buk-<name>@barclays-cio-buk`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution workflow — from idea alignment through piloting, stats, and raising an MR.

## Documentation

| Doc | Description |
|---|---|
| [docs/plugin-principles.md](docs/plugin-principles.md) | Seven principles governing plugin, agent, and skill design |
| [docs/plugin-architecture.md](docs/plugin-architecture.md) | Architecture diagram showing plugin and skill relationships |
| [docs/shared-standards-approach.md](docs/shared-standards-approach.md) | How shared standards work — dependencies, skill loading, extension pattern |
| [docs/templates/AUTHORING.md](docs/templates/AUTHORING.md) | Plugin authoring guide with principles checklist |
| [docs/templates/agent.md.template](docs/templates/agent.md.template) | Agent file template |
| [docs/templates/skill.md.template](docs/templates/skill.md.template) | Skill file template |
| [docs/templates/plugin.json.template](docs/templates/plugin.json.template) | Plugin manifest template |

## Ownership

| | |
|---|---|
| **Tier** | CIO Area (2b) |
| **Scope** | BUK CIO domain |
| **Owner** | BUK Retail CAPL |
| **Marketplace maintainer** | @senthilnathan.thiyagasundaramumashankar |
| **Approvers** | See [CODEOWNERS](CODEOWNERS) |
