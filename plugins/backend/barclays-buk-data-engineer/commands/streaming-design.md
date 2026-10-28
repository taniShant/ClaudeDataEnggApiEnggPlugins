---
name: streaming-design
description: Assess batch vs streaming fit and produce a streaming architecture design if justified.
agent: streaming-design-adviser
user-invocable: true
---

## Purpose

Evaluate whether a use case warrants a streaming architecture over batch processing, using evidence from supplied latency, volume, and ordering requirements. If streaming is justified, produce a recommended streaming architecture design referencing only approved platforms. If batch is more appropriate, the output states that conclusion with supporting reasoning.

## Usage

```
/streaming-design --requirements <path> \
                     --approved-platforms <platform,...> \
                    [--existing-infra <description>] \
                    [--output <path>]
```

Pass `--help` to receive this document along with the full input and output JSON schemas and worked examples:

```
/streaming-design --help
```

## Arguments

| Name | Required / Optional | Description |
|---|---|---|
| `--requirements` | Required | Path to a requirements file describing latency targets, expected data volumes, ordering and exactly-once semantics needs, consumer SLAs and any other relevant constraints. Accepted formats: JSON, YAML, Markdown. |
| `--approved-platforms` | Required | Comma-separated list of streaming platforms approved for use in this context (e.g. `kafka,flink`, `confluent-cloud`, `kinesis,lambda`). Only platforms in this list will appear in the design output. |
| `--existing-infra` | Optional | Free-text or structured description of the current infrastructure landscape (batch schedulers, databases, message brokers, cloud provider, network topology). Used to assess integration complexity and reuse opportunities. |
| `--output` | Optional | Directory or file path for output artefacts. Defaults to `./output/streaming-design/`. |

## Example Invocations

**1. Assess fit and design for a real-time fraud detection use case:**

```
/streaming-design \
  --requirements ./requirements/fraud-detection-reqs.yaml \
  --approved-platforms kafka,flink \
  --existing-infra "On-prem Kafka 3.4 cluster, Oracle batch ETL, AWS VPC" \
  --output ./output/streaming-design/
```

**2. Assess fit for a reporting pipeline with relaxed latency requirements:**

```
/streaming-design \
  --requirements ./requirements/reporting-pipeline-reqs.json \
  --approved-platforms kafka,confluent-cloud \
  --output ./output/streaming-design/
```

**3. Design only, where streaming is already decided, using Kinesis:**

```
/streaming-design \
  --requirements ./requirements/iot-telemetry-reqs.yaml \
  --approved-platforms kinesis,lambda \
  --existing-infra "AWS-native stack, no on-prem dependencies"
```

## Output

The command writes the following artefacts to the `--output` directory:

- `fit-assessment.yaml` — Structured batch vs streaming fit assessment. Includes decision (`batch_recommended`, `streaming_recommended`, `hybrid_recommended`), scoring against each requirement dimension, and a written rationale.
- `streaming-architecture.yaml` — Present only when streaming or hybrid is recommended. Describes: recommended topology (source, processor, sink), platform choices with justification, partitioning and ordering strategy, consumer group design, fault tolerance and replay approach, and estimated throughput capacity.
- `architecture-diagram.md` — Mermaid diagram source for the recommended architecture. Renderable in GitLab, GitHub, and Confluence.
- `platform-comparison.yaml` — Comparative assessment of all supplied approved platforms against the requirements. Absent if only one platform is supplied.
- `unknowns.yaml` — Requirements dimensions that were ambiguous or absent from the input, and the assumptions made in their place. The agent will not design for unstated requirements without flagging them.
- `status.json` — Machine-readable exit status. Field `exit_code`: `0` = complete, `1` = complete with assumptions, `2` = failure.

**Loaded standards:** The agent states the Barclays Streaming Architecture Standard version and the approved platform list version at the top of `fit-assessment.yaml`.

**Exit codes:** `0` success, `1` success with stated assumptions, `2` failure.

**Unknowns and assumptions:** Any requirement dimension not covered by the input file is listed explicitly in `unknowns.yaml` before the design proceeds.

## Related Commands

- `/tech-choice` — Broader platform selection analysis, not limited to streaming technologies.
- `/generate-pipeline` — Generate pipeline code implementing the streaming design produced here.
- `/performance` — Analyse performance of an existing streaming or batch pipeline.
