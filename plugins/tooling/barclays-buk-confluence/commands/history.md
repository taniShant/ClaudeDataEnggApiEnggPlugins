---
description: Show edit history of a Confluence page
user-invocable: true
argument-hint: "[page ID or URL]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-confluence:history`, they want to see the version history of a Confluence page — who edited it, when, and what version comments were left.

## Instructions

1. **Delegate to Subagent**: Delegate this task to the `barclays-buk-confluence:confluence-agent` subagent.
   - Pass the user's argument (page ID or URL) to the subagent.
   - Instruct the subagent to perform the **History** operation.

2. **Fallback Behavior**: If the `barclays-buk-confluence:confluence-agent` subagent is unavailable, inform the user that the Confluence plugin requires the `barclays-buk-confluence:confluence-agent` subagent to function. Suggest they reinstall the plugin.

3. **Handoff**: The subagent handles URL-to-ID resolution, API calls, and formatting the version history table.

## User Input Format

Arguments after `/barclays-buk-confluence:history`:
- **[page ID or URL]**: A numeric page ID or a full Confluence URL (required)

## Options

| Argument | Description | Required |
|----------|-------------|----------|
| `[page ID]` | Numeric Confluence page ID | Yes (one of) |
| `[URL]` | Full Confluence page URL (ID is extracted automatically) | Yes (one of) |

## Usage Examples

### Example 1: History by page ID
```bash
/barclays-buk-confluence:history 12345678
```

### Example 2: History by URL
```bash
/barclays-buk-confluence:history https://confluence.example.com/spaces/ENG/pages/12345678/API+Design+Guide
```

## Example Output

```
## Version History for "API Design Guide"

| Version | Author          | Date       | Message                     |
|---------|-----------------|------------|-----------------------------|
| 1       | Jane Smith      | 2024-01-15 | Initial creation            |
| 2       | John Doe        | 2024-02-20 | Updated endpoint section    |
| 3       | Jane Smith      | 2024-03-10 | Added authentication flow   |
| 4       | Alice Johnson   | 2024-03-15 | Fixed formatting issues     |
```
