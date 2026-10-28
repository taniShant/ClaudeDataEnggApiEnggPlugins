---
description: Route a problem description to the right BUK plugin and agent, with a ready-to-run invocation
user-invocable: true
argument-hint: "[describe your problem]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-discovery:discover`, they want to know which BUK plugin and agent to use for their problem, and exactly how to invoke it.

## Instructions

1. **Extract inputs**: Take the user's arguments as the `PROBLEM`. If they are in a project directory, use the current working directory as `PROJECT_PATH`. Otherwise set it to `unknown`.

2. **Delegate to subagent**: Delegate to the `barclays-buk-discovery:discover-agent` subagent with:
   - `PROBLEM`: the user's argument text
   - `PROJECT_PATH`: current working directory or `unknown`

3. **Output verbatim**: Take the subagent's full response and output it to the user exactly as returned. Do not summarise, interpret, or add commentary. Do not attempt to answer the problem yourself — your only job is to surface the routing recommendation.

4. **Do not answer the question**: The user is asking what to run, not asking you to solve their problem. Even if you know how to fix a Wiz finding or build a screen, do not do it. Route only.

5. **Fallback**: If the subagent is unavailable, tell the user to reinstall the `barclays-buk-discovery` plugin.

## Options

| Argument | Description | Required |
|---|---|---|
| `[problem description]` | Plain English description of what you need to do | Yes |

## Usage Examples

```bash
/barclays-buk-discovery:discover I need to build a new savings screen for the iOS app
```

```bash
/barclays-buk-discovery:discover I have Wiz SAST findings to fix in a Java service
```

```bash
/barclays-buk-discovery:discover I need to write acceptance criteria for a new overdraft feature
```

```bash
/barclays-buk-discovery:discover I need to migrate this service from SDK2 to SDK3
```

## Next Steps

Once the discovery agent returns a recommendation, copy the invocation block and run the named agent directly. If the recommended plugin is marked Draft or Planned, check the plugin's README for current status before proceeding.

See also: `docs/plugin-architecture.md` in the BUK repo for the full plugin map.

## Example Output

```
### Recommended: `barclays-buk-ui-engineer-ios`

**Why:** Problem involves iOS screens and project contains an .xcodeproj.

**Entry point:** `ui-engineer-ios-screen-composer-agent`

**Run with:**

  ui-engineer-ios-screen-composer-agent

  PROJECT_PATH:   /Users/me/code/my-ios-project
  JIRA_ID:        <your Jira ticket ID>
  FIGMA_URL:      <Figma URL or "none">
  SCREENS:        []
  ADDITIONAL_INPUT: none

**Standards skills that apply:**
  accessibility — UI screen generation
  security      — handles customer data
  mobile        — iOS platform rules

**Workflow position:**
  ui-engineer-discover-agent → ui-engineer-ios-screen-composer-agent → ui-engineer-ios-validation-agent
```
