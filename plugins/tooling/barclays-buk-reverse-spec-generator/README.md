# barclays-buk-reverse-spec-generator

Generate BDD-style behavioral specifications from existing code, with a self-verification loop to converge specs and implementation.

## What it does

Extracts formal behavioral specifications from source code automatically, and provides a self-verification loop to keep specs and code aligned over time.

- **Generate specs from code** — Extract entities, behaviors, rules, and constraints from Python, Java, and JavaScript/TypeScript
- **BDD-style format** — Token-efficient `.spec` YAML files optimized for test generation
- **Amend and refine** — Edit specs and mark behavioral intent (spec-led vs code-led)
- **Convergence checking** — Detect and classify divergences between spec and code
- **Test generation** — Generate test suites from specs (pytest, JUnit 5, Jest)
- **Self-verification loop** — Iterate generate → test → converge → implement until 100% aligned

## Commands

| Command | Description |
|---|---|
| `/generate-spec` | Extract BDD specs from source code files |
| `/amend` | Edit and refine specifications; marks changed behaviors as spec-led |
| `/converge` | Find and classify spec↔code divergences; writes `.convergence.yaml` |
| `/generate-tests` | Generate test suites from a `.spec` file |
| `/run-tests` | Execute tests and map results back to spec behaviors |
| `/implement` | Generate code stubs for spec-led missing or diverged behaviors |
| `/status` | Show the convergence loop dashboard with next-action recommendation |

## Agent

`reverse-spec-generator-agent` — handles all actions, loads domain knowledge skills, maintains `.convergence.yaml` persistent state.

## Self-Verification Loop

```
gather context ────▶ take action ──────▶ verify ─────────▶ repeat
/generate-spec        /generate-tests      /run-tests          until
→ the spec            /implement      →    /converge       →   converged
(durable context)     (spec-led items)     → .convergence.yaml
       ▲                                          │
       └───── /amend (when spec was wrong) ◀──────┘
                                                  │
                                             /status
                                        (loop dashboard)
```

## Specification Format

```yaml
version: "1.0"
module: "my_module"
description: "Module description"

entities:
  - name: "EntityName"
    description: "What this entity represents"
    properties:
      - name: "property"
        type: "string"
        required: true
        description: "Property description"

behaviors:
  - name: "behavior_name"
    description: "What this behavior does"
    given:
      - "initial state"
    when:
      - "action"
    then:
      - "expected outcome"

rules:
  - name: "rule_name"
    description: "Business rule"
    condition: "when X"
    action: "then Y"

constraints:
  - name: "constraint_name"
    description: "System constraint"
    type: "limit|invariant|dependency|timeout"
    value: "constraint value"
```

## Installation

```bash
/plugin install barclays-buk-reverse-spec-generator@barclays-cio-buk
```

## Quick Start

1. Open a source code file in Claude Code
2. Run `/generate-spec` to create initial specifications
3. Review the generated `.spec` files
4. Use `/amend` to refine specifications
5. Use `/converge` to check spec↔code alignment
6. Use `/generate-tests` to create tests from specs
7. Run `/status` at any time to see loop progress

## Supported Languages

- Python (classes, dataclasses, type hints, docstrings)
- Java (classes, interfaces, JavaDoc, Spring annotations)
- JavaScript/TypeScript (classes, functions, JSDoc, type hints)
- Generic extraction (other languages via heuristics)

## Quality Score

**`/test-plugin` score:** 100/100 — PRODUCTION READY

Validated 2026-08-06 against plugin-testing-toolkit v1.0.1. All structure, content, schema, and BUK compliance checks pass.

## Pilot Summary

**Pilot validated 2026-08-06** — validated during strangler refactoring integration pilot.

**Pilot users:**
- Rajshree Jha (rajshree.jha@barclays.com)

### Improvements Implemented

| Improvement | Detail |
|-------------|--------|
| Explicit validator invocation | Agent workflow now calls `validator/spec-check.py` and `validator/post-test.py` directly — no reliance on implicit hook firing |
| Context-diagnostics skill | New skill added for debugging convergence issues and diagnosing extraction failures |
| Agent documentation expansion | Error Handling table, Worked Examples (3 scenarios), and Integration Points added to main agent |
| Status agent expansion | Usage notes, Error Handling, and Worked Examples added to status agent |
| Quick Start in all skills | Quick Start sections added to bdd-specification, convergence-loop, and spec-generation-patterns skills |
| Command documentation | Options table added to `amend.md` command |
| Strangler integration | Validated as Phase 5 BDD extraction provider — generates `.spec` YAML consumed by hexagonal service spec generation |

### Observed During Pilot

- Spec extraction reliable across Python, Java, and TypeScript source
- Convergence loop tracks state correctly across multiple iterations
- Validator scripts provide immediate feedback on spec quality (exit codes suitable for CI)
- Integration with strangler Phase 5 produces dual-artifact output (`.spec` + hexagonal service spec)

## Acknowledgements

Inspired by [Allium](https://github.com/juxt/allium)

## Author

Preetha Ramaswamy — preetha.ramaswamy@barclays.com
