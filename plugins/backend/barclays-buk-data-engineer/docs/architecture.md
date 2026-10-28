# Architecture

## Plugin Architecture Diagram

```
.claude-plugin/
  plugin.json                  <- Plugin manifest: metadata, version, extension points, dependencies
       |
       +-- agents/             <- 20 specialist agents + 1 front-door routing agent
       |      Each agent: agent.md (system prompt), input/output schema refs, skill refs
       |
       +-- commands/           <- 22 independently invocable slash commands
       |      Each command maps 1:1 to an agent or a composed workflow
       |
       +-- skills/             <- 15 shared skill definitions (engineering + worker-behaviour)
       |      Reusable instruction modules composed into agents
       |
       +-- schemas/            <- 14 JSON schemas for input/output contracts
       |      input-manifest.schema.json, run-manifest-schema.json, result-manifest.schema.json,
       |      and task-specific schemas
       |
       +-- hooks/              <- 5 deterministic safety hooks
              block-destructive-sql.md       (pre-tool-call, Bash)
              block-secret-output.md         (pre-write, Write/Edit)
              block-unsafe-publish.md        (before_publish, Marquez publication)
              validate-result-manifest.md    (post-agent, all agents)
              validate-standards-provenance.md (post-agent, all agents)
```

## Design Principles

1. **Separation of concerns.** Each agent has a single primary responsibility. Agents do not overlap in scope.
2. **Contract-first.** Every agent interaction is governed by a JSON schema. No agent produces unstructured output for downstream programmatic consumption.
3. **Standards by dependency, never by copy.** Standards definitions live in `barclays-buk-standards`. This plugin depends on that plugin; it does not duplicate or embed standards content.
4. **Deterministic safety outside the model.** Safety controls (destructive SQL blocking, secret detection) are implemented as hooks that run deterministically, not as prompt instructions that the model could reason around.
5. **Human accountability at every action boundary.** No action that modifies a production system, creates a ticket, raises a PR, or submits a change is taken without explicit human confirmation. The agent prepares; the human acts.
6. **Evidence over assertion.** Every compliance or quality claim must be backed by an evidence entry in the evidence ledger. Unsupported claims are flagged, not silently passed.
7. **Additive extension, never forking.** The plugin exposes registered extension points. Platform plugins and domain extensions add capability through those points. The base plugin is never forked.

## Dependency Model

```
barclays-buk-standards          <- Standards definitions (security, data, governance, architecture)
        |
        v
barclays-buk-data-engineer      <- This plugin (base data engineering AI worker)
        |
        +-----> barclays-buk-aws-data-platform     (platform plugin, depends on this)
        +-----> barclays-buk-databricks-platform   (platform plugin, depends on this)
        +-----> barclays-buk-streaming-platform    (platform plugin, depends on this)
        |
        +-----> [domain extensions]                (e.g. barclays-buk-cdao-data-products)
```

This plugin must never take a dependency on any domain extension or platform plugin. Dependency direction is strictly downward.

## Extension Points

| Extension Point | Description |
|---|---|
| `agent` | Register a new specialist agent that participates in the front-door routing table |
| `command` | Register a new slash command, mapped to an agent or workflow |
| `skill` | Register a new reusable skill module that agents can compose |
| `schema` | Register additional JSON schemas for task-specific input/output contracts |
| `hook` | Register additional pre- or post-hooks for tool calls or agent lifecycle events |
| `standard` | Reference an additional standard from a standards plugin dependency |
| `source` | Register an additional source in the source register (MCP server or static reference) |
| `evidence-rule` | Register a domain-specific evidence classification rule |
| `prompt-override` | Override a specific named prompt section within a defined scope and compatibility range |
| `tads-stage` | Register an additional or modified TADS workflow stage for domain-specific delivery processes |

## Agent Interaction Model

The `data-engineer` front-door agent acts as the routing entry point. It:

- Accepts a natural language or structured request
- Determines the appropriate specialist agent(s)
- Routes to the specialist and returns its result

Each specialist agent is independently invocable via its corresponding slash command. There is no mandatory sequencing between agents. Agents do not call each other at runtime; composition is expressed at the command level if multi-agent workflows are needed.

```
User / Caller
     |
     v
data-engineer-worker (front-door)
     |
     +-- requirement-assessor
     +-- context-resolver
     +-- source-profiler
     +-- mapping-assistant
     +-- logical-data-modeller
     +-- physical-data-modeller
     +-- technology-option-adviser
     +-- pipeline-generator
     +-- data-quality-engineer
     +-- database-change-adviser
     +-- migration-planner
     +-- lineage-impact-analyst
     +-- metadata-publisher
     +-- performance-engineer
     +-- streaming-design-adviser
     +-- pii-discovery-adviser
     +-- merge-request-adviser
     +-- validation-and-handoff-agent
     +-- ab-initio-discovery-agent
```

## Standards Enforcement

- Standards are loaded from the `barclays-buk-standards` dependency. They are never copied into this plugin.
- The precedence hierarchy for conflicting standards claims is: domain extension > platform plugin > this plugin > barclays-buk-standards.
- Staleness is surfaced via the `validate-standards-provenance` post-agent hook. Overdue standards generate warnings; placeholder or missing standards prevent a `PASS` status.
- Standards provenance fields (`standard_id`, `version`, `owner`, `review_status`, `source_url`) are mandatory on every `standards_applied[]` entry.

## Safety Model

- **Destructive SQL:** The `block-destructive-sql` pre-tool-call hook intercepts any Bash call containing DROP, TRUNCATE, DELETE without WHERE, or CASCADE DDL. Always blocked in staging/prod; warned in dev/test.
- **Secret detection:** The `block-secret-output` pre-write hook intercepts any Write or Edit call containing credential patterns. Always blocked. Secret values are never logged.
- **Human accountability:** No production mutation is initiated by the agent. All DDL, pipeline deployments, ticket creation, and PR submissions require explicit human action after agent preparation.
- **No production write identity:** The agent identity used for schema introspection and profiling must be read-only. Write identity is never provided to the agent.

## Evidence Model

Evidence entries in the evidence ledger carry one of seven states (defined authoritatively in the `evidence-and-uncertainty` skill):

| State | Meaning |
|---|---|
| `VERIFIED_STANDARD` | Directly stated in a loaded, approved, non-stale standard. Version and section cited. |
| `VERIFIED_SOURCE` | Directly observed from an authorised, accessible data source or schema at runtime. |
| `RUNTIME_OBSERVATION` | Observed at runtime (e.g. row count, profile statistic) but not from a canonical reference. |
| `USER_SUPPLIED` | Provided explicitly by the user in the current session. Not independently verified. |
| `INFERRED_CANDIDATE` | Inferred by the worker from available context using documented reasoning. Requires human confirmation. |
| `ASSUMPTION` | Held in the absence of evidence. Explicitly stated; must be validated before production use. |
| `UNKNOWN` | No evidence available; recorded in the unknowns register with resolution path. |

The evidence ledger accumulates across agent invocations within a session. The unknowns register records all gaps that could not be resolved. The source register lists the mandatory Barclays internal sources (LCT, BDP, Alation, Data Marketplace, Policy Hub, BUK Data Products, and TADS/LCP Confluence pages) that agents must consult before generating output.

## TADS Compliance

Agents that produce delivery artefacts follow the 8-stage TADS V2.0 workflow:

1. **Understand** - Capture requirements, constraints, and context
2. **Assess** - Evaluate existing state against standards
3. **Design** - Produce design artefacts (schemas, pipeline topology, test plan)
4. **Review** - Apply quality and security assessment; surface findings
5. **Decide** - Record technology decisions with rationale (platform-neutral method)
6. **Implement** - Generate code, configuration, and DDL artefacts
7. **Validate** - Run test generation; record quality gate results
8. **Handoff** - Produce result manifest, evidence ledger, LCT artefacts, and human accountability summary

LCT (Lifecycle Tracking) integration is mandatory for stages 5-8. Artefact tracking entries are included in the result manifest `lct_artefacts[]` array.
