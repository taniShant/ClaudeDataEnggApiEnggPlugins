---
name: implement
description: >
    Implements observability improvements for a service using a red-green verification loop.
    Plans and applies migrations in sequence (structured logging → correlation IDs → collector
    wiring → sensitive data guard → capability attestation). Manages state in .reliability/.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When OTel SDK versions change or new stacks are added to otel-conventions
---

# Implement — Observability Migrations

> **Skills needed:** Load `barclays-buk-standards:observability` and `otel-conventions` alongside this skill.

---

## Inputs

```
CODE_PATH:     /absolute/path/to/service        (default: current working directory)
MIGRATION:     <NNN> | --all | (none)
               NNN    → implement a specific migration by number
               --all  → implement all remaining migrations in sequence
               (none) → implement the next unimplemented migration only
```

---

## Output

- Code changes implementing the migration(s)
- Updated `.reliability/state.yaml`
- A test proving the migration works
- `.reliability/changelog/<NNN>__<title>.md` (created if absent)

First-run also creates: `.reliability/docker-compose.verify.yaml`, `.reliability/collector-config.yaml`, `.reliability/exports/.gitignore`

---

## Step 1: Read existing state

1. Read `.reliability/observability-target.md` if it exists — understand agreed decisions (schema, strategy, stack)
2. Read `.reliability/state.yaml` if it exists — determine which migrations are already implemented/verified
3. If no target exists, perform a silent scan to determine the stack and current state, then proceed
4. Load `otel-conventions` skill and the stack-specific file

---

## Step 2: Determine what to implement

If a specific migration is requested (e.g., `003`), implement that one.

If no specific migration is given, determine the next unimplemented migration:
- Read `.reliability/changelog/` for existing migration files
- Cross-reference with `.reliability/state.yaml` to find the next pending one
- If no migrations exist, plan the first one (001 — structured logging)

**Advisory phase order:** Logging should come before tracing, tracing before metrics. If asked to implement tracing before logging is complete, proceed with a note: "Logging phase is not yet verified — consider completing logging first for a solid foundation."

---

## Step 3: Plan the migration (if no migration file exists yet)

For the next migration in sequence, generate `.reliability/changelog/<NNN>__<title>.md`:

```markdown
---
version: <NNN>
phase: logging
test_method: <test class>#<test method>
target_files:
  - <relative paths of files to create/modify>
---

# <NNN> — <Title>

## Why

<What gap this migration closes and why it matters>

## Changes

- **<file path>**: <what changes and why>

## Acceptance Criteria

- [ ] <measurable, testable criteria>
```

Then generate the test skeleton in the repo's existing test file (or create a new test class following the repo's conventions):

```java
// Spring Boot example
@Test
void v001_structuredLoggingEmitsOtelSchema() {
    // TODO: assert structured JSON with Timestamp, SeverityText, Body, service.name
}
```

Match the repo's test framework (JUnit 5, Jest/Vitest, pytest, Go testing package).

---

## Step 4: First-run infrastructure

If `.reliability/docker-compose.verify.yaml` does NOT exist, create it now:

```yaml
services:
  otel-collector:
    image: container-release.container-registry-non-prod.barcapint.com/external/docker.io/otel/opentelemetry-collector-contrib:0.149.0
    command: ["--config=/etc/otelcol/config.yaml"]
    volumes:
      - ./collector-config.yaml:/etc/otelcol/config.yaml:ro
      - ./exports:/exports
    ports:
      - "4317:4317"
      - "4318:4318"
```

Create `.reliability/collector-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s

exporters:
  file/logs:
    path: /exports/logs.json
  file/traces:
    path: /exports/traces.json
  file/metrics:
    path: /exports/metrics.json

service:
  pipelines:
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [file/logs]
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [file/traces]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [file/metrics]
```

Create `.reliability/exports/.gitignore`:
```
*
!.gitignore
```

---

## Step 5: Implement the migration

Write the code changes described in the migration file. Follow:
- `otel-conventions` skill for the correct stack-specific patterns
- The repo's existing code style, naming, and file organisation
- The bridge pattern when existing logging infrastructure is present — never remove existing appenders or log destinations

---

## Step 6: Red-green loop (max 5 iterations)

```
iteration = 0
while iteration < 5:
    Run the specific test method
    If PASSES → done, go to Step 7
    If FAILS → read error, diagnose, fix, increment iteration
```

**How to run the test:**
- Spring Boot: `mvn test -pl <module> -Dtest=<TestClass>#<testMethod>`
- Node.js: `npx jest --testPathPattern=<file> --testNamePattern="<method>"` or `npx vitest run <file> -t "<method>"`
- Python: `pytest <file>::<class>::<method> -v`
- Go: `go test ./... -run <TestFunction> -v`

**On failure:** Read the error output carefully. Common issues: missing dependency, config not on classpath, Docker unavailable (switch to schema-only assertions), import errors.

---

## Step 7: Report and update state

Update `.reliability/state.yaml` (create if absent):

```yaml
migrations:
  "001":
    status: implemented
    implemented_at: <ISO 8601 timestamp>
```

Report what was done, what the test proves, and what the suggested next step is.

**On stuck (5 iterations exhausted):** Report what was tried and where it's blocked. Ask the user how to proceed — provide a hint, take over manually, or skip. Do not abandon silently.

---

## Suggested Next Steps

Always end with 2–4 numbered options. Examples:

```
**Suggested next steps:**
1. Implement the next migration — run /barclays-buk-reliability-engineer:implement for <NNN+1>
2. Verify the logging phase — run the full phase test suite to confirm phase completion
3. Review other capability areas — run /barclays-buk-reliability-engineer:review
4. Nothing right now — changes look good as-is
```

---

## Flags

State any of the following that apply (or "None identified"):

**Placeholder skills:**
- `barclays-buk-standards:observability` is a placeholder — phase gate criteria used from `otel-conventions` only
- `otel-conventions` unavailable — implementation patterns may not match BUK stack conventions

**Missing or ambiguous inputs:**
- No `.reliability/observability-target.md` found — implementation based on code scan only
- CODE_PATH not provided — scanned current working directory

**Decisions made under uncertainty:**
- Stack detected as [X] based on [indicator] — if incorrect, specify and re-run
- Docker availability assumed — if Docker is unavailable, switch to schema-only verification and flag

---

## Agent Self-Check

- [ ] Existing state files read before planning any migration
- [ ] Stack-specific `otel-conventions` file loaded
- [ ] Migration file created in `.reliability/changelog/` before implementing
- [ ] First-run infrastructure created if `.reliability/docker-compose.verify.yaml` absent
- [ ] Bridge pattern used — no existing log destinations removed
- [ ] Red-green loop ran (max 5 iterations); result reported
- [ ] `.reliability/state.yaml` updated after successful implementation
- [ ] OTLP exporter gated on `OTEL_EXPORTER_OTLP_ENDPOINT` env var
- [ ] Container images reference internal registry only (`container-release.container-registry-non-prod.barcapint.com`)
