---
name: implement
description: Generate code stubs for spec-led behaviors (source_of_truth=spec) that are missing or diverged — Java, Python, and JavaScript supported.
agent: reverse-spec-generator-agent
allowed-tools: Read, Write, Glob
---

# Implement

Generate code stubs for behaviors where the **spec is the source of truth** and the implementation is missing or wrong. Closes the "then implement" phase of the verification loop.

## Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `spec_file` | path | yes | — | Path to .spec file containing behaviors to implement |
| `--language` | enum | no | auto-detect | Target language: `python`, `java`, `javascript` |
| `--output` | path | no | auto (matches source structure) | Directory to write generated stubs |
| `--behavior` | string | no | all diverged/missing | Implement specific behavior only |
| `--stub-style` | enum | no | `raise` | Stub body: `raise` (NotImplementedError) or `todo` (comment placeholder) |

## Overview

`/implement` is the action step after `/converge` or `/run-tests` identifies spec-led gaps. It:

- **Reads `.convergence.yaml`** to find behaviors with `source_of_truth: spec` and `divergence_status: missing_impl` or `diverged`
- **Generates language-appropriate stubs** — Spring/Java, Python, or JavaScript
- **Creates scaffold only** — stubs raise `UnsupportedOperationException` / `NotImplementedError` until you fill them in
- **Updates convergence state** — marks each stubbed behavior as `implementation_status: stub_generated`

## When to Use

Use `/implement` when `/converge` or `/run-tests` shows:

```
  ✗ get_steps  [HIGH]
    type   : missing_impl
    truth  : spec  (spec leads → update code)
    action : Implement the behavior in code, or remove from spec
```

Do **not** use `/implement` for:
- `source_of_truth: code` divergences — use `/amend` instead
- `source_of_truth: unknown` divergences — decide the correct side first

## How It Works

1. Read `.convergence.yaml` for the spec
2. Filter to items: `source_of_truth == "spec"` AND `divergence_status in (missing_impl, diverged)`
3. Detect the target language from project files
4. Generate a stub file per module containing all missing behaviors
5. Write stubs to `stubs/` in the project directory (or a specified location)
6. Print a summary of what was generated

## Usage

```
/implement
# Spec file: a-digi-msg-data-mgt.spec
# Language: java
```

Or auto-detect language:

```
/implement
```

Specify a target directory:

```
/implement
# Spec file: a-digi-msg-data-mgt.spec
# Output: src/main/java/com/barclays/api/stubs/
```

## Generated Stub Examples

### Java (Spring)

```java
// AUTO-GENERATED STUBS — fill in implementation
// Source: a_digi_msg_data_mgt spec
// Run /converge after implementing to verify alignment

@RestController
public class ADigiMsgDataMgtStubs {

    /**
     * Retrieve ordered step content for a journey.
     *
     * Given:
     *   - The request contains a valid location and action
     *   - AEM content is accessible
     * When:
     *   - POST /steps is called with StepsApiRequest
     * Then:
     *   - Step definitions are retrieved and mapped from AEM content
     *   - 200 response with StepsResponse
     *
     * NOTE: stub — divergence_type=missing_impl
     */
    @PostMapping("/get-steps")
    public ResponseEntity<?> getSteps() {
        throw new UnsupportedOperationException("Stub: get_steps not implemented");
    }
}
```

### Python

```python
def get_steps(*args, **kwargs):
    """
    Retrieve ordered step content for a journey identified by location and action.

    Given:
        - The request contains a valid location and action identifying a journey
        - AEM content is accessible
    When:
        - POST /steps is called with StepsApiRequest
    Then:
        - Step definitions are retrieved and mapped from AEM content
        - 200 response with StepsResponse containing ordered step list

    Note: stub — divergence_type=missing_impl
    """
    raise NotImplementedError("get_steps is not implemented")
```

### JavaScript

```javascript
/**
 * Retrieve ordered step content for a journey.
 * Given: The request contains a valid location and action
 * Then: Step definitions retrieved from AEM; 200 response
 * @stub divergence_type=missing_impl
 */
async function getSteps(...args) {
  throw new Error("Stub: get_steps not implemented");
}
```

## Language Detection

The target language is inferred from:

| Signal | Language |
|---|---|
| `build.gradle` or `*.java` files present | Java |
| `setup.py`, `pyproject.toml`, or `*.py` files | Python |
| `package.json` or `*.ts` / `*.js` files | JavaScript |

Override with `# Language: java` in the command invocation.

## Output Location

Stubs are written to `stubs/` relative to the spec file by default.

To integrate directly into your source tree, specify the full output path:

```
/implement
# Output: src/main/java/com/barclays/api/messaging/controller/
```

## After Generating Stubs

1. Open the stub file and implement each method
2. Run `/run-tests` to verify the implementation passes tests
3. Run `/converge` to confirm the divergence is resolved
4. Delete the stub file once the real implementation is in place

## Important Notes

- Stubs are **scaffolding, not production code** — they will throw on any invocation
- One stub file is generated per module, not per behavior
- If a behavior already has an implementation, `/implement` will note it and skip
- `/implement` does not modify existing source files — it creates new stub files only

## Loop Integration

```
/converge (or /run-tests)
    │
    ├── source_of_truth: spec  →  /implement  →  fill in stubs  →  /run-tests  →  /converge
    ├── source_of_truth: code  →  /amend
    └── source_of_truth: unknown  →  human decision first
```

Run `/status` to see all open items and the recommended next action.
