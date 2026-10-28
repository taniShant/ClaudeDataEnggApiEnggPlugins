# barclays-buk-security-architect

> **Status: Draft**

Evaluates solutions for security risks and scans code for vulnerabilities. Produces threat models, security reviews, and compliance validation against Barclays Secure Coding Practices.

## Workflow Position

```
Solution Architect → Security Architect → [gates release]
```

## Dependencies

- `buk-standards` — provides `security` skill

## Agents

| Agent | Purpose |
|---|---|
| `security-architect-agent` | STRIDE threat model, design review, code scan, compliance validation, sign-off recommendation |
