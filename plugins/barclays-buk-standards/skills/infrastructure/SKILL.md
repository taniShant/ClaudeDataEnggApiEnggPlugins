---
name: infrastructure
description: BUK infrastructure and deployment standards. Covers Service Mesh configuration, cluster deployment conventions, environment promotion, secrets management at infrastructure level, and IaC standards. Use when designing or reviewing deployment pipelines, infrastructure configs, or runtime environments.
user-invocable: false
---

# BUK Infrastructure Standards

> **Placeholder — owned by BUK Platform Engineering.**
> This skill needs content derived from BUK infrastructure standards, Service Mesh (VINZ) configuration guidelines, and cluster deployment runbooks.
> See `docs/shared-standards-approach.md` for context on how this skill fits into the shared standards architecture.

---

## Areas to Cover

### Service Mesh (VINZ)
- Required VINZ configuration for DAF API deployment
- mTLS requirements between services
- Traffic policy conventions (retries, timeouts at mesh level)
- Service discovery and registry integration (Digital Registry)

### Cluster Deployment
- Approved cluster types and their intended workloads
- Resource requests and limits conventions (CPU, memory)
- Horizontal pod autoscaling configuration
- Pod disruption budgets for high-availability services
- Channel-specific cluster deployment patterns

### Environment Promotion
- Environment tiers: dev → test → staging → production
- Promotion gates — what must pass before promotion
- Environment parity expectations
- Non-production data seeding constraints (no real PII)

### Infrastructure as Code
- Approved IaC tooling (Ansible — see `buk-chef2ansible` for Chef migration context)
- Repository structure for IaC
- Review and approval process for infrastructure changes
- Drift detection and remediation

### Secrets Management at Infrastructure Level
- Secrets store — approved platform for infrastructure secrets
- Rotation policy for infrastructure credentials
- Access control for secrets (least privilege)
- See `barclays-buk-standards:security` for application-level secrets rules

### Networking
- Ingress/egress rules and approved patterns
- Internal vs. external service exposure
- DNS conventions

### Observability Integration
- Required sidecar/agent configuration for logging and tracing
- Health check endpoint conventions (`/health`, `/ready`)
- See `barclays-buk-standards:observability` for metrics and alerting standards

---

## How to Contribute

Raise the source documents with BUK Platform Engineering. Suggested inputs:

- VINZ / Service Mesh configuration guide
- Cluster deployment runbook
- IaC standards and conventions document
- Environment promotion checklist
