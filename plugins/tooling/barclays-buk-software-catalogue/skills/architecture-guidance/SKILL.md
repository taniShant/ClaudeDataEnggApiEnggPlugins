---
description: Query Barclays architecture patterns (ArchitectureGuidance entities, non-production catalog only) and ADRs (via the Backstage ADR plugin search).
user-invocable: false
owner: Developer AI Tooling <dspedeveloperaitoolingteam@barclays.com>
review-trigger: When the ArchitectureGuidance entity schema changes, when ArchitectureGuidance is promoted to production, or when the ADR plugin indexing changes.
source: Authored by Developer AI Tooling based on the Barclays ArchitectureGuidance entity proposal (backstage-architectureguidance-proposal.md) and the behaviour of the Backstage ADR plugin search index.
status: draft
---
# Architecture Guidance & Decisions

Find Barclays architecture patterns and Architecture Decision Records (ADRs) in Backstage. Patterns are `ArchitectureGuidance` entities, a custom Barclays kind that currently exists in the **non-production** catalog only. ADRs are not catalog entities: they are indexed by the Backstage ADR plugin and found through search.

## Quick Start

ADRs (indexed by the Backstage ADR plugin, so use search, not an entity query):

```
mcp__backstage__search_query(term: "[topic]", types: ["adr"], pageLimit: 5)
```

Architecture patterns (`ArchitectureGuidance` exists in non-production only, so use the `backstage-np` server):

```
mcp__backstage-np__catalog-mcp_get_all_entities_by_kind_and_type(kind: "ArchitectureGuidance", type: "pattern")
```

## When to use this skill

Load this skill when the user wants to:
- Find architectural patterns (non-production catalog only)
- Look up Architecture Decision Records (ADRs)
- Understand the rationale behind a technical decision
- Find the status, date or owning system of a decision

## Where each source lives

| Source | How it is stored | Where it is available | How to query |
|--------|------------------|-----------------------|--------------|
| Architecture patterns | `ArchitectureGuidance` catalog entities | Non-production only | `mcp__backstage-np__*` catalog tools |
| ADRs | Backstage ADR plugin (indexed from ADR markdown in system repos) | Search index | `search_query` with `types: ["adr"]` |

There is **no** `ArchitectureDecision` entity kind. Do not query for it. If a pattern query returns nothing on the production server, that is expected: report that patterns are non-production only rather than treating it as a failure.

---

## ArchitectureGuidance (non-production only)

`ArchitectureGuidance` is a Barclays-specific Backstage entity kind — **not** a standard Backstage kind. It currently exists in the **non-production** catalog only (production returns no entities of this kind). The non-production catalog contains patterns only; principles and exemplars are planned but not yet populated.

### Three subtypes (spec.type)

| Type | Meaning | Current status |
|------|---------|----------------|
| `pattern` | Reusable solution to a recurring problem ("the how") | Populated — query these |
| `principle` | Abstract rule that informs decision-making ("the why") | Not yet populated |
| `exemplar` | Production-grade reference implementation ("the show") | Not yet populated |

### Real entity structure (from catalog data)

All current entities follow this shape:

```yaml
apiVersion: backstage.io/v1alpha1
kind: ArchitectureGuidance
metadata:
  name: string              # kebab-case, e.g. "app-to-gateway"
  namespace: buk            # always "buk" for BUK patterns
  title: string             # e.g. "App to Gateway - Integration Pattern"
  description: string       # short summary
  labels:
    domain: string          # pattern group: "common" | "integration" | "session-management"
                            #                "implementation-control" | "sequence-validation"
    layer: string           # e.g. "service" | "api"
    severity: string        # e.g. "medium" | "high" | "critical" | "low"
  tags: string[]            # e.g. ["integration", "api", "buk", "pattern"]
  links:
    - title: "Source Confluence Page"
      url: string           # link to originating Confluence page
      type: documentation
  annotations:
    backstage.io/techdocs-ref: dir:.   # TechDocs rendered from docs/index.md alongside the YAML
spec:
  type: pattern             # currently always "pattern"
  lifecycle: recommended    # currently always "recommended"
  owner: group:buk/cto      # currently always the BUK CTO group
  relatedPrinciples: []     # empty — not yet linked
  implementedBy: []         # empty — not yet linked
  alternatives: []          # empty — not yet linked
```

### Pattern domain groups (metadata.labels.domain)

These are the actual domain values present in the catalog — they are **not** Backstage Domain entity names, they are label values used for grouping:

| Domain label | What it covers |
|-------------|---------------|
| `common` | Cross-cutting patterns: caching, logging, image handling, messaging, upload, tagging |
| `integration` | App-to-backend patterns: gateway, API, web, 3rd-party, session sharing, universal links |
| `session-management` | Session caching and secure data manipulation patterns |
| `implementation-control` | Configuration, feature switches, access control patterns |
| `sequence-validation` | Journey framework and custom validation check patterns |

### TechDocs content

Every pattern has a `docs/index.md` rendered via TechDocs. The `mkdocs.yml` defines the navigation. Content includes: Intent, When This Pattern Applies, Problem Statement, Solution, Principles/Rules, Architecture diagrams (Mermaid), Consequences, Known Uses, Anti-Patterns, Ownership/Lifecycle, and References. Always mention the TechDocs link when a user wants to read the full pattern detail.

### Relationship fields (currently empty, planned for future)

| Spec field | Direction |
|-----------|-----------|
| `spec.relatedPrinciples` | Pattern → Principle |
| `spec.implementedBy` | Pattern → Exemplar |
| `spec.alternatives` | Pattern ↔ Pattern |

---

## Architecture decisions (ADRs)

ADRs are written as markdown in each system's repository and indexed by the Backstage **ADR plugin**. They are found with `search_query` and the `adr` document type. They are not catalog entities, so catalog queries by kind will not find them.

Each search hit carries these fields in `document`:

| Field | Meaning |
|-------|---------|
| `title` | ADR title |
| `text` | Full ADR markdown (long: summarise it, do not paste it) |
| `status` | Decision status as written in the ADR, for example `approved` |
| `date` | Decision date |
| `entityRef` / `entityTitle` | The system the ADR belongs to, for example `system:buk/dev-portal` |
| `location` | Catalog-relative path to the ADR, for example `/catalog/buk/system/dev-portal/adrs?record=0005-replatform.md` |

Status values are whatever each ADR records. Do not assume a fixed lifecycle or casing.

---

## Query strategy

### Find all patterns (non-production only)
```
mcp__backstage-np__catalog-mcp_get_all_entities_by_kind_and_type(kind: "ArchitectureGuidance", type: "pattern")
```

### Find patterns in a specific domain group (non-production only)
```
mcp__backstage-np__catalog-mcp_get_entities_with_custom_query(
  filter: "kind=ArchitectureGuidance,spec.type=pattern,metadata.labels.domain=integration"
)
```
Valid domain values: `common`, `integration`, `session-management`, `implementation-control`, `sequence-validation`

### Find all recommended guidance (non-production only)
```
mcp__backstage-np__catalog-mcp_get_entities_with_custom_query(
  filter: "kind=ArchitectureGuidance,spec.lifecycle=recommended"
)
```

### Search for ADRs
```
mcp__backstage__search_query(term: "[user's search term]", types: ["adr"], pageLimit: 5)
```
Use `pageCursor` from the response to fetch more results. To see which system an ADR belongs to, read `document.entityRef`; to see the owning system's other details, fetch it with `mcp__backstage__catalog_get-catalog-entity`.

### Search patterns by keyword (non-production only)
```
mcp__backstage-np__search_query(term: "[user's search term]", types: ["software-catalog"])
```

---

## Response format

### For ArchitectureGuidance pattern results

```
**[Title]** (`archguidance:buk/<name>`)
Type: pattern | Lifecycle: [recommended | deprecated]
Domain group: [domain label] | Layer: [layer] | Severity: [severity]
Owner: [resolved group name]
Source: [Confluence link from metadata.links]
TechDocs: available — full pattern detail including diagrams, rules, and known uses
Tags: [metadata.tags]
```

### For ADR results

```
**[title]** — [one-line summary of the decision outcome]
Status: [status] | Date: [date]
System: [entityTitle] (`[entityRef]`)
Location: [location]
```

Summarise the Context and Decision Outcome in a few lines. Do not reproduce the whole `text` field.

---

## Agent Self-Check

- [ ] Did I use the non-production server (`mcp__backstage-np__*`) for `ArchitectureGuidance` queries?
- [ ] Did I tell the user that patterns are non-production only when production returned nothing?
- [ ] Did I use a valid `metadata.labels.domain` value (`common`, `integration`, `session-management`, `implementation-control`, `sequence-validation`) when filtering by domain?
- [ ] Did I mention TechDocs availability when a user asks for pattern detail?
- [ ] Did I search ADRs with `search_query` and `types: ["adr"]` rather than querying a non-existent `ArchitectureDecision` kind?
