---
name: typescript-fix-patterns
description: "TypeScript Type Safety Security Patterns — Provide TypeScript-specific type safety patterns for applying CWE remediations in TypeScript codebases. This skill is composed with CWE-specific remediation skills to leverage TypeScript's type system"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/language_patterns_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# TypeScript Type Safety Security Patterns
## Quick Start

This skill provides language-specific fix patterns for applying CWE remediations in a target programming language.

```
# Loaded by detox-fix-agent based on the detected programming language.
# Provides language-idiomatic fix patterns for each CWE type.
```



## Purpose

Provide TypeScript-specific type safety patterns for applying CWE remediations in TypeScript codebases. This skill is composed with CWE-specific remediation skills to leverage TypeScript's type system as a compile-time security enforcement mechanism. It covers strict mode configuration, branded types for validated input, discriminated unions for structured error handling, runtime validation with Zod and io-ts, and type guards for security-sensitive operations. These patterns ensure that security invariants are enforced both at compile time (via the type system) and at runtime (via validation libraries).

## Inputs

- **cwe_id** (required, string): The CWE identifier being remediated (e.g., `CWE-89`, `CWE-79`).
- **vulnerability** (required, JSON object): The normalized vulnerability object from the CWE skill, containing `file_path`, `line_number`, and `code_snippet`.
- **framework** (optional, string): The framework in use (`express`, `nestjs`, `next`, `react`, `angular`). Auto-detected from imports and project structure if not provided.
- **validation_library** (optional, string): The preferred runtime validation library (`zod`, `io-ts`, `yup`, `class-validator`). Auto-detected from project dependencies if not provided.
- **tsconfig_strict** (optional, boolean): Whether TypeScript strict mode is enabled. Auto-detected from `tsconfig.json` if not provided.

## Steps

1. **Detect TypeScript configuration and framework.**
   - Use `Glob` to find `tsconfig.json`.
   - Use `Read` to examine `tsconfig.json` for `strict`, `strictNullChecks`, `noImplicitAny`, and other relevant compiler options.
   - Use `Read` to examine `package.json` for framework dependencies and existing validation libraries.

2. **Evaluate strict mode status.**
   - If `strict: true` is not enabled, recommend enabling it and note the recommendation in the output.
   - At minimum, the fix patterns require `strictNullChecks: true` and `noImplicitAny: true`.

3. **Select the appropriate type safety pattern based on CWE.**
   - Match the CWE ID to the relevant pattern section below.
   - Choose the framework-specific and validation-library-specific variant.

4. **Apply the fix using the patterns defined below.**
   - Use `Edit` to apply the code transformation.
   - Add required imports at the top of the file.
   - Add type definitions in a types file if the project follows that convention.

5. **Verify type correctness.**
   - Ensure the fix introduces no `any` types unless the original code uses them.
   - Ensure all type assertions (`as`) are justified and minimized.
   - Verify that branded types and type guards are used correctly.

6. **Scan for similar patterns.**
   - Use `Grep` to find other instances of the same vulnerable pattern in the project.
   - Apply the same type safety pattern consistently.

---

## Fix Patterns

### Strict Mode Configuration

#### Enabling Strict TypeScript

**When to use:** As a prerequisite for all type-safety-based security patterns. CWE-20 (Improper Input Validation), general security hardening.

**Before (vulnerable -- lax tsconfig):**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "outDir": "./dist"
  }
}
```

**After (fixed):**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "outDir": "./dist",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noPropertyAccessFromIndexSignature": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

**What `strict: true` enables:**
- `strictNullChecks` -- prevents `null`/`undefined` from being assignable to all types. Catches null pointer dereferences at compile time.
- `noImplicitAny` -- requires explicit type annotations where TypeScript cannot infer types. Prevents accidentally untyped values.
- `strictFunctionTypes` -- enforces contravariant function parameter checking.
- `strictBindCallApply` -- type-checks `bind`, `call`, and `apply`.
- `strictPropertyInitialization` -- requires class properties to be initialized.
- `useUnknownInCatchVariables` -- makes `catch` variables `unknown` instead of `any`.

**Key points:**
- `strict: true` is the single most impactful configuration for type safety.
- `noUncheckedIndexedAccess` adds `undefined` to index signature returns, preventing unsafe assumptions about array/object access.
- Enabling strict mode on an existing project may produce many errors. Recommend incremental adoption if the project is large.

---

### Branded Types for Validated Input

#### Creating Branded Types

**When to use:** CWE-20 (Input Validation), CWE-89 (SQL Injection), CWE-79 (XSS) -- to ensure that only validated data flows into security-sensitive operations.

**Concept:** Branded types use TypeScript's structural type system to create nominal types that can only be constructed through validation functions. This makes it a compile-time error to pass unvalidated input to functions that expect validated input.

**Define branded types:**
```typescript
// types/branded.ts

declare const __brand: unique symbol;

type Brand<T, B extends string> = T & { readonly [__brand]: B };

// Branded string types for validated input
export type SanitizedHtml = Brand<string, 'SanitizedHtml'>;
export type ValidatedEmail = Brand<string, 'ValidatedEmail'>;
export type ValidatedUsername = Brand<string, 'ValidatedUsername'>;
export type SafeSqlParam = Brand<string, 'SafeSqlParam'>;
export type ValidatedUrl = Brand<string, 'ValidatedUrl'>;
export type HashedPassword = Brand<string, 'HashedPassword'>;

// Branded number types
export type PositiveInt = Brand<number, 'PositiveInt'>;
export type UserId = Brand<number, 'UserId'>;
```

**Validation functions that produce branded types:**
```typescript
// validation/validators.ts
import type { ValidatedEmail, ValidatedUsername, ValidatedUrl, PositiveInt } from '../types/branded';

const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
const USERNAME_REGEX = /^[a-zA-Z0-9_]{3,50}$/;

export function validateEmail(input: string): ValidatedEmail {
  const trimmed = input.trim().toLowerCase();
  if (!EMAIL_REGEX.test(trimmed)) {
    throw new ValidationError('Invalid email format');
  }
  return trimmed as ValidatedEmail;
}

export function validateUsername(input: string): ValidatedUsername {
  const trimmed = input.trim();
  if (!USERNAME_REGEX.test(trimmed)) {
    throw new ValidationError('Username must be 3-50 alphanumeric characters or underscores');
  }
  return trimmed as ValidatedUsername;
}

export function validateUrl(input: string): ValidatedUrl {
  try {
    const parsed = new URL(input);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      throw new ValidationError('Only HTTP and HTTPS URLs are allowed');
    }
    return parsed.href as ValidatedUrl;
  } catch {
    throw new ValidationError('Invalid URL format');
  }
}

export function validatePositiveInt(input: unknown): PositiveInt {
  const num = Number(input);
  if (!Number.isInteger(num) || num <= 0) {
    throw new ValidationError('Must be a positive integer');
  }
  return num as PositiveInt;
}

class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}
```

**Using branded types in security-sensitive functions:**
```typescript
// Now these functions can ONLY be called with validated input
function queryUserByEmail(email: ValidatedEmail): Promise<User | null> {
  return db.query('SELECT * FROM users WHERE email = ?', [email]);
}

function setProfileLink(element: HTMLAnchorElement, url: ValidatedUrl): void {
  element.href = url;
}

function renderUserContent(html: SanitizedHtml): string {
  return `<div class="content">${html}</div>`;
}
```

**Key points:**
- Branded types have zero runtime cost -- they exist only at compile time.
- The `as BrandedType` cast should only appear inside validation functions, never at call sites.
- If a developer tries to pass a raw `string` to a function expecting `ValidatedEmail`, TypeScript reports a compile-time error.
- Combine branded types with runtime validation (Zod, io-ts) for comprehensive safety.

---

### Discriminated Unions for Error Handling

#### Result Type Pattern

**When to use:** CWE-200 (Information Exposure), CWE-209 (Error Message Leak), CWE-755 (Improper Exception Handling) -- to enforce structured error handling that prevents information leakage.

**Define a Result type:**
```typescript
// types/result.ts

type Success<T> = {
  readonly success: true;
  readonly data: T;
};

type Failure<E> = {
  readonly success: false;
  readonly error: E;
};

export type Result<T, E = AppError> = Success<T> | Failure<E>;

// Factory functions
export function ok<T>(data: T): Success<T> {
  return { success: true, data };
}

export function fail<E>(error: E): Failure<E> {
  return { success: false, error };
}
```

**Structured error types:**
```typescript
// types/errors.ts

export type AppError =
  | { code: 'VALIDATION_ERROR'; message: string; field?: string }
  | { code: 'NOT_FOUND'; resource: string }
  | { code: 'UNAUTHORIZED'; message: string }
  | { code: 'FORBIDDEN'; message: string }
  | { code: 'INTERNAL_ERROR'; internalMessage: string };

// Map errors to HTTP responses without leaking internal details
export function toHttpResponse(error: AppError): { status: number; body: object } {
  switch (error.code) {
    case 'VALIDATION_ERROR':
      return { status: 400, body: { error: error.code, message: error.message } };
    case 'NOT_FOUND':
      return { status: 404, body: { error: error.code, message: `${error.resource} not found` } };
    case 'UNAUTHORIZED':
      return { status: 401, body: { error: error.code, message: 'Authentication required' } };
    case 'FORBIDDEN':
      return { status: 403, body: { error: error.code, message: 'Access denied' } };
    case 'INTERNAL_ERROR':
      // Never expose internalMessage to the client
      return { status: 500, body: { error: error.code, message: 'An unexpected error occurred' } };
  }
}
```

**Usage in service layer:**
```typescript
async function getUser(id: UserId): Promise<Result<User>> {
  try {
    const user = await db.findUser(id);
    if (!user) {
      return fail({ code: 'NOT_FOUND', resource: 'User' });
    }
    return ok(user);
  } catch (err) {
    console.error('Database error in getUser:', err);
    return fail({ code: 'INTERNAL_ERROR', internalMessage: String(err) });
  }
}

// In the route handler -- TypeScript forces you to handle both cases
app.get('/api/users/:id', async (req, res) => {
  const idResult = validatePositiveInt(req.params.id);
  const result = await getUser(idResult);

  if (result.success) {
    return res.json(result.data);
  }

  const { status, body } = toHttpResponse(result.error);
  return res.status(status).json(body);
});
```

**Key points:**
- The discriminated union (`success: true | false`) forces callers to check the result before accessing `.data`.
- Internal error details (stack traces, SQL errors) are captured in `internalMessage` but never sent to the client.
- TypeScript's exhaustiveness checking (via `switch` on the `code` field) ensures all error types are handled.
- This pattern replaces try/catch blocks that might accidentally expose error details.

---

### Runtime Validation with Zod

#### Schema-Based Request Validation

**When to use:** CWE-20 (Input Validation), CWE-89 (SQL Injection boundary), CWE-79 (XSS boundary) -- to validate all external input at the boundary of the application.

**Define schemas:**
```typescript
import { z } from 'zod';

// User creation schema
export const CreateUserSchema = z.object({
  username: z.string()
    .min(3, 'Username must be at least 3 characters')
    .max(50, 'Username must be at most 50 characters')
    .regex(/^[a-zA-Z0-9_]+$/, 'Username must be alphanumeric'),
  email: z.string()
    .email('Invalid email address')
    .transform(val => val.toLowerCase().trim()),
  age: z.number()
    .int('Age must be an integer')
    .min(13, 'Minimum age is 13')
    .max(150, 'Invalid age'),
  role: z.enum(['user', 'moderator', 'admin']).default('user'),
});

// Infer the TypeScript type from the schema
export type CreateUserInput = z.infer<typeof CreateUserSchema>;
// { username: string; email: string; age: number; role: 'user' | 'moderator' | 'admin' }

// Query parameter schema
export const SearchQuerySchema = z.object({
  q: z.string().min(1).max(200).trim(),
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  sort: z.enum(['name', 'date', 'relevance']).default('relevance'),
});
```

**Express middleware for Zod validation:**
```typescript
import { z, ZodSchema } from 'zod';
import { Request, Response, NextFunction } from 'express';

function validateBody<T extends ZodSchema>(schema: T) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        details: result.error.issues.map(i => ({
          field: i.path.join('.'),
          message: i.message,
        })),
      });
    }
    req.body = result.data; // Replace with validated and transformed data
    next();
  };
}

function validateQuery<T extends ZodSchema>(schema: T) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.query);
    if (!result.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        details: result.error.issues.map(i => ({
          field: i.path.join('.'),
          message: i.message,
        })),
      });
    }
    req.query = result.data;
    next();
  };
}

// Usage:
app.post('/api/users', validateBody(CreateUserSchema), async (req, res) => {
  // req.body is typed as CreateUserInput and validated
  const user = await userService.create(req.body);
  res.status(201).json(user);
});
```

#### Runtime Validation with io-ts

**When to use:** When the project already uses io-ts or fp-ts.

```typescript
import * as t from 'io-ts';
import { isRight } from 'fp-ts/Either';
import { PathReporter } from 'io-ts/PathReporter';

const CreateUserCodec = t.type({
  username: t.string,
  email: t.string,
  age: t.number,
});

type CreateUserInput = t.TypeOf<typeof CreateUserCodec>;

function validateInput(input: unknown): CreateUserInput {
  const result = CreateUserCodec.decode(input);
  if (isRight(result)) {
    return result.right;
  }
  throw new ValidationError(PathReporter.report(result).join(', '));
}
```

**Key points:**
- Zod is recommended for new projects due to its developer experience and TypeScript-first design.
- io-ts integrates well with fp-ts for projects using functional programming patterns.
- Both libraries infer TypeScript types from runtime schemas, ensuring type safety and runtime safety are always in sync.
- `safeParse()` (Zod) and `decode()` (io-ts) return structured results instead of throwing, enabling explicit error handling.
- Always replace `req.body` with the validated output to get the benefit of transformations (trimming, lowercasing, coercion).

---

### Type Guards for Security-Sensitive Operations

#### Custom Type Guards

**When to use:** CWE-20, CWE-502 (Deserialization), CWE-843 (Type Confusion) -- to safely narrow types before performing security-sensitive operations.

**User role type guard:**
```typescript
type UserRole = 'user' | 'moderator' | 'admin';

const VALID_ROLES: ReadonlySet<UserRole> = new Set(['user', 'moderator', 'admin']);

function isValidRole(value: unknown): value is UserRole {
  return typeof value === 'string' && VALID_ROLES.has(value as UserRole);
}

function requireAdmin(role: unknown): asserts role is 'admin' {
  if (role !== 'admin') {
    throw new ForbiddenError('Admin access required');
  }
}
```

**Safe JSON parsing type guard:**
```typescript
interface ApiResponse {
  status: string;
  data: {
    id: number;
    name: string;
  };
}

function isApiResponse(value: unknown): value is ApiResponse {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  if (typeof obj.status !== 'string') return false;
  if (typeof obj.data !== 'object' || obj.data === null) return false;
  const data = obj.data as Record<string, unknown>;
  if (typeof data.id !== 'number') return false;
  if (typeof data.name !== 'string') return false;
  return true;
}

// Usage: safely parse untrusted JSON
function parseApiResponse(json: string): ApiResponse {
  const parsed: unknown = JSON.parse(json);
  if (!isApiResponse(parsed)) {
    throw new ValidationError('Invalid API response structure');
  }
  return parsed; // TypeScript knows this is ApiResponse
}
```

**Assertion functions for preconditions:**
```typescript
function assertNonNull<T>(value: T | null | undefined, name: string): asserts value is T {
  if (value === null || value === undefined) {
    throw new Error(`Expected ${name} to be non-null`);
  }
}

function assertString(value: unknown, name: string): asserts value is string {
  if (typeof value !== 'string') {
    throw new ValidationError(`Expected ${name} to be a string, got ${typeof value}`);
  }
}

// Usage:
function processRequest(params: Record<string, unknown>) {
  assertString(params.username, 'username');
  assertNonNull(params.email, 'email');
  // After assertions, TypeScript narrows the types
  // params.username is string, params.email is non-null
}
```

**Key points:**
- Type guards (`value is T`) narrow the type in the `true` branch. TypeScript trusts the guard's implementation.
- Assertion functions (`asserts value is T`) narrow the type for all subsequent code.
- Prefer Zod schemas over hand-written type guards for complex objects. Type guards are best for simple, focused checks.
- Type guards used for security checks must validate every field -- do not rely on structural assumptions.
- `as` type assertions bypass checking entirely. Minimize their use; prefer type guards.

---

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "language": "typescript",
  "framework": "<string: detected framework>",
  "strict_mode": "<boolean: whether strict mode is enabled>",
  "validation_library": "<string: zod | io-ts | class-validator | none>",
  "pattern_applied": "<string: name of the pattern applied>",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer>",
      "original_code": "<string>",
      "fixed_code": "<string>",
      "pattern": "<string: pattern name used>"
    }
  ],
  "types_added": ["<string: new type definitions added>"],
  "imports_added": ["<string: new import statements>"],
  "packages_needed": ["<string: npm packages to install>"],
  "tsconfig_recommendations": ["<string: recommended tsconfig changes>"],
  "warnings": ["<string: manual review items>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries contain valid TypeScript code that compiles under the project's `tsconfig.json`.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **Strict mode not enabled** | Apply the fix pattern but add a `tsconfig_recommendations` entry recommending `strict: true`. The fix should still work without strict mode but may not catch all issues at compile time. |
| **No validation library present** | Recommend Zod as the default. If adding a dependency is not acceptable, use hand-written type guards instead. |
| **Existing `any` types in the codebase** | Preserve existing `any` usage but do not introduce new ones. Add a warning recommending gradual `any` elimination. |
| **JavaScript files mixed with TypeScript** | Only apply TypeScript patterns to `.ts` and `.tsx` files. For `.js` files, defer to the JavaScript fix patterns skill. |
| **Generic type constraints needed** | Ensure generic types have appropriate constraints (e.g., `<T extends string>` instead of `<T>`). |
| **Declaration files (.d.ts) needed** | If branded types or shared types are added, create or update `.d.ts` files if the project uses them. Note this in the output. |

## Constraints

- **Type correctness**: All generated code must compile without errors under the project's `tsconfig.json` settings.
- **No `any` introduction**: Do not introduce `any` types in fix patterns. Use `unknown` for values of uncertain type and narrow with type guards.
- **Minimal `as` assertions**: Type assertions (`as`) bypass type checking. Use them only inside validation functions, never at call sites.
- **Runtime safety**: Branded types alone do not provide runtime safety. Always pair them with runtime validation (Zod, io-ts, or type guards).
- **No runtime execution**: Do not run `tsc` or execute TypeScript code to test fixes.
- **Minimal diff**: Change only the code required for the security fix.
- **Preserve existing types**: Do not change existing type definitions unless they are part of the vulnerability.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to compile or run code.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
