---
name: review-config
description: >
    Scans a service codebase for config management gaps and produces a prioritised findings report
    covering hardcoded values, secrets handling, feature flags, config documentation,
    startup validation, and incomplete implementation markers.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When BUK secrets management or feature flag standards change
---

# Review — Config Management

---

## Inputs

```
CODE_PATH:  /absolute/path/to/service   (default: current working directory)
```

---

## Output

A focused config management findings report covering:
- Prioritised findings table (Critical / High / Medium)
- Suggested next steps

---

## Step 1: Silent scan

Use Glob, Read, Bash, and Grep. Output nothing during this phase.

Detect stack and build tool:
- `pom.xml` / `build.gradle` → Spring Boot, Maven/Gradle
- `package.json` → Node.js
- `go.mod` → Go
- `requirements.txt` / `pyproject.toml` → Python

---

## Step 2: Assess config management

Scan for:

- **Hardcoded environment values**: URLs, hostnames, port numbers, credentials, or environment names appearing as string literals in source
- **Secrets not from CSM**: passwords, API keys, tokens that should be fetched from the secrets manager at runtime but appear in config files or environment variable defaults
- **Feature flags**: environment-specific behaviour controlled by code branching rather than flags
- **Undocumented config**: config keys with no description or rationale in comments or docs
- **Config validation at startup**: required env vars (`os.Getenv` in Go, `process.env.X` in Node.js, `os.environ.get` in Python, `System.getenv` in Java) used directly without validating for empty/nil at startup. Flag absence of a fail-fast validation pattern that checks all required config on init.
- **Incomplete implementation markers**: `TODO`, `FIXME`, `HACK`, `XXX` in production code paths (not tests or docs) indicate unfinished functionality that has shipped. Flag with file paths. Distinguish from test/doc TODOs which are acceptable.

---

## Step 3: Produce findings report

Severity definitions:

| Priority | Definition |
|----------|-----------|
| **Critical** | Secrets in source or config files; credentials committed to version control |
| **High** | Hardcoded environment values; config not validated at startup (silent empty-string at runtime) |
| **Medium** | Missing feature flags; undocumented config keys; TODO/FIXME in production code |

Report format:

```markdown
# Config Management Review — [service name]

**Date:** [date]
**Stack:** [stack] ([build tool])
**Modules:** [list]

---

## Summary

[2–3 sentence overview: what is the most significant config risk? Are secrets handled safely?]

---

## Findings

| Priority | Finding | File / Location | Recommendation |
|----------|---------|-----------------|---------------|
| Critical | | | |
| High | | | |
| Medium | | | |

---

## Suggested Next Steps

[3–5 numbered options — never require a specific path]
```

---

## Flags

State any of the following that apply (or "None identified"):

**Missing or ambiguous inputs:**
- CODE_PATH not provided — skill scanned current working directory

**Decisions made under uncertainty:**
- Stack detected as [X] based on [indicator] — if incorrect, specify and re-run
- Secrets manager in use inferred from import patterns and env var names — confirm if detection is uncertain

---

## Agent Self-Check

- [ ] Stack detected
- [ ] All 6 config management scan patterns checked
- [ ] Secret and credential scan completed (not just env var defaults — check hardcoded literals too)
- [ ] TODO/FIXME scan distinguished between production paths and test/docs (test and doc TODOs are acceptable)
- [ ] Startup validation pattern checked for each required config key found
