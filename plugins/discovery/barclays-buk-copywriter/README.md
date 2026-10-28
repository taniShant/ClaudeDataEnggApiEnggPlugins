# barclays-buk-copywriter

> **Status: Draft**

Generates customer-facing and UI copy for BUK journeys and communications. Works from PM requirements and UX journey definitions to produce copy that is clear, accessible, and Consumer Duty compliant.

## Channel Scope

All BUK customer-facing channels: app, web, letter, email, SMS, in-app notifications.

## Workflow Position

```
Product Manager → UX Designer → Copywriter → [QA validation]
```

The copywriter agent works from a brief produced by the PM and UX Designer. Compliance validation (CUNA triggers, regulatory language, Consumer Duty sign-off) is handled by downstream QA agents — not this plugin.

## Dependencies

- `buk-standards` — provides `accessibility` and `consumer-duty` skills

## Agents

| Agent | Purpose |
|---|---|
| `copywriter-agent` | Generates journey and communication copy from a PM/UX brief |
