---
name: generate-spec
description: Generate BDD specifications from source code files — extracts entities, behaviors, rules, and constraints automatically.
agent: reverse-spec-generator-agent
allowed-tools: Read, Write, Glob, Grep
---

# Generate Spec

Extract behavioral specifications from existing code using reverse-spec-generator.

## Overview

This command automatically analyzes source code files and generates formal BDD-style specifications that capture:

- **Entities** - Data structures and domain objects (classes, records, types)
- **Behaviors** - What the code does (methods, functions, operations)
- **Rules** - Business logic and decision rules
- **Constraints** - System limits, invariants, dependencies, timeouts

## How It Works

1. You provide source code file(s)
2. The tool analyzes the code and extracts patterns
3. Specifications are generated in `.spec` YAML format
4. Specs are automatically validated
5. You review and refine the generated specs

## Supported Languages

- **Python** - Classes, dataclasses, type hints, docstrings (Google/NumPy style)
- **Java** - Classes, interfaces, records, JavaDoc, annotations
- **JavaScript/TypeScript** - Classes, functions, JSDoc, TypeScript types
- **Generic** - Fallback pattern matching for other languages

## Generation Process

### What Gets Extracted

**Entities** (from classes, dataclasses, records):
- Class name and docstring
- Property/field names, types, and documentation
- Visibility and mutability information

**Behaviors** (from methods and functions):
- Method/function names and docstrings
- Parameters and return types
- Observable actions the code performs
- Examples from code comments

**Rules** (from logic and control flow):
- Guard clauses and assertions (raises exceptions)
- Conditional logic patterns
- Business rule comments in code
- Validation constraints

**Constraints** (from limits and dependencies):
- Named constants (MAX_, MIN_, TIMEOUT_, etc.)
- Timeout patterns (30s, 5000ms, etc.)
- Dependency annotations
- Invariant assertions

### Confidence Scoring

Extractions are ranked by confidence:
- **High (1.0)** - Documented in docstring/comments with full details
- **Medium (0.7)** - Extracted from code structure + partial documentation
- **Low (0.5)** - Inferred from naming or patterns only

Only high and medium confidence extractions are included by default.

## Usage

### Extract from a Single File

```
/generate-spec
```

Then provide the file path or content when prompted.

**Example:**
```
/generate-spec
# Select or paste: src/user_service.py
```

### Extract from Multiple Files

Specify one or more files to extract specs that integrate all entities, behaviors, and rules:

```
/generate-spec
# Files: src/auth.py src/user.py src/permissions.py
```

The tool will:
1. Extract from each file independently
2. Merge results (highest-confidence duplicates win)
3. Generate a single integrated `.spec` file
4. Validate the result

### Extract with Options

| Option | Default | Description |
|--------|---------|-------------|
| `confidence_threshold` | `0.5` | Minimum confidence score for inclusion (0.0–1.0) |
| `include_private` | `false` | Include private methods/fields in extraction |
| `output_path` | auto | Specify output file name (default: `<module>.spec`) |

Example:
```
/generate-spec
# Files: src/auth.py
# Options: confidence_threshold=0.6 include_private=false
```

## Output

Generated specs are written to `.spec` files in YAML format:

```yaml
version: "1.0"
module: "user_authentication"
description: "User authentication and session management service"

entities:
  - name: "User"
    description: "System user with credentials..."
    properties:
      - name: "id"
        type: "string"
        required: true
        description: "Unique user identifier"
      # ...

behaviors:
  - name: "authenticate_user"
    description: "User logs in with email and password..."
    given:
      - "user exists in system"
      - "credentials are valid"
    when:
      - "POST /auth/login is called"
    then:
      - "authentication token is returned"
    examples:
      - input: "email=user@example.com, password=secret"
        output: "token=abc123xyz"

rules:
  - name: "suspended_user_cannot_login"
    description: "Suspended users are denied authentication"
    condition: "when user status is suspended and login attempted"
    action: "then return 403 Forbidden"

constraints:
  - name: "session_timeout"
    description: "Sessions expire after 1 hour"
    type: "timeout"
    value: "3600s"
```

## Validation

After writing the `.spec` file, validate it before reporting completion. Run through this checklist against the file you just wrote:

- [ ] `version: "1.0"` is present at root
- [ ] `module` is snake_case, no spaces
- [ ] `description` is 10–500 characters
- [ ] Entity names are PascalCase (`User`, not `user` or `user_entity`)
- [ ] Behavior/rule/constraint names are snake_case
- [ ] Every behavior has at least one `given`, `when`, and `then` item
- [ ] All property `type` values are from: string, number, boolean, null, array, object
- [ ] Constraint `type` values are from: limit, invariant, dependency, timeout
- [ ] No `then` items describe implementation details (no SQL, no object references)
- [ ] Descriptions are non-empty (10+ characters) throughout

Fix any failures and re-read the file before completing.

## Best Practices

1. **Start with well-documented code** - Docstrings and comments improve extraction quality
2. **One module per file** - Generate specs for logical modules, not entire projects
3. **Review and refine** - Use `/amend` to improve generated specs
4. **Add examples** - Manually add concrete examples to behaviors
5. **Keep specs focused** - Remove behaviors that are internal implementation details

## Typical Workflow

1. **Generate** - Run `/generate-spec` on your code
2. **Review** - Look at the generated `.spec` file
3. **Validate** - Check that all entities, behaviors, and rules are captured
4. **Amend** - Use `/amend` to improve clarity and completeness
5. **Converge** - Use `/converge` to verify code matches spec
6. **Generate Tests** - Use `/generate-tests` to create test suite

## Language-Specific Details

### Python
- **Entities from:** `@dataclass`, `class` definitions
- **Behaviors from:** Methods with docstrings
- **Types from:** Type hints (`int`, `str`, `Optional[X]`, `List[T]`)
- **Rules from:** `if not X: raise ValueError()`
- **Constraints from:** Module-level `UPPER_CASE` constants

### Java
- **Entities from:** `class`, `record`, `interface` definitions
- **Behaviors from:** Methods with JavaDoc
- **Types from:** Type annotations, generics (`List<String>`)
- **Rules from:** `if (cond) { throw new Exception() }`
- **Constraints from:** `public static final` constants, `@Min`, `@Max` annotations

### JavaScript/TypeScript
- **Entities from:** `class`, TypeScript interfaces
- **Behaviors from:** Methods with JSDoc (`@param`, `@returns`)
- **Types from:** TypeScript types, JSDoc `@param {type}`
- **Rules from:** Guard clauses, throw statements
- **Constraints from:** `const UPPER_CASE` values, `setTimeout` patterns

## Troubleshooting

**No entities extracted:**
- Ensure code has classes or record definitions
- Check that docstrings are present
- Language might not be detected - try specifying explicitly

**Behaviors incomplete:**
- Add docstrings with parameter and return descriptions
- Behaviors are extracted from function/method signatures
- Add comments to clarify what complex functions do

**Rules not detected:**
- Add explicit guard clauses: `if (condition) throw`
- Add comments above rules to document them
- Some business logic may need manual documentation

**Spec validation fails:**
- Check field lengths (descriptions: 10-500 chars)
- Verify naming conventions (entities: PascalCase, others: snake_case)
- Ensure required fields are present

## Next Steps

After generating specs:
- **Refine:** Use `/amend` to improve clarity and completeness
- **Verify:** Use `/converge` to check code matches spec
- **Test:** Use `/generate-tests` to create tests from specs
- **Document:** Share specs as living documentation
