# barclays-buk-incident-manager

> **Status: Draft**

Monitors services in production to evaluate risks and find root cause when things go wrong. Reviews logs, analyses incidents, and determines RCA.

## Workflow Position

```
Production incident → Incident Manager → Reliability Engineer / Security Architect
```

## Dependencies

- `buk-standards` — provides `security` skill

## Agents

| Agent | Purpose |
|---|---|
| `incident-manager-agent` | READ-ONLY analyst producing incident timeline, impact assessment, RCA, and remediation actions |
