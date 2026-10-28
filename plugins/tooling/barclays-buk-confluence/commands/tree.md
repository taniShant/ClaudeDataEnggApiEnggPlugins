---
description: Browse page hierarchy in a Confluence space
user-invocable: true
argument-hint: "[space key or page ID]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-confluence:tree`, they want to browse the page hierarchy — either for an entire Confluence space or under a specific parent page.

## Instructions

1. **Delegate to Subagent**: Delegate this task to the `barclays-buk-confluence:confluence-agent` subagent.
   - Pass the user's argument (space key or page ID) to the subagent.
   - Instruct the subagent to perform the **Tree** operation.

2. **Fallback Behavior**: If the `barclays-buk-confluence:confluence-agent` subagent is unavailable, inform the user that the Confluence plugin requires the `barclays-buk-confluence:confluence-agent` subagent to function. Suggest they reinstall the plugin.

3. **Handoff**: The subagent handles determining whether the input is a space key or page ID, fetching child pages, and rendering the tree.

## User Input Format

Arguments after `/barclays-buk-confluence:tree`:
- **[space key or page ID]**: A Confluence space key (e.g. `ENG`) or a numeric page ID (required)

## Options

| Argument | Description | Required |
|----------|-------------|----------|
| `[space key]` | Confluence space key (e.g. `ENG`) — short uppercase string | Yes (one of) |
| `[page ID]` | Numeric page ID to browse children of | Yes (one of) |

## Usage Examples

### Example 1: Browse a space
```bash
/barclays-buk-confluence:tree ENG
```

### Example 2: Browse children of a page
```bash
/barclays-buk-confluence:tree 12345678
```

## Example Output

```
Space: Engineering (ENG)
├── Architecture
│   ├── API Design Guidelines
│   └── Database Schema Docs
├── Runbooks
│   ├── Deployment Process
│   └── Incident Response
└── Onboarding
    ├── New Starter Guide
    └── Team Directory
```
