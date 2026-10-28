# Capability Landscape

> Narrow by domain/stage/scope, then load details/<id>.md for full contract.
> No credible candidates → no-fit.
> Rev: 346ead6eeb5f | 2026-09-23 | 56 caps
> Scope: ro=read-only, local-mod=local-modification, ext-conseq=externally-consequential
> Mode: usr=user-only, model=model-invocable, tool=tool/agent-plugin

## Domains

### api-service-creation
- barclays-buk-api-engineer-api-engineer-agent-v1 | design,build | ext-conseq | tool
- barclays-buk-api-engineer-create-v1 | build | ext-conseq | usr

### frontend-sdf
- barclays-buk-scaffold-sdf-v1 | design | local-mod | model
- barclays-buk-ui-engineer-sdf-ui-engineer-sdf-v1 | build | local-mod | usr
- barclays-buk-ui-engineer-sdf-ui-engineer-sdf-worker-agent-v1 | build | ext-conseq | tool

### frontend-web
- barclays-buk-ui-engineer-ui-engineer-agent-v1 | build | ext-conseq | tool
- barclays-buk-ui-engineer-web-ui-engineer-web-worker-agent-v1 | build | ext-conseq | tool

### frontend-mobile
- barclays-buk-ui-engineer-android-tba-android-tba-v1 | build | local-mod | model
- barclays-buk-ui-engineer-android-ui-engineer-android-worker-agent-v1 | build | ext-conseq | tool
- barclays-buk-ui-engineer-ios-ui-engineer-ios-worker-agent-v1 | build | ext-conseq | tool

### data-engineering
- barclays-buk-data-engineer-assess-v1 | design | local-mod | usr
- barclays-buk-data-engineer-run-v1 | build | ext-conseq | usr
- barclays-buk-data-product-builder-init-v1 | build | local-mod | usr

### reliability-observability
- barclays-buk-reliability-engineer-implement-v1 | build | local-mod | usr
- barclays-buk-reliability-engineer-plan-observability-v1 | design | local-mod | model
- barclays-buk-reliability-engineer-plan-performance-v1 | design | local-mod | model
- barclays-buk-reliability-engineer-plan-resilience-v1 | design | local-mod | model
- barclays-buk-reliability-engineer-review-observability-v1 | build,verify | ro | model
- barclays-buk-reliability-engineer-review-performance-v1 | build,verify | ro | model
- barclays-buk-reliability-engineer-review-resilience-v1 | build,verify | ro | model
- barclays-buk-reliability-engineer-status-v1 | any | ro | model

### refactoring
- barclays-buk-strangler-refactoring-strangler-discover-v1 | design | local-mod | usr
- barclays-buk-strangler-refactoring-strangler-extract-v1 | build | local-mod | usr
- barclays-buk-strangler-refactoring-strangler-plan-v1 | design | local-mod | usr

### migration
- barclays-buk-mca-jdk-upgrade-mca1-jdk-upgrade-v1 | build | local-mod | usr
- barclays-buk-mca-jdk-upgrade-mca2-jdk-upgrade-v1 | build | local-mod | usr
- barclays-buk-mca1-to-mca2-eps-mca1-to-mca2-eps-v1 | build | local-mod | model
- barclays-buk-mca1-ui-mca2-migration-mca1-migration-v1 | build | local-mod | usr
- barclays-buk-mts-migrate-toolkit-mts-documentation-v1 | design,build | ro | usr
- barclays-buk-mts-migrate-toolkit-mts-migrate-v1 | build | ext-conseq | usr
- barclays-buk-nx-angular-migration-toolkit-angular-nx-enterprise-migration-v1 | build | local-mod | model
- barclays-buk-sdk3-migration-sdk3-migrate-v1 | build | ext-conseq | usr

### knowledge-documentation
- barclays-buk-confluence-confluence-comments-v1 | design,build | ro | model
- barclays-buk-confluence-confluence-history-v1 | design,build | ro | model
- barclays-buk-confluence-confluence-rag-ask-v1 | design,build | ro | model
- barclays-buk-confluence-confluence-read-v1 | design,build | ro | model
- barclays-buk-confluence-confluence-search-v1 | design,build | ro | model
- barclays-buk-confluence-confluence-tree-v1 | design,build | ro | model
- barclays-buk-jira-jira-agent-v1 | build | ro | tool

### platform-tooling
- barclays-buk-plugin-testing-toolkit-test-plugin-v1 | verify | ext-conseq | usr
- barclays-buk-plugin-testing-toolkit-validate-plugin-v1 | verify | ro | usr
- deploy-service-v1 | build | ext-conseq | model
- infra-cost-report-v1 | any | ro | tool
- security-scan-v1 | verify | local-mod | usr

### discovery
- barclays-buk-product-manager-product-manager-agent-v1 | design | local-mod | tool
- barclays-buk-security-architect-security-architect-agent-v1 | design | ext-conseq | tool
- barclays-buk-solution-architect-solution-architect-agent-v1 | design | ext-conseq | tool
- barclays-buk-ux-designer-ux-designer-agent-v1 | design | local-mod | tool

### quality-assurance
- barclays-buk-accessibility-auditor-accessibility-auditor-agent-v1 | verify | ro | tool
- barclays-buk-quality-engineer-quality-engineer-agent-v1 | verify | local-mod | tool
- detox-remediate-v1 | build,verify | ext-conseq | usr
- detox-scan-v1 | build,verify | ro | usr

### incident-management
- barclays-buk-incident-manager-incident-manager-agent-v1 | incident | ro | tool

### content-creation
- barclays-buk-copywriter-copywriter-agent-v1 | design | local-mod | tool

### diagram-tooling
- barclays-buk-drawio-drawio-agent-v1 | design,build | local-mod | tool

### reverse-engineering
- barclays-buk-reverse-spec-generator-reverse-spec-generator-agent-v1 | verify,build | local-mod | tool

## Chains

sdf→ui-engineer-sdf (frontend-sdf)
assess→run, init→run (data-engineering)
plan-observability→implement, plan-performance→implement, plan-resilience→implement, review-observability→implement (reliability-observability)
strangler-discover→strangler-plan→strangler-extract (refactoring)
mts-documentation→mts-migrate (migration)
product-manager-product-manager-agent→ux-designer-ux-designer-agent→solution-architect-solution-architect-agent→security-architect-security-architect-agent (discovery)
scan→remediate (quality-assurance)
