---
title: API Specification Validation Patterns
description: Advanced validation patterns, edge cases, and recovery strategies for spec validation
type: advanced
---

# API Specification Validation Patterns - Advanced Guide

## Overview

This guide provides advanced validation patterns for API specifications beyond the basic spec-validation-agent checks. Covers edge cases, complex scenarios, version compatibility, and recovery strategies.

---

## Part 1: OpenAPI 3.x Format Validation

**Only OpenAPI 3.x is supported.** RAML specifications are rejected immediately.

### OAS 3.x Format Detection

**Standard Case**:
```yaml
openapi: 3.0.3
info:
  title: User API
  version: 1.0.0
```

**Edge Case 1**: Different OpenAPI versions
```yaml
openapi: 3.1.0    # Latest version - VALID
openapi: 3.0.0    # Oldest v3 - VALID
openapi: 2.0      # Swagger 2.0 - REJECT (not OAS 3.x)
swagger: 2.0      # Alternative header - REJECT
```

**Validation Rule**:
- Reject if `openapi: "2.x"` or `swagger:` key present
- Reject if file starts with `#%RAML` — "RAML is not supported. Only OpenAPI 3.x is accepted."
- Accept if `openapi: "3.0.x"` or `openapi: "3.1.x"`
- Warn if version significantly different from target (3.0.3)

**Edge Case 2**: Missing or malformed version
```yaml
openapi: 3        # No minor version - WARN (should be 3.0.3 or 3.1.0)
openapi: 3.0.3.1  # Too many version parts - WARN
openapi: "3.0.3"  # Quoted version - VALID (still parses)
```

**Validation Rule**:
- Accept if major.minor.patch format
- Warn if simplified format (e.g., "3" without minor/patch)
- Reject if more than 3 version parts

---

## Part 2: Complex Type References and Circular Dependencies

### Circular Reference Detection

**Problematic Case**:
```yaml
components:
  schemas:
    User:
      type: object
      properties:
        profile:
          $ref: '#/components/schemas/Profile'
    
    Profile:
      type: object
      properties:
        user:
          $ref: '#/components/schemas/User'   # Circular!
```

**Detection Strategy**:
1. Build directed graph of type references
2. Use depth-first search (DFS) to detect cycles
3. Track visited nodes and recursion stack
4. Report cycle path: User → Profile → User

**Validation Action**:
- ✗ FAIL: Circular references prevent code generation
- Recommend: Break cycle with base type or interface
  ```yaml
  UserBase:
    type: object
    properties:
      id: string
  
  User:
    allOf:
      - $ref: '#/components/schemas/UserBase'
      - type: object
        properties:
          profile:
            $ref: '#/components/schemas/Profile'
  ```

### Self-Referencing Types

**Valid Case** (recursive array):
```yaml
TreeNode:
  type: object
  properties:
    value: string
    children:
      type: array
      items:
        $ref: '#/components/schemas/TreeNode'  # Self-reference OK
```

**Validation Rule**:
- ✓ PASS: Self-references in array items (enables recursive structures)
- ⚠ WARN: Self-references in direct properties (risky, requires careful generation)
- ✗ FAIL: Direct mutual references (A references B, B references A at same nesting level)

### Nested Reference Depth

**Problematic Case** (too deep):
```yaml
A → B → C → D → E → F → G  (7 levels deep)
```

**Validation Rule**:
- ⚠ WARN: Reference depth > 5 levels (impacts code readability)
- ✓ PASS: Reference depth ≤ 5 levels (manageable)
- Report: Max reference depth found and path to deepest

---

## Part 3: Constraint and Validation Conflicts

### Conflicting String Constraints

**Case 1**: Pattern conflicts with enum
```yaml
status:
  type: string
  enum: [active, inactive, pending]
  pattern: '^[A-Z]+$'      # Enum values are lowercase - CONFLICT!
```

**Detection**:
- Extract enum values: [active, inactive, pending]
- Extract pattern: `^[A-Z]+$` (uppercase only)
- Test if all enum values match pattern
- If not, report conflict

**Validation Action**:
- ✗ FAIL: Enum values don't match pattern
- Recommend: Align pattern with enum or remove conflicting constraint

**Case 2**: Length constraints conflict
```yaml
name:
  type: string
  minLength: 10
  maxLength: 5     # maxLength < minLength - CONFLICT!
```

**Detection**:
- Compare minLength vs maxLength
- Compare minLength vs enum values
- Compare maxLength vs minLength

**Validation Action**:
- ✗ FAIL: maxLength < minLength (impossible to satisfy)
- Report: "maxLength (5) must be ≥ minLength (10)"

### Conflicting Numeric Constraints

**Case 1**: Minimum > Maximum
```yaml
age:
  type: integer
  minimum: 100
  maximum: 50    # CONFLICT!
```

**Validation Action**:
- ✗ FAIL: minimum > maximum (impossible to satisfy)
- Report: "minimum (100) must be ≤ maximum (50)"

**Case 2**: Exclusive bounds conflict
```yaml
rating:
  type: number
  exclusiveMinimum: true
  minimum: 5
  exclusiveMaximum: true
  maximum: 5    # Exclusive min and max at same value - CONFLICT!
```

**Validation Action**:
- ✗ FAIL: exclusiveMinimum and exclusiveMaximum at same value
- Report: "Cannot have exclusiveMinimum and exclusiveMaximum at same value (5)"

### Array Item Constraints

**Case 1**: Array length conflicts
```yaml
tags:
  type: array
  minItems: 10
  maxItems: 5    # maxItems < minItems - CONFLICT!
```

**Validation Action**:
- ✗ FAIL: maxItems < minItems
- Report: "maxItems (5) must be ≥ minItems (10)"

**Case 2**: Item type conflicts
```yaml
values:
  type: array
  items:
    type: string
  default: [1, 2, 3]    # Numeric values, but items are strings - CONFLICT!
```

**Validation Action**:
- ⚠ WARN: Default values don't match item type
- Report: "Default array contains numbers but items are type string"

---

## Part 4: Naming Convention Edge Cases

### Reserved Java Keywords

**Problematic Names**:
```yaml
Person:
  type: object
  properties:
    class: string        # Java reserved word - FAIL
    package: string      # Java reserved word - FAIL
    int: integer         # Java reserved word - FAIL
    final: boolean       # Java reserved word - FAIL
```

**Full Reserved List**:
```
abstract, assert, boolean, break, byte, case, catch, char, class, const, 
continue, default, do, double, double, else, enum, extends, false, final, 
finally, float, for, goto, if, implements, import, instanceof, int, interface, 
long, native, new, null, package, private, protected, public, return, short, 
static, strictfp, super, switch, synchronized, this, throws, throw, transient, 
true, try, void, volatile, while
```

**Validation Action**:
- ✗ FAIL: Property or schema name is reserved word
- Recommend: Rename or prefix (e.g., `className`, `packageName`)

### CamelCase vs snake_case Conflicts

**Problematic Case**:
```yaml
properties:
  firstName: string    # camelCase
  first_name: string   # snake_case (different property!)
```

**Validation Rule**:
- ⚠ WARN: Mixed naming conventions detected
- ✓ PASS if consistent (all camelCase or all snake_case)
- Report: Properties using mixed conventions

### Space and Special Characters

**Problematic Names**:
```yaml
properties:
  "first name": string     # Space - FAIL
  "user-id": string        # Hyphen - FAIL
  "email@domain": string   # @ symbol - FAIL
```

**Validation Action**:
- ✗ FAIL: Property names contain spaces or special chars
- Recommend: Use camelCase without special characters

### Name Collisions After Conversion

**Problematic Case**:
```yaml
properties:
  firstName: string
  first_name: string      # Both convert to firstName in camelCase - COLLISION!
```

**Detection Strategy**:
- Convert all property names to target case (camelCase)
- Check for duplicates after conversion
- Report collisions

**Validation Action**:
- ✗ FAIL: Naming collisions after conversion
- Report: "firstName and first_name both convert to 'firstName'"

---

## Part 5: Response Code Mapping Edge Cases

### Missing Standard Responses

**Problematic Endpoint**:
```yaml
/users:
  post:
    responses:
      500: {}              # Only error response
      # Missing 201 Created!
```

**Validation Rule**:
- POST should have 200 or 201 response
- GET should have 200 response
- DELETE should have 200 or 204 response
- All methods should have some 2xx response

**Validation Action**:
- ✗ FAIL: No 2xx success response
- Recommend: Add 201 (Created) for POST, 200 (OK) for GET/PUT, 204 (No Content) for DELETE

### Unusual Response Code Patterns

**Case 1**: Multiple success responses with different content
```yaml
/orders:
  get:
    responses:
      200:
        schema: OrderList    # List of orders
      201:
        schema: Order        # Single order
```

**Validation Action**:
- ⚠ WARN: Multiple 2xx responses with different schemas
- Recommend: Use single 200 with consistent response type
- If intentional: document why (e.g., paginated vs single)

**Case 2**: Missing 404 for resource endpoints
```yaml
/users/{id}:
  get:
    responses:
      200: {}              # Success
      500: {}              # Error
      # Missing 404 Not Found!
```

**Validation Action**:
- ⚠ WARN: Resource endpoint missing 404 response
- Recommend: Add 404 (Not Found) for /users/{id} endpoints

**Case 3**: Missing 400 for mutation endpoints
```yaml
/users:
  post:
    responses:
      201: {}              # Created
      500: {}              # Error
      # Missing 400 Bad Request!
```

**Validation Action**:
- ⚠ WARN: POST/PUT/PATCH missing 400 (Bad Request) response
- Recommend: Add 400 for validation error scenarios

### Status Code Consistency

**Inconsistent Patterns**:
```yaml
/users:
  post:
    responses:
      201: {}          # Created

/posts:
  post:
    responses:
      200: {}          # OK (inconsistent - should be 201)
```

**Validation Action**:
- ⚠ WARN: Inconsistent response codes across endpoints
- Report: All POST endpoints should use 201 (Created)
- Recommend: Align all endpoints to standard patterns

---

## Part 6: Schema Completeness Checks

### Empty or Minimal Schemas

**Case 1**: Empty object
```yaml
EmptyResponse:
  type: object
  properties: {}      # No properties - problematic!
```

**Validation Action**:
- ⚠ WARN: Schema has no properties
- Consider: Is this intentional (e.g., no-content response)?
- Recommend: Add description explaining intentional emptiness

**Case 2**: Minimal with only description
```yaml
SuccessResponse:
  type: object
  description: Success response
  properties: {}      # No properties!
```

**Validation Action**:
- ⚠ WARN: Schema with description but no properties
- Recommend: Add at least a status or result field

### Required Field Validation

**Case 1**: Property in required array but not defined
```yaml
User:
  type: object
  properties:
    id: integer
    name: string
  required: [id, name, email]    # email not defined - ERROR!
```

**Validation Action**:
- ✗ FAIL: Required field "email" not defined in properties
- Report: Required fields that don't exist: [email]

**Case 2**: All fields required vs none required
```yaml
User:
  type: object
  properties:
    id: integer
    name: string
    email: string
  required: [id, name, email]    # All required - unusual
```

**Validation Action**:
- ⚠ WARN: All properties are required (unusual pattern)
- Consider: Are all fields truly required?

### Type Definition Completeness

**Case 1**: Array without item type
```yaml
tags:
  type: array
  # Missing items definition!
```

**Validation Action**:
- ✗ FAIL: Array type missing items definition
- Recommend: Add `items: {type: string}`

**Case 2**: Object with no properties definition
```yaml
metadata:
  type: object
  # Missing properties definition!
```

**Validation Action**:
- ⚠ WARN: Object type missing properties
- Recommend: Define properties or use additionalProperties

---

## Part 7: Security Scheme Validation

### Missing Security Requirements

**Case 1**: Security scheme defined but never used
```yaml
securitySchemes:
  bearerAuth:
    type: oauth2
    flows:
      implicit:
        authorizationUrl: https://example.com/oauth/authorize
        scopes:
          read: Read access
          write: Write access

paths:
  /users:
    get:
      # No securedBy - bearer auth not required!
```

**Validation Action**:
- ⚠ WARN: Security scheme defined but never referenced
- Report: Unused security schemes: [bearerAuth]

**Case 2**: Endpoint missing security
```yaml
securitySchemes:
  bearerAuth: {...}

paths:
  /users:
    get:
      securedBy: [bearerAuth]    # Secured
    post:
      # Missing securedBy!
```

**Validation Action**:
- ⚠ WARN: POST missing security while GET has it
- Recommend: Align security requirements across endpoint methods

### Invalid Security Scheme References

**Case 1**: Referenced scheme doesn't exist
```yaml
paths:
  /users:
    get:
      securedBy: [nonexistentAuth]    # Doesn't exist!
```

**Validation Action**:
- ✗ FAIL: Referenced security scheme not defined
- Report: Undefined security schemes: [nonexistentAuth]

### Security Scope Validation

**Case 1**: Required scope not defined
```yaml
securitySchemes:
  oauth2:
    type: oauth2
    flows:
      implicit:
        scopes:
          read: Read access

paths:
  /admin:
    get:
      securedBy:
        - oauth2: [admin]    # Scope "admin" not defined!
```

**Validation Action**:
- ✗ FAIL: Required scope "admin" not defined in securityScheme
- Report: Undefined scopes in oauth2: [admin]

---

## Part 8: Producer and Consumer Alignment

### Multiple Consumer Specs

**Scenario**: Application has multiple consumer specs (different API versions)

**Validation**:
- Verify no endpoint path conflicts
- Verify no operation ID conflicts
- Warn if different authentication schemes
- Recommend: Use API versioning in path (/v1/users vs /v2/users)

### Producer Spec Compatibility

**Scenario**: Multiple producers, checking compatibility

**Validation Checks**:
1. All producer endpoints have baseUri
2. All producer response codes are defined
3. All producer schemas are complete
4. No conflicts in model naming between producers

**Conflict Resolution**:
- Recommend: Prefix client models by producer name
  - PaymentServicePaymentRequest
  - ShippingServiceShippingRequest

---

## Part 9: Real-World Validation Examples

### Example 1: E-Commerce API Spec Validation

```yaml
openapi: 3.0.3
info:
  title: E-Commerce API
  version: 1.0.0

paths:
  /products:
    get:
      responses:
        200:
          schema: ProductList    # OK
        
  /orders:
    post:
      requestBody:
        schema: CreateOrderRequest
      responses:
        201:
          schema: Order          # OK
        400: {}                    # OK

components:
  schemas:
    Product:
      type: object
      properties:
        id: string
        name: string
        price:
          type: number
          minimum: 0             # OK
          maximum: 999999
      required: [id, name, price]
    
    Order:
      type: object
      properties:
        id: string
        products:
          type: array
          items:
            $ref: '#/components/schemas/Product'
        status:
          type: string
          enum: [pending, confirmed, shipped, delivered]
      required: [id, products, status]

    CreateOrderRequest:
      type: object
      properties:
        productIds: 
          type: array
          items:
            type: string
        shippingAddress:
          $ref: '#/components/schemas/Address'
      required: [productIds]
    
    Address:
      type: object
      properties:
        street: string
        city: string
        zipCode: string
      required: [street, city]
```

**Validation Results**:
- ✓ Format: Valid OAS 3.0.3
- ✓ Root fields: Complete
- ✓ Endpoints: Valid structure
- ✓ Response codes: Logical (200, 201, 400)
- ✓ Schemas: Complete and valid
- ✓ Type references: All exist
- ✓ No circular references
- ✓ Naming: PascalCase schemas, camelCase properties
- ✓ Constraints: Valid (price minimum=0, maximum=999999)
- Status: **VALID** ✓

### Example 2: Failed Validation Scenario

```yaml
openapi: 3.0.3
info:
  title: Broken API
  version: 1.0        # ERROR: Missing patch version

paths:
  /users:
    get:
      responses:
        # ERROR: Missing 200 success response
        500: {}
  
  /orders/{id}:
    get:
      responses:
        200: {}
        # WARNING: Missing 404 Not Found

components:
  schemas:
    User:
      type: object
      properties:
        class: string         # ERROR: Reserved Java keyword
        name: string
      required: [class, name, email]  # ERROR: email not in properties
    
    Order:
      type: object
      properties:
        items:
          type: array
          # ERROR: Missing items definition
      required: [items]
    
    Address:
      type: object
      properties:
        user:
          $ref: '#/components/schemas/UserProfile'
    
    UserProfile:
      type: object
      properties:
        address:
          $ref: '#/components/schemas/Address'  # ERROR: Circular reference!
```

**Validation Results**:
- ✗ Root fields: Version missing patch
- ✗ Endpoints: GET /users missing 200 response
- ⚠ Endpoints: GET /orders/{id} missing 404 response
- ✗ Schema: "class" is reserved Java keyword
- ✗ Schema: Required field "email" not defined
- ✗ Schema: Array missing items definition
- ✗ Schema: Circular reference User ↔ UserProfile
- Status: **ERRORS FOUND** ✗ (Fix required before generation)

---

## Part 10: Recovery and Remediation

### How to Fix Common Validation Errors

**Error 1: Reserved Java Keyword**

Before:
```yaml
properties:
  class: string
  package: string
```

After:
```yaml
properties:
  className: string
  packageName: string
```

**Error 2: Circular References**

Before:
```yaml
User:
  properties:
    profile:
      $ref: '#/components/schemas/UserProfile'

UserProfile:
  properties:
    user:
      $ref: '#/components/schemas/User'
```

After:
```yaml
UserBase:
  type: object
  properties:
    id: string

User:
  allOf:
    - $ref: '#/components/schemas/UserBase'
    - type: object
      properties:
        profile:
          $ref: '#/components/schemas/UserProfile'

UserProfile:
  type: object
  properties:
    username: string
    # No reference back to User
```

**Error 3: Missing Required Fields in Definition**

Before:
```yaml
User:
  type: object
  properties:
    id: string
    name: string
  required: [id, name, email]  # ERROR: email not defined
```

After:
```yaml
User:
  type: object
  properties:
    id: string
    name: string
    email: string
  required: [id, name, email]  # OK
```

---

**Version**: 1.0.0  
**Authority**: Advanced validation patterns for spec-validation-agent  
**Last Updated**: 2026-06-13
