---
name: generate-tests
description: Generate comprehensive test suites from BDD-style behavioral specifications — covers behaviors, rules, and constraints across pytest, JUnit 5, and Jest.
agent: reverse-spec-generator-agent
allowed-tools: Read, Write, Bash
---

# Generate Tests

Generate comprehensive test suites from BDD-style behavioral specifications.

## Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `spec_file` | path | yes | — | Path to .spec file to generate tests from |
| `--framework` | enum | no | auto-detect | Test framework: `pytest`, `junit5`, `jest` |
| `--behavior` | string | no | all | Generate tests for specific behavior only |
| `--output` | path | no | `tests/` | Directory to write generated test files |
| `--style` | enum | no | `bdd` | Test style: `bdd` (Given/When/Then) or `unit` (Arrange/Act/Assert) |

## Overview

After creating and refining specifications with `/generate-spec` and `/amend`, use this command to:

- **Generate test cases** from behaviors, rules, and constraints
- **Create BDD test suites** that validate spec compliance
- **Integrate with test frameworks** (pytest, Jest, JUnit, etc.)
- **Ensure coverage** of all specified behaviors and rules
- **Maintain alignment** between specs and tests

## How It Works

1. You provide a `.spec` file
2. The tool generates test cases for each behavior, rule, and constraint
3. Tests are written in your target framework
4. Each test validates one aspect of the specification
5. Tests are organized logically and can be run immediately

## Test Generation Strategy

### For Each Behavior

Generate tests for:
- ✓ **Happy path** - All preconditions met, expected outcome occurs
- ✓ **Precondition failures** - Missing required preconditions
- ✓ **Examples** - Concrete test cases from behavior examples
- ✓ **Edge cases** - Boundary conditions and special values

**Example Behavior:**
```yaml
behaviors:
  - name: "create_user"
    description: "Create a new user account with valid email and password"
    given:
      - "user does not already exist"
      - "email format is valid"
      - "password meets requirements"
    when:
      - "POST /users endpoint is called"
      - "email and password are provided"
    then:
      - "new user is created in database"
      - "response status is 201 Created"
      - "user ID is returned"
    examples:
      - input: '{"email": "new@example.com", "password": "SecurePass123!"}'
        output: '{"id": "uuid-123", "email": "new@example.com", "status": "active"}'
```

**Generated Tests:**
```python
def test_create_user_happy_path():
    """Create a new user with valid credentials"""
    response = create_user(email="new@example.com", password="SecurePass123!")
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert "id" in response.json()

def test_create_user_invalid_email():
    """Fail when email format is invalid"""
    response = create_user(email="not-an-email", password="SecurePass123!")
    assert response.status_code == 400

def test_create_user_user_already_exists():
    """Fail when user already exists"""
    create_user(email="existing@example.com", password="SecurePass123!")
    response = create_user(email="existing@example.com", password="SecurePass123!")
    assert response.status_code == 409
```

### For Each Rule

Generate tests that:
- ✓ Verify rule condition is detected
- ✓ Verify correct action is taken
- ✓ Verify boundary conditions

### For Each Constraint

Generate tests that verify:
- ✓ Limits are enforced (max values, lengths)
- ✓ Invariants are maintained (uniqueness, relationships)
- ✓ Dependencies are handled (error if not available)
- ✓ Timeouts are respected (operations complete in time)

## Supported Test Frameworks

- **Python:** pytest, unittest
- **Java:** JUnit 5, TestNG
- **JavaScript/TypeScript:** Jest, Mocha, Vitest
- **Generic:** Framework-agnostic test descriptions

## Usage

### Generate Tests from Spec

```
/generate-tests
# Spec file: user_service.spec
# Framework: pytest (or: jest, junit, unittest, etc.)
# Output directory: tests/
```

### Generate for Specific Behavior

```
/generate-tests
# Spec file: user_service.spec
# Behavior: authenticate_user
# Framework: pytest
```

## Output Structure

Generated tests are organized by section:

```
tests/
├── test_user_service_behaviors.py    # Tests for behaviors
├── test_user_service_rules.py        # Tests for business rules
├── test_user_service_constraints.py  # Tests for constraints
└── test_user_service_integration.py  # End-to-end tests
```

## Test Quality

Generated tests follow best practices:

- ✓ **AAA Pattern** - Arrange, Act, Assert
- ✓ **Single Responsibility** - Each test verifies one thing
- ✓ **Clear Names** - Test name describes what's tested
- ✓ **Independent** - Tests can run in any order
- ✓ **Reproducible** - Same result every time
- ✓ **Fast** - Quick execution (use mocks where appropriate)

## Integration with CI/CD

Generated tests can be immediately integrated:

```bash
# Run all generated tests
pytest tests/test_user_service_*.py

# Run with coverage
pytest tests/ --cov=src/ --cov-report=html

# Run in CI/CD pipeline
pytest tests/ -v --junit-xml=results.xml
```

## Test Coverage

Generated tests provide coverage for:

| Aspect | Coverage |
|--------|----------|
| Behaviors | All happy paths + precondition failures |
| Rules | All rule conditions and actions |
| Constraints | Limit boundaries, invariants, dependencies |
| Examples | All concrete examples from spec |
| Edge cases | Boundary values, special cases |

## Workflow

1. **Generate spec** - `/generate-spec`
2. **Refine spec** - `/amend` 
3. **Verify alignment** - `/converge`
4. **Generate tests** - `/generate-tests`
5. **Run tests** - `/run-tests`
6. **Fix failures** - Update code to pass tests
7. **Maintain** - Keep tests and spec synchronized

## Tips for Generated Tests

1. **Review generated tests** - Ensure they match your expectations
2. **Run tests first** - Verify they work before modifying
3. **Test against actual code** - Not just mocks
4. **Maintain tests** - Keep in sync with spec changes
5. **Add custom tests** - For scenarios not in spec

## Troubleshooting

**Tests are too generic:**
- Add more details to spec with `/amend`
- Include concrete examples in behaviors
- Run `/generate-tests` again after amending

**Tests don't match my code:**
- Run `/converge` to check alignment
- Update spec or code based on findings
- Regenerate tests

**Tests are failing:**
- This is good! Tests catch mismatches
- Either fix code to match spec
- Or update spec if code is correct
- Use `/amend` to clarify spec

## Run Generated Tests

After writing the test files, run them immediately to establish a baseline in `.convergence.yaml`. Auto-detect the framework and run the suite:

```bash
# Python
pytest <test-file> -v

# Java (Gradle)
./gradlew test

# JavaScript/TypeScript
npx jest <test-file>
```

Failures are expected at this point — they represent the implementation gap the convergence loop will close. The important thing is that the tests execute and results are recorded.

Update `.convergence.yaml` with the results using `python src/test_runner.py` or by running `/run-tests`.

## Next Steps

After generating tests:
- **Run tests** - Use `/run-tests` to execute and feed results into convergence state
- **Fix failures** - Update code to pass tests
- **Add CI/CD** - Integrate tests into pipeline
- **Measure coverage** - Track spec and code coverage
