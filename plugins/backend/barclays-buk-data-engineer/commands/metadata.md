---
name: metadata
description: Generate metadata and Alation payload drafts from models, mappings and lineage artefacts.
agent: metadata-publisher
user-invocable: true
---

## Purpose

Generate structured metadata payload drafts suitable for publishing to Alation or the Barclays Data Platform (BDP) catalogue. Inputs may include logical or physical data models, source-to-target mappings, a pre-built lineage graph, ownership information, and glossary terms. The command produces draft payloads and a review report; it does not publish directly.

## Usage

```
/metadata --model <path> \
            [--mapping <path>] \
            [--lineage <path>] \
            [--ownership <path>] \
            [--glossary <path>] \
            [--output <path>]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/metadata --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--model` | Required | Path to a logical or physical data model file. Accepted formats: JSON, YAML, ERML, dbt `manifest.json`, or a directory of dbt model YAML files. |
| `--mapping` | Optional | Path to one or more source-to-target mapping files. Multiple files may be comma-separated. Used to enrich column-level lineage annotations in the metadata payload. |
| `--lineage` | Optional | Path to a `lineage-graph.json` file produced by `/lineage-impact`. If supplied, column-level and table-level lineage edges are embedded in the payload. |
| `--ownership` | Optional | Path to an ownership file (JSON or YAML) declaring data owners, stewards and custodians per dataset. Follows the Barclays Data Ownership Schema v2. |
| `--glossary` | Optional | Path to a glossary file (JSON or YAML) mapping business terms to technical column names. Terms are linked in the Alation payload. |
| `--output` | Optional | Directory path for output artefacts. Defaults to `./output/metadata/`. |

## Example Invocations

**1. Generate metadata from a dbt manifest with ownership and glossary:**

```
/metadata \
  --model ./dbt-project/target/manifest.json \
  --ownership ./governance/ownership.yaml \
  --glossary ./governance/glossary.json \
  --output ./output/metadata/
```

**2. Generate metadata enriched with mapping and lineage graph:**

```
/metadata \
  --model ./models/physical-model.yaml \
  --mapping ./mappings/source-to-target.yaml \
  --lineage ./output/lineage/lineage-graph.json \
  --output ./output/metadata/
```

**3. Generate metadata from a logical model only (minimum viable invocation):**

```
/metadata \
  --model ./models/logical-model.json
```

## Output

The command writes the following artefacts to the `--output` directory:

- `alation-payload.json` — Draft Alation bulk-import payload. Must be reviewed and approved before submission to the catalogue.
- `bdp-metadata.yaml` — BDP-compatible metadata YAML for assets not yet in Alation.
- `metadata-review-report.md` — Human-readable summary of generated entries, flagging fields that required inference or could not be populated from the supplied inputs.
- `field-coverage.yaml` — Per-asset breakdown of which metadata fields were populated, inferred, or left blank, with reasons.
- `unknowns.yaml` — Explicit list of fields that could not be determined from the supplied inputs. Inferred values are clearly marked as such in the payloads.
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = complete, `1` = complete with gaps, `2` = failure.

**Loaded standards:** The agent states the Barclays Metadata Standard version and Alation API target version at the top of `alation-payload.json`.

**Exit codes:** `0` success, `1` success with unpopulated required fields, `2` failure.

**Unknowns and assumptions:** Fields that were inferred rather than explicitly supplied are annotated with `inferred: true` in the payload. All gaps are listed in `unknowns.yaml`.

## Related Commands

- `/lineage-impact` — Build a lineage graph to feed into the `--lineage` argument.
- `/model-logical` — Produce a logical data model to feed into the `--model` argument.
- `/model-physical` — Produce a physical data model to feed into the `--model` argument.
