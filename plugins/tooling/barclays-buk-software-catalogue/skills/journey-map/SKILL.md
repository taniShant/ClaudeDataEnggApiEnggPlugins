---
description: Trace a business journey across multiple domains in the Barclays catalog, mapping it to technical services and APIs.
user-invocable: false
owner: Developer AI Tooling <dspedeveloperaitoolingteam@barclays.com>
review-trigger: When the Backstage domain model or cross-domain relationship patterns change.
source: Authored by Developer AI Tooling based on Barclays Backstage catalog domain and API entity conventions.
status: draft
---
# Business Journey Mapper

Trace a business journey (e.g. "international payment", "customer onboarding") across multiple domains in the Barclays catalog, mapping it to the technical services involved.

## Quick Start

Start by listing the domains so you can pick the ones the journey touches (request only the fields you need, because the full entities are very large):

```
mcp__backstage__catalog_query-catalog-entities(
  query: { "kind": "Domain", "spec.type": "domain" },
  fields: ["metadata.name", "metadata.title", "metadata.description"],
  limit: 50
)
```

Then walk each relevant domain down to its subdomains and capabilities, and list the domain's APIs (steps below).

## When to use

Load when the user describes a business process or journey and wants to know:
- Which domains and capabilities are involved
- Which APIs they need to integrate with
- How services interact across domain boundaries
- What team owns each part of the flow

## Steps

1. **Identify candidate domains** from the user's description
   - If unclear, list all domains and ask the user to select
   - Query: `mcp__backstage__catalog_query-catalog-entities(query: { "kind": "Domain", "spec.type": "domain" }, fields: ["metadata.name", "metadata.title", "metadata.description"], limit: 50)`

2. **For each relevant domain**, discover subdomains and capabilities:
   - Subdomains: filter by `spec.subdomainOf=[domain-name]` (the bare name, such as `dom.credit-card`)
   - Capabilities: fetch each subdomain entity and extract `relations.hasPart`

3. **For each relevant domain**, find its APIs. APIs attach to the domain's system, not to a capability:
   - Fetch the domain entity and take its `hasPart` relation that starts with `system:`
   - `mcp__backstage__catalog-mcp_get_entities_with_custom_query(filter: "kind=Api,spec.system=buk/[system-name]", fields: "metadata.name,metadata.title,spec.type")`
   - Present the APIs against the domain and say they are not capability-specific

4. **Synthesize the journey**:
   - Show the sequence: Domain A → capability → API → Domain B → capability → API
   - Flag cross-domain calls and ordering constraints
   - Report any gaps honestly

## Output format

```
## Journey: [user's description]

### Domains involved
- **[Domain A]** — [brief role in journey]
- **[Domain B]** — [brief role in journey]

### Service flow
1. [Capability in Domain A]
2. [Capability in Domain B]
...

### APIs by domain (not capability-specific)
- **[Domain A]** (system `[system-name]`): `[api-name]`, `[api-name]`

### Cross-domain notes
- [Any ordering constraints or integration requirements]

### Gaps
- [Capabilities or APIs not found in catalog]
```

Always cite which catalog query returned each capability or API.

## Agent Self-Check

- [ ] Did I query the catalog to identify domains before mapping the journey?
- [ ] Did I cover all domains relevant to the user's described journey?
- [ ] Did I cite which MCP query returned each capability and API, and avoid tying an API to a specific capability?
- [ ] Did I include a Gaps section even if empty?
- [ ] Did I avoid inventing steps in the journey not supported by catalog results?
