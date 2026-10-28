---
description: Read and summarize comments on a Confluence page
user-invocable: true
argument-hint: "[page ID or URL]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-confluence:comments`, they want to read and summarize the comments and discussion threads on a specific Confluence page.

## Instructions

1. **Delegate to Subagent**: Delegate this task to the `barclays-buk-confluence:confluence-agent` subagent.
   - Pass the user's argument (page ID or URL) to the subagent.
   - Instruct the subagent to perform the **Comments** operation.

2. **Fallback Behavior**: If the `barclays-buk-confluence:confluence-agent` subagent is unavailable, inform the user that the Confluence plugin requires the `barclays-buk-confluence:confluence-agent` subagent to function. Suggest they reinstall the plugin.

3. **Handoff**: The subagent handles URL-to-ID resolution, API calls, HTML stripping, and formatting the comment threads.

## User Input Format

Arguments after `/barclays-buk-confluence:comments`:
- **[page ID or URL]**: A numeric page ID or a full Confluence URL (required)

## Options

| Argument | Description | Required |
|----------|-------------|----------|
| `[page ID]` | Numeric Confluence page ID | Yes (one of) |
| `[URL]` | Full Confluence page URL (ID is extracted automatically) | Yes (one of) |

## Usage Examples

### Example 1: Comments by page ID
```bash
/barclays-buk-confluence:comments 12345678
```

### Example 2: Comments by URL
```bash
/barclays-buk-confluence:comments https://confluence.example.com/spaces/ENG/pages/12345678/RFC+New+Auth+Flow
```

## Example Output

```
## Comments on "RFC: New Auth Flow" (3 comments)

**Jane Smith** — 2024-03-15:
This looks great, but we should update the API endpoint section to reflect the new gateway.

**John Doe** — 2024-03-16:
Agreed. I'll update it this week. Should we also add the sequence diagram?

**Jane Smith** — 2024-03-17:
Yes, a sequence diagram would be very helpful. Also consider adding the new token refresh flow.
```
