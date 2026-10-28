---
description: Discover business domains and their ownership in the Barclays Backstage catalog.
user-invocable: false
owner: Developer AI Tooling <dspedeveloperaitoolingteam@barclays.com>
review-trigger: When the Backstage domain hierarchy or ownership model changes.
source: Authored by Developer AI Tooling based on Barclays Backstage catalog domain conventions.
status: draft
---
# Domain Lookup

Discover business domains and their ownership in the Barclays Backstage catalog.

## Quick Start

To list the business domains (the full entities are very large, so request only the fields you need):

```
mcp__backstage__catalog_query-catalog-entities(
  query: { "kind": "Domain", "spec.type": "domain" },
  fields: ["metadata.name", "metadata.title", "spec.owner"],
  limit: 50
)
```

Then resolve each `spec.owner` to a team name and report the subdomain count.

## When to use

Load when the user wants to:
- List all top-level business domains
- Find who owns a domain or subdomain
- Understand the domain hierarchy at Barclays
- Find which team is responsible for a business area

## Steps

1. Query the business domains. They sit directly under the single root `dom.buk`, which appears in the results too:
   ```
   mcp__backstage__catalog_query-catalog-entities(
     query: { "kind": "Domain", "spec.type": "domain" },
     fields: ["metadata.name", "metadata.title", "spec.owner"],
     limit: 50
   )
   ```
   Use the `cursor` from the response for further pages.

2. For each domain, display:
   - `metadata.title` or `metadata.name`
   - the owner, resolved from the `ownedBy` relation (for example `group:buk/digital`) to a group entity for team name + email
   - `metadata.description`

3. If the user names a specific domain, fetch it directly:
   ```
   mcp__backstage__catalog_get-catalog-entity(kind: "Domain", name: "[name]")
   ```
   Then find its subdomains (use the bare domain name, such as `dom.credit-card`, not a `domain:buk/…` reference):
   ```
   mcp__backstage__catalog-mcp_get_entities_with_custom_query(
     filter: "kind=Domain,spec.type=subdomain,spec.subdomainOf=[domain-name]",
     fields: "metadata.name,metadata.title"
   )
   ```
   The `hasPart` relations on the domain entity list the same subdomains.

## Output format

For each domain:
```
**[Domain Title]** (`[entity-name]`)
Owner: [Team name] — [email if available]
Description: [spec description or metadata.description]
Subdomains: [count] — e.g. the first few subdomain titles
```

Always report if no domains match the user's query — do not invent alternatives.

## Agent Self-Check

- [ ] Did I query the catalog before listing any domains?
- [ ] Did I resolve the `ownedBy` relation to a human-readable team name?
- [ ] Did I include subdomain count where available?
- [ ] Did I report honestly if a named domain was not found?
- [ ] Did I avoid inventing or inferring domain names not returned by the catalog?
