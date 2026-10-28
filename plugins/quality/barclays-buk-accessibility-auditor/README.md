# barclays-buk-accessibility-auditor

> **Status: Draft**

Checks compliance of solutions against industry accessibility rules. Audits against WCAG 2.1 AA, keyboard navigation, and screen reader requirements.

## Workflow Position

```
UI Engineer → Accessibility Auditor → [gates release]
```

## Dependencies

- `buk-standards` — provides `accessibility` skill

## Agents

| Agent | Purpose |
|---|---|
| `accessibility-auditor-agent` | READ-ONLY auditor producing scored pass/fail report with remediation guidance |
