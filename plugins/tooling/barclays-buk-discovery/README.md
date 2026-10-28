# barclays-buk-discovery

> **Status: Trial**

Marketplace discover agent for BUK. Describe a problem — get routed to the right plugin, agent, and entry point with a ready-to-run invocation.

## The problem it solves

The BUK marketplace has 30+ plugins across 6 groups and can be difficult to discover the right agent/skill for a particular task. This discover agent takes a plain-English problem description and maps it to the correct tool.

## Usage

```
Run discover-agent with:

PROBLEM:        I need to build a new savings account screen for the iOS app
PROJECT_PATH:   /Users/me/code/my-ios-project
```

```
Run discover-agent with:

PROBLEM:        I have Wiz SAST findings to fix in a Java service
PROJECT_PATH:   /Users/me/code/my-api-service
```

```
Run discover-agent with:

PROBLEM:        I need to write acceptance criteria and Consumer Duty obligations for a new overdraft feature
PROJECT_PATH:   unknown
```

## What you get back

- **Recommended plugin and agent** with a one-line reason
- **Ready-to-paste invocation block** with inputs pre-filled where possible
- **Relevant standards skills** from `barclays-buk-standards` that apply to the task
- **Workflow position** — what comes before and after

## Plugin groups covered

| Group | Plugins |
|---|---|
| Discovery | product-manager, ux-designer, copywriter, solution-architect, security-architect |
| Frontend | ui-engineer (dispatcher), sdf, ios, android, android-tba, web |
| Backend | api-engineer, data-engineer |
| Quality | quality-engineer, accessibility-auditor, reliability-engineer, incident-manager |
| Tooling | detox, confluence, scaffold, reverse-spec-generator, plugin-testing-toolkit |
| Migration | sdk3-migration, mca-jdk-upgrade, mca1-ui-mca2-migration, mts-migrate-toolkit |

## Dependencies

- `barclays-buk-standards` — standards skills loaded dynamically per task

## Agents

| Agent | Purpose |
|---|---|
| `discover-agent` | Routes a problem description to the correct plugin and outputs a ready-to-run invocation |
