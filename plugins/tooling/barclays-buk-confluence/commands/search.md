---
description: Search Confluence pages by keyword or CQL query
user-invocable: true
argument-hint: "[CQL query or keywords]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-confluence:search`, they want to search for Confluence pages by keyword or CQL query using the Confluence REST API.

## Instructions

1. **Delegate to Subagent**: Delegate this task to the `barclays-buk-confluence:confluence-agent` subagent.
   - Pass the user's arguments as the search query.
   - Instruct the subagent to perform the **Search** operation.

2. **Fallback Behavior**: If the `barclays-buk-confluence:confluence-agent` subagent is unavailable, inform the user that the Confluence plugin requires the `barclays-buk-confluence:confluence-agent` subagent to function. Suggest they reinstall the plugin.

3. **Handoff**: The subagent handles the full search flow including CQL construction, API calls, and result formatting.

## User Input Format

Arguments after `/barclays-buk-confluence:search`:
- **[CQL query or keywords]**: Plain text keywords or a CQL query string (required)

## Options

| Argument | Description | Required |
|----------|-------------|----------|
| `[keywords]` | Plain text keywords to search for | Yes (one of) |
| `[CQL query]` | Raw CQL query string (detected automatically if CQL operators present) | Yes (one of) |

## Usage Examples

### Example 1: Simple keyword search
```bash
/barclays-buk-confluence:search authentication API
```

### Example 2: CQL query
```bash
/barclays-buk-confluence:search type=page AND space=ENG AND text~"deployment guide"
```

### Example 3: Search within a space
```bash
/barclays-buk-confluence:search runbook incident response
```

## Example Output

```
1. [**Authentication Service Overview**](https://confluence.example.com/spaces/ENG/pages/12345/Authentication+Service+Overview) — Engineering — Last updated 2024-03-15 by Jane Smith

2. [**API Gateway Configuration**](https://confluence.example.com/spaces/PLAT/pages/67890/API+Gateway+Configuration) — Platform — Last updated 2024-02-20 by John Doe

3. [**OAuth2 Token Management**](https://confluence.example.com/spaces/ENG/pages/11111/OAuth2+Token+Management) — Engineering — Last updated 2024-01-10 by Alice Johnson
```
