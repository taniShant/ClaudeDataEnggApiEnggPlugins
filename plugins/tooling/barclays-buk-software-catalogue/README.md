# barclays-buk-software-catalogue

Navigate the Barclays Software Catalogue — discover domains, capabilities, APIs, and service owners using the Backstage catalog MCP.

## What it does

This plugin gives Claude Code the ability to query the Barclays Backstage Software Catalogue in natural language. It covers:

- **Domain discovery** — list all business domains and their owners
- **API inventory** — find APIs by domain, subdomain, or capability
- **Journey mapping** — trace a business journey across domains to the technical services involved
- **Owner lookup** — resolve service and capability ownership to team names and contacts
- **Architecture guidance** — search ADRs through the Backstage ADR plugin, and browse architecture patterns (`ArchitectureGuidance` entities, which currently exist in the non-production catalog only)
- **NP environment access** — OAuth flow for the non-production catalog

Catalog model: `dom.buk` (root) → `dom.*` domains → `sub.*` subdomains → `cap.*` capabilities. APIs are registered against a domain's system (for example `partner-integration-trans-cell`), not against individual capabilities.

## Installation

```
/plugin install barclays-buk-software-catalogue@barclays-cio-buk
```

## Configuration

After installing, configure the environment:

```
/plugin configure barclays-buk-software-catalogue
```

| Option | Values | Default |
|--------|--------|---------|
| `environment` | `production`, `non-production` | `production` |

## Authenticating to the MCP

The plugin registers two Backstage MCP servers (see [.mcp.json](.mcp.json)): `backstage` (production) and `backstage-np` (non-production). Both use OAuth, and both require the Barclays network or VPN. The `environment` option only controls which server the skills query — both servers are always registered.

### Production

The production MCP (`https://software-catalogue-29950.pr8.apaas4.barclays.intranet`) is the `backstage` server. Authentication uses OAuth with a client ID metadata document (the `clientId` URL in `.mcp.json`). To connect:

1. Run `/mcp` and select `backstage`, then choose **Authenticate**.
2. A browser window opens and signs you in to Backstage via SSO.
3. Grant the MCP server access using your user account. The MCP then acts with your permissions.

Tokens are valid for **1 hour**. If you see authentication errors mid-session, re-authenticate via `/mcp`, or reload the plugin:

```
/reload-plugins
```

### Non-production

The non-production MCP (`https://software-catalogue-gl-29678.np6.apaas4.barclays.intranet`) is the `backstage-np` server. It is authenticated through the plugin's connect skill, which walks you through the OAuth login. Complete the following steps once per session:

1. Set your environment to non-production via `/plugin configure barclays-buk-software-catalogue`

2. Run the connect skill:
   ```
   /barclays-buk-software-catalogue:connect
   ```

3. Claude will call the MCP's `authenticate` tool and return an **authorization URL**. Open that URL in your browser.

4. Log in with your Barclays credentials. Your browser will be redirected to a `localhost` callback URL — **the page will fail to load, that is expected**.

5. Copy the full URL from your browser's address bar (it will look like `http://localhost:<port>/callback?code=...&state=...`) and paste it back into Claude.

6. Claude will complete the OAuth handshake. A confirmation catalog query runs automatically to verify the connection.

Tokens are valid for **1 hour**. After that, MCP calls will begin failing with authentication errors — repeat the connect steps above to re-authenticate. You will also need to re-authenticate each time you start a new Claude Code session.

## Example prompts

- "What domains exist in the BUK catalog?"
- "Who owns the Payment Initiation domain?"
- "List all APIs in the Trade Finance capability"
- "Map the customer onboarding journey to technical services"
- "Connect me to the non-production catalog"

## Owner

Developer AI Tooling — dspedeveloperaitoolingteam@barclays.com
