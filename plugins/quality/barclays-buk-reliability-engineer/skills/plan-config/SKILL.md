---
name: plan-config
description: >
    Leads an interactive config management planning session for a greenfield service. Walks through
    one multichoice question per turn covering deployment target, secrets management, feature flags,
    and config validation strategy. Converges on a written config target document.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When BUK secrets management platform or feature flag standards change
---

# Plan — Config Management

For greenfield services making upfront config management design decisions. Leads a session that converges on a config target covering secrets strategy, feature flags, and startup validation approach.

---

## Inputs

```
CODE_PATH:  /absolute/path/to/service   (default: current working directory)
```

---

## Output

`.reliability/config-target.md` documenting agreed secrets management approach, feature flag strategy, and config validation pattern.

---

## Format rule

Every question must be a numbered multichoice list. Always mark one option **(recommended)**. Always offer a custom/different option. One question per response — never batch questions.

---

## Step 1: Silent scan

Scan the repo to detect stack, build tool, module structure, existing environment variable usage, any secrets manager SDK imports, and feature flag client imports. Do NOT output anything.

---

## Step 2: Walk the decision tree

Ask one question at a time, wait for response, then continue:

**Question 1 — Deployment target:**
```
Where will this service be deployed? This determines which config injection patterns apply.
1. Kubernetes — env vars from ConfigMaps and Secrets (recommended for containerised services)
2. AWS Lambda — env vars from Lambda environment configuration
3. EC2 / VM — env vars from instance profile or startup scripts
4. Multiple / not yet decided — describe
```

**Question 2 — Secrets management:**
```
How will this service retrieve secrets at runtime?
1. CyberArk Conjur — BUK standard CSM (recommended)
2. AWS Secrets Manager — use if service already uses AWS SDK heavily
3. Kubernetes Secrets — acceptable only for non-sensitive config; not for credentials
4. Not decided yet — describe the security requirements
```

**Question 3 — Feature flags:**
```
Does this service need feature flags to control environment-specific behaviour?
1. Yes — use a flag provider to avoid code branching per environment (recommended if env differences exist)
2. No — behaviour is identical across environments; no flags needed
3. Not yet — the service is greenfield with no environment-specific paths today
4. Using an existing flag provider — specify which one
```

**Question 4 — Config validation:**
```
How should this service handle missing required config at startup?
1. Fail fast — validate all required env vars at startup, log clear errors, refuse to start (recommended)
2. Fail on first use — let the service start, fail only when the missing config is accessed
3. Default values — provide sensible defaults for missing config where safe to do so
4. Combination — describe which keys need fail-fast vs. defaults
```

---

## Step 3: Convergence summary

Present a summary of agreed decisions. Explain what the config target gives the team — no secrets in source, fail-fast on misconfiguration, feature flags for safe environment differences. Ask for approval.

---

## Step 4: Write the target

On approval, write `.reliability/config-target.md`:

```markdown
---
deployment_target: <kubernetes|lambda|ec2|mixed>
secrets_manager: <cyberark-conjur|aws-secrets-manager|kubernetes-secrets|tbd>
feature_flags: <provider-name|none|tbd>
config_validation: <fail-fast|fail-on-use|defaults|mixed>
---

# Config Management Target

## Decisions

- **Deployment target:** [target]
- **Secrets management:** [CSM]
- **Feature flags:** [provider or none]
- **Config validation:** [strategy]

## Patterns to Enforce

Based on the above decisions, enforce these patterns in code review:

| Pattern | Why it applies here |
|---------|-------------------|
| [e.g. All secrets fetched from CyberArk Conjur at startup — never from env var defaults] | [CyberArk Conjur confirmed as CSM] |
| [e.g. Fail-fast validation block at application entrypoint] | [fail-fast strategy agreed] |
| [e.g. No hardcoded URLs or hostnames] | [Kubernetes deployment — all endpoints from env vars] |

## Required Config Keys

List config keys identified during scan (populate as the service develops):

| Key | Required | Source | Validation |
|-----|----------|--------|-----------|
| [e.g. DATABASE_URL] | Yes | Env var (Kubernetes ConfigMap) | Non-empty at startup |
| [e.g. API_KEY] | Yes | CyberArk Conjur | Non-empty at startup |
```

After writing, suggest next steps.

---

## Backward compatibility

If `.reliability/config-target.md` already exists:
- Read it and understand agreed decisions
- Report what has already been decided and ask whether to update specific decisions or proceed with a review
- Do NOT overwrite without explicit confirmation

---

## Suggested Next Steps

Always end with 2–5 numbered options. Examples:

```
**Suggested next steps:**
1. Review config — run /barclays-buk-reliability-engineer:review-config to scan existing code against this target
2. Design another area — run /barclays-buk-reliability-engineer:plan observability|performance|resilience
3. Review the target — inspect .reliability/config-target.md before starting
4. Something different — describe what you'd like to do
```

---

## Flags

State any of the following that apply (or "None identified"):

**Missing or ambiguous inputs:**
- CODE_PATH not provided — scanned current working directory

**Decisions made under uncertainty:**
- Deployment target inferred from Docker/Kubernetes config files — confirmed in Question 1 if uncertain
- Secrets manager inferred from existing SDK imports — override in Question 2 if needed

---

## Agent Self-Check

- [ ] Silent scan completed before asking any questions
- [ ] Each question presented one at a time with numbered options and a recommendation
- [ ] All 4 decision questions answered before writing the target
- [ ] Convergence summary shown and approved before writing
- [ ] `.reliability/config-target.md` written with correct frontmatter
- [ ] Backward compatibility: existing target read and preserved unless explicitly overwritten
