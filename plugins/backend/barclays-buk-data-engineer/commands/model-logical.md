---
name: model-logical
description: Produce a platform-independent logical data model from requirements and/or mappings.
agent: logical-data-modeller
user-invocable: true
---

## Purpose

Produce a platform-independent logical data model (entities, attributes, relationships, cardinalities) from requirement assessments and/or approved mappings. The logical model is free of physical implementation detail and serves as the authoritative semantic layer that physical modelling, pipeline generation, and DQ rule creation can reference.

## Usage

```
/model-logical [--requirements <path>] [--mapping <path>] [--existing-model <path>] [--patterns <path>] [--output <path>] [--help]
```

At least one of `--requirements` or `--mapping` must be supplied.

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--requirements` | Required if `--mapping` not supplied | Path to a requirements assessment artefact (output of `/assess`). |
| `--mapping` | Required if `--requirements` not supplied | Path to an approved mapping file (output of `/map`). Both may be supplied together. |
| `--existing-model` | Optional | Path to an existing logical model to extend or refactor rather than create from scratch. |
| `--patterns` | Optional | Path or reference to approved modelling patterns (entity naming conventions, canonical types, relationship rules). If omitted, the agent applies default enterprise patterns and notes this as PROPOSED. |
| `--output` | Optional | Directory path to write logical model artefacts. Defaults to `./output/model/logical/`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Produce a logical model from a requirements assessment:**
```
/model-logical --requirements ./output/assessment/assessment.json --output ./output/model/logical/v1/
```

**2. Produce a logical model from an approved mapping, extending an existing model:**
```
/model-logical --mapping ./mappings/crm-to-cdp-approved.json --existing-model ./models/logical/cdp-v2.json --output ./output/model/logical/v3/
```

**3. Produce a logical model from both requirements and mapping with explicit pattern reference:**
```
/model-logical --requirements ./output/assessment/assessment.json --mapping ./mappings/crm-to-cdp-approved.json --patterns ./standards/modelling-patterns-v4.yaml --output ./output/model/logical/final/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `logical-model.json` — The logical data model containing:
  - `entities[]` — Each entity with name, description, canonical identifier, and source traceability to requirement or mapping.
  - `attributes[]` — Per entity: attribute name, logical type, nullable, description, and FR/NFR traceability references.
  - `relationships[]` — Entity pairs with relationship name, cardinality (`1:1`, `1:N`, `M:N`), and optionality.
  - `applied_patterns[]` — Modelling patterns applied and their versions.
  - `loaded_standards[]` — Standards and versions consulted.
  - `unverified_assumptions[]` — Relationship cardinalities or entity boundaries inferred without explicit requirement evidence.
- `logical-model-diagram.md` — Mermaid ER diagram of the logical model for visual review.
- `logical-model-summary.md` — Human-readable narrative of the model structure.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Logical model produced successfully. |
| `1` | Neither `--requirements` nor `--mapping` supplied. |
| `2` | Requirements or mapping file not found. |
| `3` | Existing model file not found (when `--existing-model` supplied). |
| `4` | Input artefacts contain insufficient entity information to produce a model; check `unverified_assumptions[]`. |
| `10` | Patterns file not found or unreadable; default patterns applied and flagged PROPOSED. |

## Related Commands

- `/model-physical` — Translate this logical model into platform-specific physical structures and DDL.
- `/map` — Create or validate the mapping that feeds into this logical model.
- `/assess` — Produce the requirements assessment artefact that this command consumes.
