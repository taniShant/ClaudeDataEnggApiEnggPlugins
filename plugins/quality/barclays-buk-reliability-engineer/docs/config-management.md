# Config Management — Detailed Standards

The agent reviews code for configuration hygiene risks. No automated implementation — findings are advisory with remediation guidance.

---

## Hardcoded Environment Values

Zero tolerance. The agent flags any environment-specific value in source code.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Hardcoded URL / hostname | Critical | Literal URL string in source (e.g., `https://api.prod.internal/...`) |
| Hardcoded port number | Medium | Port literal that differs between environments |
| Hardcoded environment name | High | String literals like `"production"`, `"staging"` used for branching logic |
| Hardcoded credentials | Critical | Passwords, API keys, tokens, certificates in source or config files |

---

## Config Validation at Startup

Required configuration must be validated early in the application lifecycle. Fail fast with a clear error message rather than failing later with a cryptic nil/empty dereference.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Unvalidated required env var | Critical | `os.Getenv("X")` (Go), `process.env.X` (Node.js), `os.environ.get("X")` (Python), `System.getenv("X")` (Java) used directly in business logic without checking for empty/nil at startup |
| No fail-fast on missing config | High | Application starts successfully with missing config, then fails at runtime when the config is first accessed — error is cryptic and hard to diagnose |
| Config error not actionable | Medium | Validation error message does not name the missing key or expected format — engineer must read source to diagnose |

---

## Incomplete Implementation Markers

TODO/FIXME/HACK/XXX comments in production code paths indicate incomplete functionality that has been shipped. These must be resolved or tracked in a backlog before production deployment.

| Finding | Severity | Trigger |
|---------|----------|---------|
| TODO/FIXME in production code path | High | `TODO`, `FIXME`, `HACK`, or `XXX` comment in a file that is not a test (`_test.go`, `.test.ts`, `.spec.ts`, `test_*.py`) or documentation (`.md`, `.txt`) |
| Untracked incomplete implementation | High | TODO comment with no JIRA ticket reference — incomplete work that is not tracked in a backlog |
| Placeholder return value | Medium | Function returns a hardcoded/empty value with a comment indicating it should be replaced (e.g., `return nil // TODO: implement`, `return "" // FIXME`) |

---

## Secrets Management

Secrets must be retrieved from an approved secrets manager (CSM) at runtime. Never at build time, never from environment variable defaults in code.

| Finding | Severity | Trigger |
|---------|----------|---------|
| Secret in config file | Critical | Passwords, tokens, or keys in `application.yml`, `.env`, or equivalent |
| Secret as build-time env var | High | Secret injected during Docker build or CI pipeline, baked into image |
| No rotation mechanism | Medium | Secret with no documented rotation procedure or TTL |
| Shared secret across environments | Critical | Same credential used in dev and prod |

---

## Feature Flags

Environment-specific behaviour must be controlled by feature flags or external config — not code-level branching.

| Finding | Severity | Trigger |
|---------|----------|---------|
| `if (env === "production")` pattern | High | Code branching on environment name |
| Behaviour differs by env with no flag | Medium | Logic that only applies in certain environments without external control |
| No kill switch for new features | Medium | New capability with no way to disable without redeployment |

---

## Config Documentation

| Finding | Severity | Trigger |
|---------|----------|---------|
| Undocumented config keys | Medium | Config keys with no description in README, config schema, or comments |
| No default value for non-secret config | Medium | Config that requires a value but has no sensible default |
| Config scattered across multiple files | Medium | No single reference for all config an operator needs to set |
