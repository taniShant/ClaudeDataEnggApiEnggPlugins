---
description: Ask a question and get an answer synthesized from Confluence pages
user-invocable: true
argument-hint: "[your question]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-confluence:ask`, they want to ask a question and receive a comprehensive answer synthesized from relevant Confluence pages, with citations.

## Instructions

1. **Delegate to Subagent**: Delegate this task to the `barclays-buk-confluence:confluence-agent` subagent.
   - Pass the user's question to the subagent.
   - Instruct the subagent to perform the **Ask (RAG)** operation.
   - **IMPORTANT**: Require the subagent to include inline citations with VISIBLE URLs for EVERY statement, claim, or fact presented in the answer, not just at the end.

2. **Citation Format**: Every sentence or claim must be followed by or include an inline citation showing both the page title AND the full URL. Use format: `[Page Title - https://confluence.example.com/...]` so that both title and clickable URL are visible inline where the information is used, not grouped at the end.

3. **Fallback Behavior**: If the `barclays-buk-confluence:confluence-agent` subagent is unavailable, inform the user that the Confluence plugin requires the `barclays-buk-confluence:confluence-agent` subagent to function. Suggest they reinstall the plugin.

4. **Handoff**: The subagent handles the full RAG pipeline: query formulation, search, content retrieval, synthesis, and **inline citation formatting for every statement**.

## User Input Format

Arguments after `/barclays-buk-confluence:ask`:
- **[your question]**: A natural language question to answer from Confluence content (required)

## Options

| Argument | Description | Required |
|----------|-------------|----------|
| `[question]` | Natural language question to answer from Confluence content | Yes |

## Usage Examples

### Example 1: Technical question
```bash
/barclays-buk-confluence:ask How does our authentication service handle token refresh?
```

### Example 2: Process question
```bash
/barclays-buk-confluence:ask What is the deployment process for production releases?
```

### Example 3: Architecture question
```bash
/barclays-buk-confluence:ask What databases does the payments service depend on?
```

## Example Output

```
The authentication service handles token refresh using a rotating refresh token pattern
[Auth Service Architecture - https://confluence.example.com/spaces/ENG/pages/111].
When a client presents an expired access token, the auth middleware checks for a valid
refresh token and issues a new access/refresh token pair
[Auth Service Architecture - https://confluence.example.com/spaces/ENG/pages/111].

## Sources
- [Auth Service Architecture](https://confluence.example.com/spaces/ENG/pages/111) — Engineering
- [Service Configuration Guide](https://confluence.example.com/spaces/ENG/pages/222) — Engineering
```
