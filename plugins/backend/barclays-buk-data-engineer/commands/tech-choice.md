---
name: tech-choice
description: Produce a neutral technology comparison ADR from approved candidates.
agent: technology-option-adviser
user-invocable: true
---

## Purpose

Produce a neutral, evidence-based technology comparison Architecture Decision Record (ADR) from a set of approved platform candidates. All scoring is driven by supplied workload characteristics and criteria weights; any scoring done without a weights file is marked PROPOSED in the output and must not be used as the sole basis for a platform decision.

## Usage

```
/tech-choice --candidates <platform-names> --workload <path> [--weights <path>] [--constraints <path|inline>] [--output <path>] [--help]
```

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--candidates` | Required | Comma-separated list of platform names to compare (e.g., `snowflake,bigquery,databricks`). Each candidate must appear in the approved platform catalogue; unknown platforms are flagged. |
| `--workload` | Required | Path to a workload description file specifying query patterns, data volumes, concurrency, latency SLAs, and integration requirements. |
| `--weights` | Optional | Path to a criteria weights file mapping evaluation dimensions (cost, performance, operability, security, vendor lock-in, etc.) to numeric weights. If omitted, equal weights are applied and the entire ADR is marked PROPOSED. |
| `--constraints` | Optional | Path to a constraints file or an inline JSON/YAML string describing hard constraints (e.g., data residency region, approved cloud provider, max cost threshold). |
| `--output` | Optional | Directory path to write ADR artefacts. Defaults to `./output/tech-choice/`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Compare three platforms with a workload and no weights (equal weighting, PROPOSED):**
```
/tech-choice --candidates "snowflake,bigquery,databricks" --workload ./workloads/cdp-batch.yaml --output ./output/tech-choice/initial/
```

**2. Compare platforms with explicit criteria weights:**
```
/tech-choice --candidates "snowflake,databricks" --workload ./workloads/cdp-batch.yaml --weights ./criteria/weights-v2.json --output ./output/tech-choice/weighted/
```

**3. Compare with weights and hard constraints (data residency, approved provider):**
```
/tech-choice --candidates "snowflake,bigquery,synapse" --workload ./workloads/real-time-ingest.yaml --weights ./criteria/weights-v2.json --constraints ./constraints/eu-residency.yaml --output ./output/tech-choice/constrained/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `adr.json` — The structured ADR containing:
  - `candidates[]` — Each platform with per-dimension scores, evidence citations, and catalogue status (`approved|unapproved|unknown`).
  - `scoring_method` — Weighted or equal, with weights applied.
  - `recommendation` — Highest-scoring approved candidate. Marked PROPOSED if weights were not supplied.
  - `constraints_applied[]` — Hard constraints and whether each candidate satisfies them.
  - `eliminated_candidates[]` — Candidates removed due to constraint violations, with reasons.
  - `loaded_standards[]` — Platform catalogue version and evaluation framework version consulted.
  - `unverified_assumptions[]` — Capability claims that could not be verified against the current platform catalogue.
- `adr.md` — Human-readable ADR document formatted for architecture review, with decision table and recommendation narrative.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | ADR produced successfully. |
| `1` | Workload file not found. |
| `2` | One or more candidates not found in approved platform catalogue; flagged in output. |
| `3` | Constraints file not found (when `--constraints` path supplied). |
| `4` | All candidates eliminated by hard constraints; ADR produced with empty recommendation. |
| `10` | Weights file not found; equal weights applied and ADR marked PROPOSED. |

## Related Commands

- `/model-physical` — Proceed to physical modelling once a platform is selected from this ADR.
- `/generate-pipeline` — Generate pipeline code targeting the chosen platform.
- `/streaming-design` — Design a streaming architecture using the chosen platform.
