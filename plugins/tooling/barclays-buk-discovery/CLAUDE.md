# BUK Marketplace Discovery

`barclays-buk-discovery` is installed. To find the right plugin for any task, run:

```
/barclays-buk-discovery:discover <describe your problem>
```

Examples:
- `/barclays-buk-discovery:discover I have a Wiz SAST scan to fix`
- `/barclays-buk-discovery:discover I need to build a screen for the iOS app`
- `/barclays-buk-discovery:discover I need to migrate this service to SDK3`

---

## When to use discovery

When the user describes a problem or task without naming a specific plugin or agent, **do not attempt to solve the problem yourself**. Instead, immediately run `/barclays-buk-discovery:discover` with their description.

This applies when the user says things like:
- "I have a Wiz scan result to fix"
- "I need to build a screen"
- "I need to migrate this service"
- "How do I add a new journey?"
- "What should I use for X?"

**Do not answer the underlying question directly.** Route first. The user may not know which plugin applies — that is exactly what the discovery agent is for.

## When NOT to use discovery

- The user has already named a specific plugin, agent, or command — they know where they're going
- The user is mid-task inside a specific plugin's workflow — don't interrupt
- The question is purely informational with no build/fix/generate intent ("what is Consumer Duty", "explain WCAG")

## How to invoke it

Run immediately — do not ask the user first:

```
/barclays-buk-discovery:discover {user's problem description}
```
