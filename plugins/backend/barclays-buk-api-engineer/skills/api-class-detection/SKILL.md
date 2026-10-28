---
name: api-class-detection
description: Rules and test scenarios for automatically deriving api_classification (external|internal) from the OAS info.description "API Type:" field.
color: blue
---

> **Source:** Barclays BUK API Engineer plugin — generate workflow Step 6a.
> **Owner:** BUK
> **Review trigger:** When a new Barclays API Type value is introduced or the OAS description convention changes.
> **Status:** Reviewed

# Skill: API Classification Detection from OAS

## Purpose

When generating a Spring Boot 3 project from an OpenAPI 3.x spec, the `api_classification` value determines which SDK3 initializer bean (`ExternalApiInitializer` or `InternalApiInitializer`) is wired into `ApplicationConfig.java`. Rather than prompting the user for this value, it can be derived automatically from the spec's `info.description` field where Barclays teams embed an `API Type:` declaration.

---

## OAS Convention

Barclays OpenAPI specs declare their API type inside `info.description`:

```yaml
info:
  title: My Payment API
  version: 1.0.0
  description: |
    This API handles payment processing for retail customers.

    API Type: External
```

The `API Type:` key may appear anywhere in the description block. Detection is **case-insensitive** and **whitespace-tolerant**.

---

## Mapping Table

| `info.description` `API Type:` value | Normalised `api_classification` |
|---|---|
| `External` | `external` |
| `Process` | `internal` |
| `Internal` | `internal` |
| `Domain` | `internal` |
| _(absent)_ | `null` (prompt user) |
| _(unrecognised value)_ | `null` (prompt user) |

**Case-insensitivity:** `external`, `EXTERNAL`, `External`, `eXtErNaL` all resolve to `external`.

**Priority order** (highest first):

1. Explicit `--api-class` command-line flag
2. `OAS_DETECTED_API_CLASS` (this skill's output)
3. Config file (`.claude/api-engineer-config.yml`)
4. Interactive user prompt (standard mode only)
5. Hardcoded default: `internal`

---

## Extraction Algorithm

```python
import re

def detect_api_classification(description: str) -> dict:
    """
    Extract 'API Type:' from an OAS info.description string.
    Returns:
        {
            "raw_value": str | None,          # the raw token found after "API Type:"
            "detected_api_classification": str | None  # "external" | "internal" | None
        }
    """
    MAPPING = {
        "external": "external",
        "process":  "internal",
        "internal": "internal",
        "domain":   "internal",
    }

    if not description:
        return {"raw_value": None, "detected_api_classification": None}

    # Match "API Type" optionally followed by whitespace, then ":" or "-", then the value token
    match = re.search(r'api\s+type\s*[:\-]\s*(\S+)', description, re.IGNORECASE)
    if not match:
        return {"raw_value": None, "detected_api_classification": None}

    raw = match.group(1).strip().rstrip('.,;')   # strip trailing punctuation
    normalised = MAPPING.get(raw.lower())         # map or None

    return {
        "raw_value": raw,
        "detected_api_classification": normalised
    }
```

---

## Unit Test Scenarios

These scenarios define the expected detection behaviour. Every change to the mapping table or extraction algorithm must pass all tests.

### Test Group 1: Standard mappings

| # | `info.description` content | Expected `detected_api_classification` | Expected `raw_value` |
|---|---|---|---|
| T1 | `"API Type: External"` | `external` | `External` |
| T2 | `"API Type: Process"` | `internal` | `Process` |
| T3 | `"API Type: Internal"` | `internal` | `Internal` |
| T4 | `"API Type: Domain"` | `internal` | `Domain` |

### Test Group 2: Case-insensitive values

| # | `info.description` content | Expected `detected_api_classification` |
|---|---|---|
| T5 | `"API Type: external"` | `external` |
| T6 | `"API Type: EXTERNAL"` | `external` |
| T7 | `"API Type: eXtErNaL"` | `external` |
| T8 | `"API Type: PROCESS"` | `internal` |
| T9 | `"API Type: process"` | `internal` |
| T10 | `"API Type: INTERNAL"` | `internal` |
| T11 | `"API Type: DOMAIN"` | `internal` |

### Test Group 3: Absent or unparseable

| # | `info.description` content | Expected `detected_api_classification` | Expected `raw_value` |
|---|---|---|---|
| T12 | `"A payment processing API."` (no API Type line) | `null` | `null` |
| T13 | `null` / empty description | `null` | `null` |
| T14 | `"API Type: Unknown"` | `null` | `Unknown` |
| T15 | `"API Type: GraphQL"` | `null` | `GraphQL` |
| T16 | `"API Type: "` (value absent after colon) | `null` | `null` |

### Test Group 4: Whitespace and formatting variations

| # | `info.description` content | Expected `detected_api_classification` |
|---|---|---|
| T17 | `"API Type :  External"` (spaces around colon) | `external` |
| T18 | `"api type: External"` (lowercase key) | `external` |
| T19 | `"API TYPE: External"` (uppercase key) | `external` |
| T20 | `"API Type - External"` (dash separator) | `external` |
| T21 | Multi-line description with API Type on line 3 | `external` |
| T22 | `"API Type: External."` (trailing period) | `external` |
| T23 | `"API Type: External,"` (trailing comma) | `external` |

### Test Group 5: Priority precedence

| # | Scenario | `--api-class` flag | `OAS_DETECTED_API_CLASS` | Expected resolved `api_classification` | Prompt shown? |
|---|---|---|---|---|---|
| T24 | Flag takes precedence over OAS | `external` | `internal` | `external` | No |
| T25 | OAS used when no flag | _(not provided)_ | `external` | `external` | No |
| T26 | OAS used when no flag | _(not provided)_ | `internal` | `internal` | No |
| T27 | Prompt when both null | _(not provided)_ | `null` | _(user input)_ | **Yes** |
| T28 | Full-automation, no flag, no OAS | _(not provided)_ | `null` | `internal` (default) | No |

---

## Logging Contract

The following log entries must appear in `.claude/generation.log` for each detection outcome:

**Successful detection:**
```
[PHASE 1a] api-class derived from OAS: external (source: API Type: External in info.description)
ℹ️  API classification auto-detected from spec: external (source: API Type: External in info.description)
```

**Flag overrides detection:**
```
[PHASE 1a] api-class explicitly provided via --api-class flag: external. OAS detection skipped.
```

**Detection failed — will prompt:**
```
[PHASE 1a] api-class not derivable from OAS (API Type absent or unrecognised). Will prompt user in Phase 2.
```

**Detection failed — full-automation, using default:**
```
[PHASE 1a] api-class not derivable from OAS (API Type absent or unrecognised). Full-automation mode: using default 'internal'.
```

---

## Principles

**Principle 4 (Independently invocable):** This skill documents a self-contained detection algorithm with an explicit input (`info.description` string) and an explicit output (`detected_api_classification` + `raw_value`). Any agent can apply it standalone — it requires no upstream context beyond the OAS spec field value. The mapping table and extraction algorithm are fully specified here with no external dependencies.

**Principle 5 (Transparent about unknowns):** When the `API Type:` key is absent, the value is unrecognised, or the description field is empty, the skill returns `null` and documents this explicitly in the Mapping Table (rows 5–6) and Test Group 3. Agents loading this skill must report which resolution path was taken (`api_classification_source`) so the outcome is always traceable. The Known Limitations section in Source Attribution lists what this skill cannot detect.

**Principle 7 (No workflow enforcement):** This skill defines detection rules only — it does not instruct the loading agent to skip prompts, use full-automation defaults, or make any workflow decision. Those sequencing choices belong to the command layer (e.g. the `generate` command) or the orchestrator. The skill's priority order table describes the precedence contract but does not enforce it; the caller decides which path to take.

---

## Relationship to barclays-buk-standards:api-design

This skill does **not** duplicate and does **not** depend on `barclays-buk-standards:api-design`.

**What `barclays-buk-standards:api-design` covers:** DAF architecture principles, authorization layers (Edge Gateway, VINZ, DAF API), DAF header contract, OpenAPI documentation rules, versioning policy, request handling, error handling, caching, logging, and deployment standards. It is a *design* standard — it tells teams how to build and govern APIs.

**What this skill covers:** A single, narrow code-generation concern — reading the `API Type:` metadata value already embedded in an OAS `info.description` field to avoid prompting the user for a value the spec already declares. It is a *generation tooling* concern — it tells the `spec-parsing-agent` and `clarification-checkpoint-agent` how to extract and resolve one input parameter.

**Why this skill is domain-specific and necessary:**

1. **Different layer** — `api-design` governs how APIs are designed and deployed. This skill governs how the *generator* reads a pre-existing spec to configure itself. The two layers do not interact.
2. **Nothing shared** — `api-design` contains no content about `API Type:` field parsing, `ExternalApiInitializer`, `InternalApiInitializer`, extraction algorithms, or priority resolution logic. Merging this content into `api-design` would contaminate a design standard with generator internals.
3. **Different review triggers** — `api-design` changes when Barclays DAF architecture evolves. This skill changes only when the Barclays `API Type:` naming convention changes or a new type value is introduced. These are independent events.

**`plugin.json` dependency:** No change required. The `plugin.json` already declares `barclays-buk-standards` as a dependency for the agents that load `api-design`. This skill does not load `api-design` and requires no additional dependency entry.

---

## Source Attribution

**Primary sources:**
- Barclays BUK API Engineer plugin — generate workflow Step 6a (internal design specification)
- Barclays OpenAPI Specification Standard — `info.description` field convention for API Type declaration
- BUK Retail CAPL team knowledge: production API specs observed to contain `API Type: external` / `API Type: internal` declarations

**Training knowledge applied:**
- OAS 3.x `info.description` field parsing (multi-line YAML `|` block scalar)
- Case-insensitive substring matching patterns for configuration detection

**Known limitations:**
- Only recognises the `API Type:` prefix convention; free-form descriptions without this prefix default to `null` (no classification)
- Does not validate whether the declared type matches the actual audience of the API — that is an architectural decision for the team
- Test scenarios cover the known Barclays convention only; non-standard prefixes are not detected

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Is `detected_api_classification` set to exactly `"external"`, `"internal"`, or `null` — never to the raw token value?
- [ ] Is the detection case-insensitive (passes T5–T11)?
- [ ] Does a missing `API Type:` key produce `null` (passes T12–T13)?
- [ ] Does an unrecognised value produce `null` (passes T14–T15)?
- [ ] Does the explicit `--api-class` flag take priority over OAS detection (passes T24)?
- [ ] Is the user NOT prompted when `OAS_DETECTED_API_CLASS` is non-null (passes T25–T26)?
- [ ] Is the user prompted when both the flag and OAS detection are null, in standard mode (passes T27)?
- [ ] Does full-automation mode default to `internal` when detection fails (passes T28)?
- [ ] Is a one-line notice displayed to the user when auto-detection succeeds?
- [ ] Is the `api_classification_source` field recorded in the state file for traceability?
