---
name: amend
description: Edit and refine behavioral specifications to improve clarity, completeness, and accuracy. Marks amended behaviors as spec-led in the convergence state.
agent: reverse-spec-generator-agent
allowed-tools: Read, Edit, Write, Grep
---

# Amend

Edit and refine behavioral specifications to improve clarity, completeness, and accuracy.

## Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `spec_file` | path | yes | — | Path to .spec file to amend |
| `amendment` | string | yes | — | Description of what to change (natural language) |
| `--behavior` | string | no | all | Target specific behavior by name |
| `--add-example` | flag | no | off | Add concrete input/output example to behavior |
| `--mark-spec-led` | flag | no | on | Mark amended behaviors as spec-led in convergence |

## Overview

After generating specifications with `/generate-spec`, use this command to:

- **Improve descriptions** - Add clarity and detail to specifications
- **Add examples** - Include concrete input/output examples for behaviors
- **Fix extraction errors** - Correct mistakes from automatic generation
- **Complete specs** - Add behaviors or rules that were missed
- **Enhance documentation** - Elaborate on complex behaviors, rules, or constraints

## Common Amendments

### 1. Improve Behavior Descriptions

**Before:**
```yaml
behaviors:
  - name: "authenticate_user"
    description: "Executes authenticate_user operation"
    given: ["user exists"]
    when: ["credentials provided"]
    then: ["token returned"]
```

**After:**
```yaml
behaviors:
  - name: "authenticate_user"
    description: "User authenticates using email and password to obtain session token"
    given:
      - "user account exists in system"
      - "user account is in active status"
      - "email and password combination is correct"
    when:
      - "POST /api/auth/login endpoint is called"
      - "credentials are validated against stored hash"
    then:
      - "JSON Web Token (JWT) is generated with 1-hour expiration"
      - "token is returned in response body"
      - "HTTP 200 OK response is sent"
    examples:
      - input: '{"email": "user@example.com", "password": "secret123"}'
        output: '{"token": "eyJhbGciOiJIUzI1NiIs..."}'
        description: "Successful login"
      - input: '{"email": "user@example.com", "password": "wrong"}'
        output: '{"error": "Invalid credentials"}'
        description: "Failed login with wrong password"
```

### 2. Add Missing Rules

**Check if the spec captures:**
- ✓ Access control rules (who can do what?)
- ✓ Validation rules (input constraints)
- ✓ State transition rules (what states are valid?)
- ✓ Business logic rules (special cases, discounts, limits)

**Example addition:**
```yaml
rules:
  - name: "suspended_users_cannot_authenticate"
    description: "Users with suspended status are prevented from logging in"
    condition: "when user status is 'suspended' and login is attempted"
    action: "then return HTTP 403 Forbidden with error message"

  - name: "failed_login_attempts_blocked"
    description: "After 5 failed attempts, account is temporarily locked"
    condition: "when failed_login_count >= 5"
    action: "then lock account for 15 minutes and reject further attempts"
```

### 3. Add Missing Constraints

**Check if the spec includes:**
- ✓ Limits (max/min values, lengths, counts)
- ✓ Invariants (properties that must always be true)
- ✓ Dependencies (external services required)
- ✓ Timeouts (time-based constraints)

**Example addition:**
```yaml
constraints:
  - name: "password_minimum_length"
    description: "Passwords must be at least 12 characters"
    type: "limit"
    value: "12"

  - name: "email_uniqueness"
    description: "No two users can have the same email address"
    type: "invariant"
    value: "database has UNIQUE constraint on email column"

  - name: "api_gateway_required"
    description: "Authentication requires API Gateway to be running"
    type: "dependency"
    value: "api-gateway service must be healthy"

  - name: "login_timeout"
    description: "Login request must complete within 5 seconds"
    type: "timeout"
    value: "5s"
```

### 4. Add Missing Entities

If the spec references entities that aren't defined, add them:

```yaml
entities:
  - name: "AuthToken"
    description: "Session token returned after successful authentication"
    properties:
      - name: "token"
        type: "string"
        required: true
        description: "JWT token value"
      - name: "expires_at"
        type: "number"
        required: true
        description: "Unix timestamp when token expires"
      - name: "token_type"
        type: "string"
        required: true
        description: "Token type (always 'Bearer')"
        default: "Bearer"
```

### 5. Fix Naming Conventions

**Entity names** → PascalCase:
```yaml
# ✓ Correct
entities:
  - name: "User"
  - name: "AuthToken"
  - name: "PermissionRole"

# ✗ Incorrect
# - name: "user" (should be "User")
# - name: "auth_token" (should be "AuthToken")
```

**Behavior/Rule/Constraint names** → snake_case:
```yaml
# ✓ Correct
behaviors:
  - name: "authenticate_user"
  - name: "create_user_account"
  
rules:
  - name: "inactive_user_cannot_login"
  
constraints:
  - name: "max_concurrent_sessions"

# ✗ Incorrect
# - name: "AuthenticateUser" (should be "authenticate_user")
# - name: "inactiveUserCannotLogin" (should be "inactive_user_cannot_login")
```

## How to Amend

### Using Claude Code

1. Open the `.spec` file you want to edit
2. Run `/amend`
3. Describe what you want to improve

**Example:**
```
/amend
# File: user_service.spec
# Change: Add more detailed "given" conditions to authenticate_user behavior
# Reason: Generated version is too generic, needs to capture all preconditions
```

### Manual Editing

Directly edit the `.spec` file in your editor:
1. Open file in Claude Code
2. Make changes directly
3. Save file (validation runs automatically)
4. Review any validation errors and fix

### Review for Completeness

Use this checklist:

**For each Behavior:**
- ✓ Description is 20+ characters and clearly explains what happens
- ✓ `given` list has at least 2 items (preconditions)
- ✓ `when` list is clear and specific
- ✓ `then` list describes actual outcomes (not implementation)
- ✓ Examples show concrete input/output pairs (optional but recommended)

**For each Rule:**
- ✓ Description is clear and explains the business logic
- ✓ `condition` is specific and testable
- ✓ `action` describes what happens when condition is true

**For each Constraint:**
- ✓ Type is correct (limit/invariant/dependency/timeout)
- ✓ Value is specific and measurable
- ✓ Description explains why the constraint exists

**For each Entity:**
- ✓ All properties have descriptions (10+ characters)
- ✓ Types are correct and from allowed set
- ✓ Properties that can be null have `required: false`
- ✓ Default values are reasonable

## Amendment Workflow

1. **Generate** - Run `/generate-spec` on your code
2. **Review** - Read through the generated `.spec`
3. **Identify gaps** - What's missing or unclear?
4. **Amend** - Use this command to improve the spec
5. **Validate** - Fix any validation errors
6. **Iterate** - Repeat until spec is complete and clear
7. **Converge** - Use `/converge` to verify code matches
8. **Generate Tests** - Use `/generate-tests` for test suite

## Validation

After saving amendments, validate the spec before reporting completion. Run through this checklist against the file you just edited:

- [ ] `version: "1.0"` is present at root
- [ ] `module` is snake_case, no spaces
- [ ] `description` is 10–500 characters
- [ ] Entity names are PascalCase (`User`, not `user` or `user_entity`)
- [ ] Behavior/rule/constraint names are snake_case
- [ ] Every behavior has at least one `given`, `when`, and `then` item
- [ ] All property `type` values are from: string, number, boolean, null, array, object
- [ ] Constraint `type` values are from: limit, invariant, dependency, timeout
- [ ] No `then` items describe implementation details
- [ ] Descriptions are non-empty (10+ characters) throughout

Treat any failure as a blocker — fix and re-read the file before completing.

## Tips for Good Specs

1. **Be specific** - Describe observable behavior, not implementation
2. **Use examples** - Concrete examples clarify complex behaviors
3. **Document assumptions** - In descriptions and rules
4. **Keep it focused** - One responsibility per behavior
5. **Be concise** - Clear and detailed, but not verbose
6. **Check for completeness** - Can someone implement from this spec?

## Common Issues

**"Description is too short"**
- Minimum 10 characters
- Make descriptions more specific: "user_authentication" → "User authenticates with email and password"

**"Invalid naming convention"**
- Entities: `PascalCase` (User, AuthToken)
- Behaviors/Rules/Constraints: `snake_case` (authenticate_user)

**"Missing entity definition"**
- Add the entity to the `entities` section
- Or rename to refer to an existing entity

**"Incomplete behavior"**
- Add at least one `given`, `when`, and `then` clause
- Add examples to clarify complex behaviors

---

## Marking Intent: Amending Makes the Spec the Source of Truth

When you amend a behavior, you are stating that the **spec now leads** — the code must catch up, not the other way around.

Every time `/amend` modifies a behavior, rule, or constraint, it writes `source_of_truth: spec` for that item into the `.convergence.yaml` state file alongside the spec.

```yaml
# .convergence.yaml (written automatically by /amend)
behaviors:
  delete_event_log:
    source_of_truth: "spec"   # ← set by /amend
    divergence_status: "diverged"
```

This signal is picked up by `/converge` on the next run. Instead of defaulting to "code leads" for that divergence, it will report:

```
  truth  : spec  (spec leads → update code)
  action : Implement the behavior in code, or remove from spec if no longer required
```

And `/implement` will generate a code stub for it.

### When source_of_truth is NOT automatically set

If you amend purely cosmetic things (typos, description wording, adding examples without changing the behavioral contract), the source_of_truth is **not** changed — the divergence classification remains as-is.

The trigger is: **did the given/when/then or condition/action contract change?** If yes → `source_of_truth: spec`. If no → unchanged.

### Reverting an amendment

To revert a behavior back to code-led, edit `.convergence.yaml` directly and set `source_of_truth: "code"` for that item. Run `/converge` to recompute.

---

## Next Steps

After amending specs:
- **Verify:** Use `/converge` to ensure code matches spec
- **Implement:** Use `/implement` for behaviors now marked source_of_truth=spec
- **Test:** Use `/generate-tests` to create test suite
- **Share:** Distribute `.spec` files as documentation
