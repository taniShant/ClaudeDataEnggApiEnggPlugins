---
description: Authenticate with the non-production Barclays Backstage Software Catalogue (required when environment is set to non-production).
user-invocable: false
owner: Developer AI Tooling <dspedeveloperaitoolingteam@barclays.com>
review-trigger: When the NP Backstage OAuth flow or MCP server authentication mechanism changes.
source: Authored by Developer AI Tooling based on the Backstage MCP OAuth implementation.
status: draft
---
# Connect to Non-Production Backstage

Authenticate with the non-production Backstage Software Catalogue.

## Quick Start

```
mcp__backstage-np__authenticate()
```

Share the returned URL with the user, then pass the `localhost` callback URL they paste back to `mcp__backstage-np__complete_authentication(callback_url: "...")`.

## When to use

Load this skill when:
- The user's `environment` config is set to `non-production`
- MCP calls to `backstage-np` are failing with authentication errors
- The user explicitly asks to connect to staging/dev catalog

## Steps

1. Check if `mcp__backstage-np__authenticate` is available (it appears when the NP server requires OAuth).

2. If authentication is needed, call:
   ```
   mcp__backstage-np__authenticate()
   ```
   This returns an authorization URL. Share it with the user and ask them to open it in their browser.

3. Once the user has completed authorization, their browser will redirect to a `localhost` callback URL. Ask them to copy that URL from the address bar (the page may fail to load — that is expected).

4. Complete authentication:
   ```
   mcp__backstage-np__complete_authentication(callback_url: "<url from user>")
   ```

5. Confirm success by running a quick catalog query:
   ```
   mcp__backstage-np__catalog-mcp_get_entity_types_for_kind(kind: "Domain")
   ```

If authentication tools are not present, the NP server may already be connected — try a catalog query directly.

## Token lifespan

NP environment tokens are valid for **1 hour**. If MCP calls start failing with authentication errors mid-session, the token has expired — repeat the steps above to re-authenticate.

## Agent Self-Check

- [ ] Did I check whether `mcp__backstage-np__authenticate` is available before attempting OAuth?
- [ ] Did I share the authorization URL with the user rather than opening it myself?
- [ ] Did I inform the user that the localhost callback page failing to load is expected?
- [ ] Did I confirm successful authentication with a catalog query after completing the flow?
- [ ] Did I fall back to a direct catalog query if authentication tools were not present?
