---
description: Navigate the Barclays Backstage Software Catalogue to discover domains, capabilities, APIs, and service owners.
user-invocable: false
owner: Developer AI Tooling <dspedeveloperaitoolingteam@barclays.com>
review-trigger: When the Backstage catalog domain model, entity kinds, or MCP tool signatures change.
source: Authored by Developer AI Tooling based on the Barclays Backstage catalog API and domain model conventions.
status: draft
---
# Barclays Software Catalogue Navigator

Query and navigate the Barclays Backstage catalog to discover services, components, APIs, and domain hierarchies.

## Quick Start

To explore the catalog from the top, list the business domains (use `fields` and `limit`, because the full entities are very large):

```
mcp__backstage__catalog_query-catalog-entities(
  query: { "kind": "Domain", "spec.type": "domain" },
  fields: ["metadata.name", "metadata.title", "spec.owner"],
  limit: 50
)
```

To search for something by keyword instead:

```
mcp__backstage__search_query(term: "[search term]", types: ["software-catalog"])
```

## When to use this skill

Load this skill whenever the user wants to:
- Find services, components, or APIs related to a business function
- Understand domain ownership or team responsibilities
- Map a business journey to technical services
- Discover what capabilities exist in a given domain
- Look up service owners, ServiceFirst CMDB entries, or container names

## Environment

This plugin connects to two Backstage environments. Check the plugin's `environment` config:
- **production** (default) — MCP tools are prefixed `mcp__backstage__*`
- **non-production** — MCP tools are prefixed `mcp__backstage-np__*` (requires OAuth; run `/barclays-buk-software-catalogue:connect` if not yet authenticated)

In all examples below, substitute `mcp__backstage__` with `mcp__backstage-np__` when querying non-production.

## Custom entity kinds

The Barclays catalog contains a Backstage entity kind that is not part of standard Backstage and is unknown to Claude without explicit guidance:

- **`ArchitectureGuidance`** — architecture patterns (principles and exemplars are planned). It exists in the **non-production** catalog only.

ADRs are not catalog entities. They are indexed by the Backstage ADR plugin and found with `search_query` and `types: ["adr"]`. There is no `ArchitectureDecision` kind.

When a user asks about architecture patterns or ADRs, load the `barclays-buk-software-catalogue:architecture-guidance` skill before querying.

## MCP tools available

This skill uses the Backstage catalog MCP tools:
- `mcp__backstage__catalog-mcp_get_all_entities_by_kind_and_type` — filter by kind + type
- `mcp__backstage__catalog_query-catalog-entities` — complex predicate queries
- `mcp__backstage__catalog_get-catalog-entity` — fetch a specific entity by name/kind
- `mcp__backstage__catalog-mcp_get_entities_with_custom_query` — flexible custom filtering
- `mcp__backstage__catalog-mcp_get_entity_types_for_kind` — discover available types
- `mcp__backstage__catalog-mcp_get_entities_by_owner` — query by owner reference
- `mcp__backstage__search_query` — full-text search across all catalog document types

## Core principles

1. **Always query first** — never assume or infer that an entity exists; verify via catalog query
2. **Follow the hierarchy** — traverse BUK root → Domain → Subdomain → Capability; reach APIs through the domain's system (capabilities have no direct API link)
3. **Report gaps honestly** — if a query returns no results, say so; do not invent alternatives
4. **Show your work** — cite which query returned each result
5. **Enrich responses** — resolve owners to teams, parse ServiceFirst annotations, show container context

## Domain model

```
dom.buk (kind: Domain, spec.type: Domain)                  ← single top-level root
  └── dom.<name> (kind: Domain, spec.type: Domain)         ← business domain, spec.subdomainOf: dom.buk
        ├── sub.<code>.<name> (spec.type: Subdomain)       ← spec.subdomainOf: dom.<name>
        │     └── cap.<code>.<name> (spec.type: Capability) ← spec.subdomainOf: sub.<code>.<name>
        └── <name>-trans-cell (kind: System)               ← hasPart of the domain
              └── API (kind: API, spec.system: buk/<name>-trans-cell)
```

Real example:

```
dom.partner-integration
  ├── sub.pi.commercial-partner-product-integration
  │     └── cap.pi.third-party-commercial-products-provisioning
  └── system:buk/partner-integration-trans-cell  →  APIs with spec.system = buk/partner-integration-trans-cell
```

**Critical points:**
- Parents link to children with `relations.hasPart` (`targetRef` like `domain:buk/sub.pi.…`); children link back with `partOf`. Never infer the hierarchy from `spec.owner`.
- `spec.subdomainOf` holds the **bare** parent name (`dom.credit-card`), not a `domain:buk/…` reference. Filtering with `domain:buk/…` returns nothing.
- Capabilities have **no** link to APIs. APIs are attached to a domain's system (`spec.system`), so an API list is per domain, not per capability.
- `spec.type` is stored capitalised (`Domain`, `Subdomain`, `Capability`) but filters are case-insensitive.
- Filter queries return at most 200 entities. If `count` is 200, the result may be truncated: narrow the filter or use `catalog_query-catalog-entities` with `limit` and `cursor`.

## Entity reference format

```
kind:namespace/name
```

Examples:
- `domain:buk/dom.buk`
- `domain:buk/dom.partner-integration`
- `domain:buk/sub.pi.commercial-partner-product-integration`
- `domain:buk/cap.pi.third-party-commercial-products-provisioning`
- `system:buk/partner-integration-trans-cell`
- `api:buk/drm-xapi-v3.0`
- `group:buk/digital`

## Query strategy

### Phase 1 — Domain discovery
```
mcp__backstage__catalog_query-catalog-entities(
  query: { "kind": "Domain", "spec.type": "domain" },
  fields: ["metadata.name", "metadata.title", "spec.owner"],
  limit: 50
)
```
The result includes the root `dom.buk` itself. Alternatively fetch `dom.buk` and read its `hasPart` relations.

### Phase 2 — Subdomain discovery
```
mcp__backstage__catalog-mcp_get_entities_with_custom_query(
  filter: "kind=Domain,spec.type=subdomain,spec.subdomainOf=[domain-name]",
  fields: "metadata.name,metadata.title"
)
```
For example `spec.subdomainOf=dom.credit-card`. Use the bare name, with no `domain:buk/` prefix.

### Phase 3 — Capability mapping
Fetch the subdomain entity (`mcp__backstage__catalog_get-catalog-entity(kind: "Domain", name: "sub.…")`) and inspect
`relations` for entries with `type: hasPart`. Each `targetRef` is a capability.

### Phase 4 — API location
Fetch the **domain** entity and find its `hasPart` relation whose `targetRef` starts with `system:` (for example `system:buk/partner-integration-trans-cell`). Then:
```
mcp__backstage__catalog-mcp_get_entities_with_custom_query(
  filter: "kind=Api,spec.system=buk/[system-name]",
  fields: "metadata.name,metadata.title,spec.type,spec.owner"
)
```
APIs cannot be listed for a single capability or subdomain. Say so, and list the domain's APIs instead.

## Enrichment

### Owner resolution
1. Take the owner from the entity's `relations` entry of type `ownedBy` (for example `group:buk/digital`). `spec.owner` can be a bare name (`digital`) or a `default/…` value, so prefer the relation.
2. Fetch the group with the namespace from the reference: `mcp__backstage__catalog_get-catalog-entity(kind: "Group", name: "digital", namespace: "buk")`
3. Display `spec.profile.displayName` (for example "Digital Channels"), `metadata.description`, and `spec.profile.email` if present (many groups have no email). The group's `ownerOf` relations can be very long, so do not list them unless asked.

### ServiceFirst annotations
When `metadata.annotations` contains `servicefirst/*` keys:
- Show: name, correlationID, sysID, businessOwner, operationalStatus
- Construct ServiceNow links for ITAS/ITTS/ITBA/ITSO object types using sysID

### Container context
- `metadata.name` — Kubernetes container name
- `metadata.title` — human-friendly display name

## Response format

Structure all responses with:
1. **Domain breakdown** — which domains/subdomains are involved
2. **Capabilities found** — only from actual catalog results
3. **APIs and services** — specific services available
4. **Gaps and notes** — missing capabilities or caveats (honest reporting)

## Error handling

- **Entity not found** — suggest alternative queries or clarify terminology
- **Ambiguous match** — present all matches, ask user to narrow down
- **No APIs found** — the domain's system has no APIs registered, or the user asked for APIs by capability (not supported: explain that APIs attach to the domain's system)
- **No capabilities** — report gap honestly, do not invent alternatives

## Agent Self-Check

- [ ] Did I query the catalog before stating any entity exists?
- [ ] Did I follow the Domain → Subdomain → Capability hierarchy, and reach APIs through the domain's system rather than a capability?
- [ ] Did I cite which MCP query returned each result?
- [ ] Did I resolve `spec.owner` to a human-readable team name where available?
- [ ] Did I report all catalog gaps honestly rather than suggesting unverified alternatives?
