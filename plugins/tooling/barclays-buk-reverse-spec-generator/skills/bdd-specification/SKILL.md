---
name: bdd-specification
description: >
    BDD specification format for reverse-spec-generator: Given-When-Then structure,
    entity/behavior/rule/constraint schema, YAML syntax rules, and quality checklist.
    Load when generating, amending, or validating .spec files.
user-invocable: false
---

# BDD Specification Standard

> **Source:** Reverse Spec Generator — BDD Guide and Format Reference (internal)
> **Owner:** Preetha Ramaswamy / BUK Quality Engineering
> **Review trigger:** When the .spec format version changes or BDD conventions are updated
> **Status:** Draft
> Source documents are Internal — Restricted.

> **Scope note:** This skill documents the `.spec` file format used exclusively by the `barclays-buk-reverse-spec-generator` plugin. It is not an organisation-wide BDD standard. General testing and quality standards are in the `barclays-buk-standards` plugin (`testing` skill).

---

## Quick Start

```
Command: /generate-spec, /amend
Agent: reverse-spec-generator-agent (Step 2, Step 4)
Load: Agent loads this skill when generating or amending .spec files
Use: Defines BDD YAML format — entities, behaviors (Given/When/Then), rules, constraints
Model: sonnet (moderate reasoning for behavior extraction)
```

---

## 1. Core Principle

A `.spec` file is a YAML 1.2 document that captures observable system behavior in BDD (Given-When-Then) format. It serves as **living documentation**: specs stay in sync with code through the convergence loop and are used to generate tests. Every spec must describe what the system does from the outside — not how it is implemented internally.

---

## 2. File Format

### 2.1 Root Fields (Required)

```yaml
version: "1.0"        # MUST be "1.0"
module: "name"        # snake_case identifier, alphanumeric + underscore, no spaces
description: "..."    # non-empty string, 10–500 chars
```

### 2.2 Top-Level Sections (at least one required)

| Section | When to use |
|---|---|
| `entities` | Data structures and domain objects |
| `behaviors` | BDD-style operations and use cases |
| `rules` | Business rules and decision logic |
| `constraints` | System limits, invariants, dependencies, timeouts |

---

## 3. Entities

```yaml
entities:
  - name: "EntityName"          # PascalCase, required
    description: "..."           # non-empty, required
    properties:
      - name: "propertyName"     # camelCase, required
        type: "string"           # allowed: string, number, boolean, object, array, null
        required: true           # boolean, optional (defaults false)
        description: "..."       # non-empty, required
        default: "value"         # optional
        enum: ["opt1", "opt2"]   # optional list of allowed values
```

**Naming:** Entity names MUST be PascalCase. Property names MUST be camelCase.

---

## 4. Behaviors

```yaml
behaviors:
  - name: "behavior_name"       # snake_case, required
    description: "..."           # non-empty, required
    given:                       # list, min 1 item, each non-empty string
      - "precondition 1"
    when:                        # list, min 1 item
      - "action or trigger"
    then:                        # list, min 1 item
      - "expected outcome"
    examples:                    # optional
      - input: "example input"
        output: "expected output"
        description: "optional scenario"
```

**Given-When-Then guidelines:**
- `given`: initial state or preconditions — what must be true before
- `when`: the action or trigger — what the user or system does
- `then`: expected outcomes — observable results (not implementation details)

**Quality rules for behaviors:**

| Aspect | Requirement |
|---|---|
| Description | 20+ characters, describes observable behavior |
| `given` items | At least 2 for non-trivial behaviors |
| `then` items | Describes outcomes, not implementation steps |
| Examples | Concrete input/output pairs for complex behaviors |
| Name | snake_case, descriptive, one responsibility |

---

## 5. Rules

```yaml
rules:
  - name: "rule_name"           # snake_case, required
    description: "..."           # why this rule exists, non-empty
    condition: "when X is true"  # specific and testable, required
    action: "then Y happens"     # what occurs when condition is true, required
```

Rules capture business constraints, enforcement logic, and special cases that apply across multiple behaviors.

---

## 6. Constraints

```yaml
constraints:
  - name: "constraint_name"     # snake_case, required
    description: "..."           # non-empty, required
    type: "limit"                # MUST be one of: limit, invariant, dependency, timeout
    value: "constraint value"    # non-empty string, required
```

| Type | Use for |
|---|---|
| `limit` | Upper/lower bounds (max connections, min length) |
| `invariant` | Properties that must always be true |
| `dependency` | External service or prerequisite required |
| `timeout` | Time-based constraint |

---

## 7. Validation Rules

All `.spec` files are validated on save:

1. Valid YAML 1.2 syntax, UTF-8, LF line endings
2. Required top-level fields: `version: "1.0"`, `module`, `description`
3. Entity names: `^[A-Z][A-Za-z0-9]*$` (PascalCase, max 64 chars)
4. Behavior/Rule/Constraint names: `^[a-z_][a-z0-9_]*$` (snake_case, max 64 chars)
5. Descriptions: 10–500 characters, non-empty
6. Types: only from allowed set (string, number, boolean, null, array, object)
7. Constraint types: only limit, invariant, dependency, timeout

---

## 8. Anti-Patterns

| Anti-pattern | Correct approach |
|---|---|
| Implementation details in `then` ("SELECT user FROM database...") | Observable outcomes ("User object is returned") |
| Ambiguous language ("system handles input") | Specific actions ("POST /users endpoint is called") |
| Multiple behaviors in one spec entry | One responsibility per behavior |
| Assumption chaining (given: "user was created in previous test") | Self-contained preconditions |
| Non-YAML comments | Use `description` fields instead |
| Empty strings or null in required fields | Fill all required fields |

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] `version: "1.0"` is present at root
- [ ] `module` is a valid snake_case identifier with no spaces
- [ ] `description` is non-empty (10+ chars) at root level
- [ ] All entity names are PascalCase (e.g. `User`, `AuthToken`)
- [ ] All behavior/rule/constraint names are snake_case (e.g. `authenticate_user`)
- [ ] Every behavior has at least one `given`, `when`, and `then` item
- [ ] Every entity property has `name`, `type`, and `description`
- [ ] All `type` values are from the allowed set: string, number, boolean, null, array, object
- [ ] All `constraint.type` values are from: limit, invariant, dependency, timeout
- [ ] No `then` items describe implementation details (no SQL, no object references)
- [ ] Descriptions are 10–500 characters and non-empty
- [ ] YAML syntax is valid (2-space indentation, no tabs, no trailing whitespace)

---

## Areas for Specialist Extension

This skill covers the base `.spec` format. The following areas may need extension:

- **Domain teams** — Domain-specific entity schemas and constraint types
- **Test framework teams** — Framework-specific test generation patterns from spec behaviors
- **CI/CD teams** — Automated spec validation integration into pipelines
