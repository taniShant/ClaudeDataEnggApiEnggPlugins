# Generality, Hardcoding, and Portability Audit

This audit is mandatory for Agents, Skills, workflows, hooks, scripts, and configuration.

## Core test

For each rule/value ask:

> Would this still be correct if installed in another appropriate repository by another team?

If not, determine the correct scope rather than immediately deleting it.

## Classifications

### Durable generic principle
Keep in reusable expert methodology.

### Intentionally domain-scoped rule
Keep only if the component explicitly declares that domain scope.

### Organisation policy
Move to the organisation-managed policy/configuration layer appropriate to the environment.

### Team convention
Keep in team-scoped configuration/knowledge, not generic plugin methodology.

### Project constraint
Project-scoped configuration/context.

### Runtime configuration
Parameter, config, environment, input, or runtime discovery.

### Example
Mark as example. Do not allow it to become normative language.

### Accidental hardcoding
Generalise, parameterise, or remove.

### Secret/sensitive value
P0. Remove from reusable source and use an appropriate secret/config mechanism.

## Hardcoding indicators

Inspect for:

- repository names
- absolute paths
- fixed branches
- account/project IDs
- URLs/endpoints
- region/environment names
- team/user names
- model names without a requirement
- fixed agent names coupled to one implementation
- fixed tool/MCP assumptions
- thresholds/timeouts/concurrency values without rationale
- output locations
- technology/product choices presented as universal
- project-specific acceptance criteria
- sample values written as MUST rules
- copied decisions from previous tasks

## Hardcoding is not automatically wrong

Valid hardcoding includes true invariants, protocol constants, stable plugin-owned paths, or deliberately scoped policy. Require an explanation of why the value is invariant.

## Required report table

| Value/rule | Location | Classification | Valid? | Recommended home/action | Severity |
|---|---|---|---|---|---|
