---
description: List all APIs available in a domain, subdomain, or for a specific capability in the Barclays catalog.
user-invocable: false
owner: Developer AI Tooling <dspedeveloperaitoolingteam@barclays.com>
review-trigger: When Backstage API entity structure, spec types, or catalog query patterns change.
source: Authored by Developer AI Tooling based on Barclays Backstage catalog API entity conventions.
status: draft
---
# API Inventory

List all APIs available in a domain, subdomain, or for a specific capability.

## Quick Start

APIs belong to a **domain's system**, not to a capability. For example, `dom.partner-integration` has the system `partner-integration-trans-cell`:

```
mcp__backstage__catalog-mcp_get_entities_with_custom_query(
  filter: "kind=Api,spec.system=buk/partner-integration-trans-cell",
  fields: "metadata.name,metadata.title,spec.type,spec.owner"
)
```

Results are capped at 200. If `count` is 200, the list may be truncated, so say so.

## When to use

Load when the user wants to:
- Find APIs they can integrate with for a business function
- See what services a domain exposes
- Find OpenAPI/AsyncAPI/gRPC/GraphQL specs

The catalog does not link APIs to subdomains or capabilities. If the user asks for the APIs of a capability, say that APIs are registered against the parent domain's system and list the domain's APIs, noting that they are not capability-specific.

## Steps

### For a domain-level inventory

1. Fetch the domain entity: `mcp__backstage__catalog_get-catalog-entity(kind: "Domain", name: "dom.[name]")`
2. In its `relations`, find the `hasPart` entry whose `targetRef` starts with `system:` (for example `system:buk/partner-integration-trans-cell`). If there is none, report that the domain has no system registered.
3. Query the APIs for that system:
   ```
   mcp__backstage__catalog-mcp_get_entities_with_custom_query(
     filter: "kind=Api,spec.system=buk/[system-name]",
     fields: "metadata.name,metadata.title,spec.type,spec.owner"
   )
   ```
4. To describe the domain's structure alongside the APIs, list its subdomains and capabilities (see the navigate skill — Phases 2 and 3).

### For a quick broad search

```
mcp__backstage__search_query(term: "[user's search term]", types: ["software-catalog"])
```
Filter the hits to `document.kind` of `API`.

### To fetch API spec location

1. Query the API entity: `mcp__backstage__catalog_get-catalog-entity(kind: "Api", name: "[api-name]")`
2. Check `spec.type` (openapi, asyncapi, graphql, grpc)
3. Check `metadata.links` for repository or spec URL

## Output format

For each API found:
```
**[API title]** (`[entity-name]`)
Type: [openapi | asyncapi | grpc | graphql]
Owner: [team, from the ownedBy relation]
System: [spec.system]
Spec: [link if available, else "not linked in catalog"]
```

Group by domain, and state which system the APIs were found under.
Report a domain whose system has no APIs, or that has no system, as a catalog gap.

## Agent Self-Check

- [ ] Did I find the domain's system through its `hasPart` relation before listing APIs?
- [ ] Did I cite which MCP query returned each API?
- [ ] Did I include `spec.type` for every API listed?
- [ ] Did I include a spec link or explicitly state "not linked in catalog"?
- [ ] Did I flag domains with no system or no APIs as catalog gaps, and say when a result was capped at 200?
