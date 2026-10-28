---
description: Fetch and summarize a Confluence page by ID or URL
user-invocable: true
argument-hint: "[page ID or URL]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-confluence:read`, they want to fetch and read a specific Confluence page by its page ID or full URL.

## Instructions

1. **Delegate to Subagent**: Delegate this task to the `barclays-buk-confluence:confluence-agent` subagent.
   - Pass the user's argument (page ID or URL) to the subagent.
   - Instruct the subagent to perform the **Read** operation.

2. **Fallback Behavior**: If the `barclays-buk-confluence:confluence-agent` subagent is unavailable, inform the user that the Confluence plugin requires the `barclays-buk-confluence:confluence-agent` subagent to function. Suggest they reinstall the plugin.

3. **Handoff**: The subagent handles URL-to-ID resolution, API calls, HTML stripping, and content formatting.

## User Input Format

Arguments after `/barclays-buk-confluence:read`:
- **[page ID or URL]**: A numeric page ID or a full Confluence URL (required)

## Options

| Argument | Description | Required |
|----------|-------------|----------|
| `[page ID]` | Numeric Confluence page ID | Yes (one of) |
| `[URL]` | Full Confluence page URL (ID is extracted automatically) | Yes (one of) |

## Usage Examples

### Example 1: Read by page ID
```bash
/barclays-buk-confluence:read 12345678
```

### Example 2: Read by URL
```bash
/barclays-buk-confluence:read https://confluence.example.com/spaces/ENG/pages/12345678/Deployment+Guide
```

## Example Output

```
# Deployment Guide
Space: Engineering | Version: 12 | Last updated: 2024-03-15 by Jane Smith

The deployment process follows a blue-green pattern with the following stages...
```
