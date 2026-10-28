---
name: map
description: Create, validate or augment a source-to-target mapping.
agent: mapping-assistant
user-invocable: true
---

## Purpose

Create a new source-to-target mapping, validate an existing mapping for correctness and completeness, or augment a partial mapping with agent-suggested field alignments. All generated or augmented mappings are clearly marked PROPOSED until a human approver promotes them to APPROVED status.

## Usage

```
/map --mode <validate|generate|augment> --source-schema <path> --target-schema <path> [--mapping <path>] [--requirements <path>] [--output <path>] [--help]
```

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--mode` | Required | Operation mode. `validate` — check an existing mapping against source and target schemas. `generate` — produce a new mapping from schemas and optional requirements. `augment` — extend an existing partial mapping with agent suggestions. |
| `--source-schema` | Required | Path to the source schema definition (`.json`, `.yaml`, `.sql`, or profiling output from `/profile`). |
| `--target-schema` | Required | Path to the target schema definition (`.json`, `.yaml`, `.sql`). |
| `--mapping` | Required for `validate` and `augment`; Optional for `generate` | Path to the existing mapping file to validate or augment. |
| `--requirements` | Optional | Path to a requirements assessment artefact (output of `/assess`) to inform field alignment decisions. |
| `--output` | Optional | Directory path to write mapping artefacts. Defaults to `./output/mapping/`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Generate a new mapping from source and target schemas:**
```
/map --mode generate --source-schema ./schemas/crm-source.yaml --target-schema ./schemas/cdp-target.yaml --output ./output/mapping/crm-to-cdp/
```

**2. Validate an existing approved mapping against updated schemas:**
```
/map --mode validate --source-schema ./schemas/crm-source-v2.yaml --target-schema ./schemas/cdp-target.yaml --mapping ./mappings/crm-to-cdp-approved.json
```

**3. Augment a partial mapping using requirements context:**
```
/map --mode augment --source-schema ./schemas/crm-source.yaml --target-schema ./schemas/cdp-target.yaml --mapping ./mappings/crm-to-cdp-partial.json --requirements ./output/assessment/assessment.json --output ./output/mapping/augmented/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `mapping.json` — The mapping document containing, per field pair:
  - `source_field`, `target_field`, `transformation` (expression or rule), `confidence` (0–1, for generated/augmented entries), `status` (`PROPOSED|APPROVED`), and `justification`.
  - `unmapped_source_fields[]` — Source fields with no target alignment.
  - `unmapped_target_fields[]` — Required target fields with no source alignment.
  - `validation_errors[]` — Type mismatches, broken references, and constraint violations (validate mode).
  - `loaded_standards[]` — Naming conventions and transformation standards applied.
  - `unverified_assumptions[]` — Field alignments the agent inferred without explicit evidence.
- `mapping-summary.md` — Human-readable mapping summary with confidence highlights and unmapped field counts.

All agent-generated or agent-augmented entries carry `status: PROPOSED`. Only human-promoted entries carry `status: APPROVED`.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Operation completed. For `validate`, zero errors found. |
| `1` | One or more validation errors found (validate mode); see `validation_errors[]`. |
| `2` | Source or target schema file not found. |
| `3` | Mapping file not found (validate/augment mode). |
| `4` | Source and target schemas have no overlapping fields; mapping cannot be generated. |
| `10` | Unknown `--mode` value supplied. |

## Related Commands

- `/profile` — Profile the source to obtain richer schema metadata before generating a mapping.
- `/model-logical` — Use an approved mapping as input to logical data modelling.
- `/generate-pipeline` — Use an approved mapping to generate pipeline code.
