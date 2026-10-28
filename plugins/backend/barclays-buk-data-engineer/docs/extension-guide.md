# Extension Guide

## Extension Model

The `barclays-buk-data-engineer` plugin exposes a set of registered extension points. Extensions add capability through these points without modifying the base plugin. This ensures that upgrades to the base plugin do not break extensions, and that extensions can be developed, versioned, and deployed independently.

Each extension declares:
- Which extension point it uses
- The compatibility range (`base_plugin_version_range`: a semver range)
- The owner team
- Tests proving base behaviour is not broken

**The base plugin must never be forked.** All customisation is additive through the extension point mechanism.

---

## Available Extension Points

| Extension Point | Interface | Description |
|---|---|---|
| `agent` | `agent.md` (system prompt) + schema refs + skill refs | Register a new specialist agent in the routing table |
| `command` | `command.md` + agent/workflow mapping | Register a new slash command |
| `skill` | `skill.md` (reusable instruction module) | Register a new skill that agents can compose |
| `schema` | JSON Schema file + registration entry | Register additional input/output schemas for new task types |
| `hook` | `hook.md` with trigger + applies_to | Register additional pre- or post-hooks |
| `standard` | Standard reference from a standards plugin | Reference an additional standard from a dependency |
| `source` | Source register entry (MCP server or static ref) | Add an approved source to the source register |
| `evidence-rule` | Evidence rule definition | Register a domain-specific evidence classification rule |
| `prompt-override` | Override block with scope + compatibility range | Override a named prompt section within a defined scope |
| `tads-stage` | Stage definition + artefact requirements | Register an additional or modified TADS workflow stage |

---

## How to Create a Platform Plugin

A platform plugin extends `barclays-buk-data-engineer` with platform-specific capability (e.g. AWS Data Platform, Databricks, streaming infrastructure).

### Example Structure

```
barclays-buk-aws-data-platform/
  .claude-plugin/
    plugin.json                  <- Declares dependency on barclays-buk-data-engineer
  agents/
    aws-pipeline-builder.md      <- Extension point: agent
    aws-cost-estimator.md        <- Extension point: agent
  commands/
    /aws-pipeline-build.md       <- Extension point: command
    /aws-cost-estimate.md        <- Extension point: command
  skills/
    aws-glue-patterns.md         <- Extension point: skill
    aws-s3-conventions.md        <- Extension point: skill
  schemas/
    aws-pipeline-input.schema.json  <- Extension point: schema
  hooks/
    validate-aws-tags.md         <- Extension point: hook
  standards/
    aws-tagging-standard.ref.json   <- Extension point: standard (reference only)
```

### plugin.json excerpt

```json
{
  "name": "barclays-buk-aws-data-platform",
  "version": "1.0.0",
  "depends_on": [
    {
      "plugin": "barclays-buk-data-engineer",
      "version_range": ">=1.0.0 <2.0.0"
    }
  ],
  "extension_points": [
    { "type": "agent", "file": "agents/aws-pipeline-builder.md" },
    { "type": "skill", "file": "skills/aws-glue-patterns.md" },
    { "type": "hook", "file": "hooks/validate-aws-tags.md" }
  ]
}
```

---

## How to Create a Domain Extension

A domain extension adds domain-specific agents, commands, and skills on top of the base plugin. It may also depend on a platform plugin.

### Example Structure

```
barclays-buk-cdao-data-products/
  .claude-plugin/
    plugin.json                  <- Declares dependency on barclays-buk-data-engineer
  agents/
    data-product-designer.md     <- Extension point: agent
    data-product-assessor.md     <- Extension point: agent
  commands/
    /design-data-product.md      <- Extension point: command
    /assess-data-product.md      <- Extension point: command
  skills/
    cdao-data-product-standards.md  <- Extension point: skill
    cdao-marketplace-conventions.md <- Extension point: skill
  schemas/
    data-product-input.schema.json  <- Extension point: schema
  standards/
    cdao-data-product-standard.ref.json  <- Extension point: standard (reference only)
```

---

## Override Rules

If an extension needs to modify the behaviour of a named component in the base plugin (e.g. a specific prompt section, a hook behaviour, a schema field), it must declare an explicit override:

```json
{
  "type": "prompt-override",
  "overrides": "barclays-buk-data-engineer/skills/assess-security.md#pii-detection-rules",
  "reason": "CDAO domain uses ML-based PII classifiers rather than heuristic patterns",
  "scope": "cdao-data-products domain only",
  "compatibility_range": ">=1.0.0 <2.0.0",
  "owner": "@cdao-data-platform-team",
  "tests": "tests/overrides/pii-detection-override.test.md"
}
```

Required override declaration fields:

| Field | Description |
|---|---|
| `overrides` | Full path to the component being overridden |
| `reason` | Why the override is necessary |
| `scope` | Which requests or contexts this override applies to |
| `compatibility_range` | Semver range of base plugin versions this override is compatible with |
| `owner` | Team or individual accountable for the override |
| `tests` | Path to tests that prove base behaviour is intact outside the declared scope |

---

## Testing Extensions

Every extension must include compatibility tests that prove:

1. The base plugin's existing agents continue to produce valid result manifests when the extension is installed.
2. The extension's new agents produce valid result manifests against their declared schemas.
3. Any overrides apply only within the declared scope and do not affect other requests.
4. All new hooks interact correctly with the base hooks (e.g. a new post-agent hook must not suppress warnings from `validate-result-manifest` or `validate-standards-provenance`).

Test files are placed in `tests/` within the extension plugin and referenced in the plugin manifest.

---

## Guidance Summary

- Never fork the base plugin. Always extend additively through registered extension points.
- Declare all dependencies with explicit version ranges.
- Declare all overrides explicitly with reason, scope, and tests.
- Compatibility tests are mandatory, not optional.
- Extension owners are responsible for updating their extensions when the base plugin releases a new major version.
