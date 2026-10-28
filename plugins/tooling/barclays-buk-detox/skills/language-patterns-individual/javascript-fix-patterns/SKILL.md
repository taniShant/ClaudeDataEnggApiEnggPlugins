---
name: javascript-fix-patterns
description: "JavaScript / Node.js Security Fix Patterns — Provide JavaScript and Node.js-specific security fix patterns and framework-specific best practices for applying CWE remediations in JavaScript codebases. This skill is composed with CWE-specific reme"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/language_patterns_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# JavaScript / Node.js Security Fix Patterns
## Quick Start

This skill provides language-specific fix patterns for applying CWE remediations in a target programming language.

```
# Loaded by detox-fix-agent based on the detected programming language.
# Provides language-idiomatic fix patterns for each CWE type.
```



## Purpose

Provide JavaScript and Node.js-specific security fix patterns and framework-specific best practices for applying CWE remediations in JavaScript codebases. This skill is composed with CWE-specific remediation skills to translate generic vulnerability fixes into idiomatic JavaScript code using Express.js middleware, Node.js core APIs, and browser DOM APIs. It covers HTTP security headers (helmet), input validation (express-validator), CORS configuration, cryptographic operations (crypto module), command injection prevention (child_process), safe DOM manipulation, and async error handling.

## Inputs

- **cwe_id** (required, string): The CWE identifier being remediated (e.g., `CWE-89`, `CWE-79`).
- **vulnerability** (required, JSON object): The normalized vulnerability object from the CWE skill, containing `file_path`, `line_number`, and `code_snippet`.
- **runtime** (optional, string): `node` or `browser`. Auto-detected from file context and imports if not provided.
- **framework** (optional, string): The framework in use (`express`, `koa`, `fastify`, `next`, `react`, `vanilla`). Auto-detected from imports and project structure if not provided.
- **module_system** (optional, string): `esm` or `commonjs`. Auto-detected from file extension and `package.json` `type` field if not provided.

## Steps

1. **Detect runtime, framework, and module system.**
   - Use `Glob` to find `package.json`.
   - Use `Read` to examine `package.json` for dependencies (express, koa, fastify, react, next) and the `type` field (`module` for ESM, absent or `commonjs` for CJS).
   - Check file extension: `.mjs` = ESM, `.cjs` = CJS, `.js` = depends on `package.json` `type`.
   - Examine import statements: `require()` = CJS, `import ... from` = ESM.

2. **Select the appropriate fix pattern based on CWE and framework.**
   - Match the CWE ID to the relevant pattern section below.
   - Choose the runtime-specific variant (Node.js vs. browser).

3. **Apply the fix using the patterns defined below.**
   - Use `Edit` to apply the code transformation.
   - Add required imports/requires at the top of the file.
   - If the fix requires a new npm package, note it in the output.

4. **Verify idiomatic JavaScript conventions.**
   - Match the project's existing style: `const`/`let` vs `var`, arrow functions vs function declarations, semicolons.
   - Use the module system already in use (ESM `import` or CJS `require`).
   - Maintain consistent `async`/`await` usage.

5. **Scan for similar patterns.**
   - Use `Grep` to find other instances of the same vulnerable pattern in the file and project.
   - Apply the same fix pattern consistently.

---

## Fix Patterns

### Express.js Security Middleware (helmet)

#### HTTP Security Headers

**When to use:** CWE-79 (XSS defense-in-depth via CSP), CWE-693 (Protection Mechanism Failure), CWE-1021 (Clickjacking) in Express applications.

**Before (vulnerable -- no security headers):**
```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.send('<h1>Hello</h1>');
});

app.listen(3000);
```

**After (fixed):**
```javascript
const express = require('express');
const helmet = require('helmet');
const app = express();

app.use(helmet());

// Or with custom CSP:
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'"],
      fontSrc: ["'self'"],
      objectSrc: ["'none'"],
      frameSrc: ["'none'"],
    },
  },
  crossOriginEmbedderPolicy: true,
  crossOriginOpenerPolicy: true,
  crossOriginResourcePolicy: { policy: "same-origin" },
  hsts: { maxAge: 31536000, includeSubDomains: true, preload: true },
  referrerPolicy: { policy: "strict-origin-when-cross-origin" },
}));

app.get('/', (req, res) => {
  res.send('<h1>Hello</h1>');
});

app.listen(3000);
```

**Key points:**
- `helmet()` sets sensible defaults for 15+ HTTP security headers.
- Apply `helmet()` before any route handlers using `app.use()`.
- Customize CSP directives based on the application's actual resource requirements.
- For APIs that do not serve HTML, `helmet()` defaults are still beneficial for defense-in-depth.

---

### Input Validation (express-validator)

#### Request Validation Middleware

**When to use:** CWE-20 (Improper Input Validation), CWE-89 (SQL Injection input layer), CWE-79 (XSS input layer) in Express routes.

**Before (vulnerable -- no validation):**
```javascript
app.post('/api/users', (req, res) => {
  const { username, email, age } = req.body;
  db.query('INSERT INTO users (username, email, age) VALUES (?, ?, ?)',
    [username, email, age]);
  res.json({ status: 'created' });
});
```

**After (fixed):**
```javascript
const { body, validationResult } = require('express-validator');

app.post('/api/users', [
  body('username')
    .isAlphanumeric()
    .isLength({ min: 3, max: 50 })
    .trim()
    .escape(),
  body('email')
    .isEmail()
    .normalizeEmail(),
  body('age')
    .isInt({ min: 13, max: 150 })
    .toInt(),
], (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }
  const { username, email, age } = req.body;
  db.query('INSERT INTO users (username, email, age) VALUES (?, ?, ?)',
    [username, email, age]);
  res.json({ status: 'created' });
});
```

**Reusable validation middleware:**
```javascript
const { validationResult } = require('express-validator');

function validate(validations) {
  return async (req, res, next) => {
    for (const validation of validations) {
      const result = await validation.run(req);
      if (!result.isEmpty()) break;
    }
    const errors = validationResult(req);
    if (errors.isEmpty()) {
      return next();
    }
    return res.status(400).json({ errors: errors.array() });
  };
}

// Usage:
app.post('/api/users', validate([
  body('username').isAlphanumeric().isLength({ min: 3, max: 50 }),
  body('email').isEmail(),
]), userController.create);
```

**Key points:**
- `express-validator` is built on top of `validator.js` and provides sanitization and validation chains.
- Always call `validationResult(req)` after the validators and before processing the request.
- Use `.trim()` and `.escape()` for string sanitization.
- Use `.toInt()`, `.toFloat()`, `.toBoolean()` for type coercion.
- Validation does not replace parameterized queries; it is a defense-in-depth measure.

---

### CORS Configuration

#### Secure CORS Setup

**When to use:** CWE-942 (Overly Permissive CORS Policy), CWE-346 (Origin Validation Error).

**Before (vulnerable -- wildcard CORS):**
```javascript
const cors = require('cors');
app.use(cors()); // Allows all origins
```

**After (fixed):**
```javascript
const cors = require('cors');

const allowedOrigins = [
  'https://www.example.com',
  'https://app.example.com',
];

app.use(cors({
  origin: function (origin, callback) {
    // Allow requests with no origin (e.g., mobile apps, curl)
    if (!origin) return callback(null, true);
    if (allowedOrigins.includes(origin)) {
      return callback(null, true);
    }
    return callback(new Error('Not allowed by CORS'));
  },
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
  maxAge: 86400,
}));
```

**Key points:**
- Never use `cors()` with no options or `origin: '*'` on endpoints that use cookies or credentials.
- `credentials: true` requires a specific origin (not `*`).
- Restrict `methods` and `allowedHeaders` to only what the application needs.
- Validate the `origin` against an explicit allowlist.

---

### Node.js Cryptographic Operations (crypto)

#### Secure Hashing

**When to use:** CWE-327 (Weak Crypto) in Node.js applications.

**Before (vulnerable):**
```javascript
const crypto = require('crypto');

function hashToken(token) {
  return crypto.createHash('md5').update(token).digest('hex');
}
```

**After (fixed):**
```javascript
const crypto = require('crypto');

function hashToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

function verifyHash(token, expectedHash) {
  const hash = crypto.createHash('sha256').update(token).digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(hash, 'hex'),
    Buffer.from(expectedHash, 'hex')
  );
}
```

#### Secure Encryption (AES-256-GCM)

**Before (vulnerable -- createCipher with DES):**
```javascript
const crypto = require('crypto');

function encrypt(text, password) {
  const cipher = crypto.createCipher('des', password);
  let encrypted = cipher.update(text, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  return encrypted;
}
```

**After (fixed -- createCipheriv with AES-256-GCM):**
```javascript
const crypto = require('crypto');

function encrypt(plaintext, key) {
  const iv = crypto.randomBytes(12); // 96-bit IV for GCM
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  let encrypted = cipher.update(plaintext, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  const authTag = cipher.getAuthTag();
  // Return IV + authTag + ciphertext for decryption
  return iv.toString('hex') + ':' + authTag.toString('hex') + ':' + encrypted;
}

function decrypt(encryptedData, key) {
  const parts = encryptedData.split(':');
  const iv = Buffer.from(parts[0], 'hex');
  const authTag = Buffer.from(parts[1], 'hex');
  const ciphertext = parts[2];
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(authTag);
  let decrypted = decipher.update(ciphertext, 'hex', 'utf8');
  decrypted += decipher.final('utf8');
  return decrypted;
}

function generateKey() {
  return crypto.randomBytes(32); // 256-bit key
}
```

**Key points:**
- Never use `crypto.createCipher()` -- it is deprecated and derives the key using MD5 internally. Always use `crypto.createCipheriv()`.
- AES-256-GCM provides authenticated encryption (confidentiality + integrity).
- Use `crypto.randomBytes()` for IV and key generation.
- Store the IV and auth tag alongside the ciphertext (they are not secret).
- Use `crypto.timingSafeEqual()` for constant-time comparison of hashes and tokens.

---

### Command Injection Prevention (child_process)

#### Safe Process Execution

**When to use:** CWE-78 (OS Command Injection) in Node.js applications.

**Before (vulnerable -- shell execution with user input):**
```javascript
const { exec } = require('child_process');

app.get('/api/ping', (req, res) => {
  const host = req.query.host;
  exec(`ping -c 4 ${host}`, (error, stdout) => {
    res.send(stdout);
  });
});
```

**After (fixed -- execFile with argument array, no shell):**
```javascript
const { execFile } = require('child_process');

const HOSTNAME_REGEX = /^[a-zA-Z0-9][a-zA-Z0-9.-]{0,253}[a-zA-Z0-9]$/;

app.get('/api/ping', (req, res) => {
  const host = req.query.host;

  // Validate input against allowlist pattern
  if (!host || !HOSTNAME_REGEX.test(host)) {
    return res.status(400).json({ error: 'Invalid hostname' });
  }

  // execFile does not spawn a shell -- arguments are passed directly
  execFile('ping', ['-c', '4', host], { timeout: 10000 }, (error, stdout) => {
    if (error) {
      return res.status(500).json({ error: 'Ping failed' });
    }
    res.send(stdout);
  });
});
```

**After (fixed -- spawn with no shell):**
```javascript
const { spawn } = require('child_process');

function runCommand(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      shell: false,   // Explicitly disable shell
      timeout: 10000,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (data) => { stdout += data; });
    child.stderr.on('data', (data) => { stderr += data; });

    child.on('close', (code) => {
      if (code === 0) resolve(stdout);
      else reject(new Error(`Process exited with code ${code}: ${stderr}`));
    });

    child.on('error', reject);
  });
}
```

**Key points:**
- Never use `exec()` with string interpolation of user input. `exec()` spawns a shell, enabling command chaining with `;`, `&&`, `||`, `|`, backticks, and `$()`.
- Use `execFile()` or `spawn()` with `shell: false` (the default). These pass arguments as an array directly to the executable without shell interpretation.
- Always validate user input against an allowlist before passing it as a command argument.
- Set `timeout` to prevent long-running commands from hanging the server.
- If `shell: true` is ever needed (avoid if possible), use `shellescape` or similar to escape arguments.

---

### DOM Manipulation (Browser JavaScript)

#### Safe Content Insertion

**When to use:** CWE-79 (DOM-based XSS) in browser-side JavaScript.

**Before (vulnerable -- innerHTML with user data):**
```javascript
function displayComment(commentText) {
  const div = document.getElementById('comments');
  div.innerHTML += `<div class="comment">${commentText}</div>`;
}
```

**After (fixed -- textContent for plain text):**
```javascript
function displayComment(commentText) {
  const container = document.getElementById('comments');
  const div = document.createElement('div');
  div.className = 'comment';
  div.textContent = commentText;  // Safely sets text, no HTML parsing
  container.appendChild(div);
}
```

**After (fixed -- DOMPurify when HTML rendering is needed):**
```javascript
import DOMPurify from 'dompurify';

function displayRichComment(commentHtml) {
  const container = document.getElementById('comments');
  const div = document.createElement('div');
  div.className = 'comment';
  div.innerHTML = DOMPurify.sanitize(commentHtml, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
    ALLOWED_ATTR: ['href', 'title'],
  });
  container.appendChild(div);
}
```

#### Replacing Dangerous Sink APIs

| Dangerous API | Safe Replacement |
|---|---|
| `element.innerHTML = userInput` | `element.textContent = userInput` or `DOMPurify.sanitize()` |
| `element.outerHTML = userInput` | DOM creation with `textContent` |
| `document.write(userInput)` | DOM manipulation APIs (`createElement`, `appendChild`) |
| `eval(userInput)` | `JSON.parse()` for data, function references for callbacks |
| `setTimeout(userInput, ms)` | `setTimeout(functionRef, ms)` |
| `setInterval(userInput, ms)` | `setInterval(functionRef, ms)` |
| `new Function(userInput)` | Predefined functions or safe parsing |
| `location.href = userInput` | URL validation with `new URL()` + scheme check |

**URL validation for href/src:**
```javascript
function setSafeLink(element, url) {
  try {
    const parsed = new URL(url, window.location.origin);
    if (['http:', 'https:'].includes(parsed.protocol)) {
      element.href = parsed.href;
    } else {
      element.href = '#';
      console.warn('Blocked unsafe URL protocol:', parsed.protocol);
    }
  } catch (e) {
    element.href = '#';
  }
}
```

---

### Async Error Handling

#### Express Async Route Handler Wrapper

**When to use:** CWE-755 (Improper Handling of Exceptional Conditions), CWE-200 (Information Exposure through error messages) in Express applications.

**Before (vulnerable -- unhandled promise rejection leaks errors):**
```javascript
app.get('/api/users/:id', async (req, res) => {
  const user = await db.query('SELECT * FROM users WHERE id = ?', [req.params.id]);
  res.json(user);
  // If db.query rejects, Express 4 does not catch it -- unhandled rejection
});
```

**After (fixed -- async wrapper):**
```javascript
function asyncHandler(fn) {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

app.get('/api/users/:id', asyncHandler(async (req, res) => {
  const user = await db.query('SELECT * FROM users WHERE id = ?', [req.params.id]);
  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }
  res.json(user);
}));
```

**Note:** Express 5 natively handles promise rejections in async route handlers. For Express 4, a wrapper is required.

#### Global Error Handler (Express)

```javascript
// Must be registered AFTER all route handlers
app.use((err, req, res, next) => {
  // Log the full error internally
  console.error('Unhandled error:', {
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
  });

  // Never expose internal error details to the client
  const statusCode = err.statusCode || 500;
  res.status(statusCode).json({
    error: statusCode === 500 ? 'Internal server error' : err.message,
  });
});

// Handle unhandled promise rejections globally
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // In production, consider graceful shutdown
});
```

**Key points:**
- Express 4 does not catch promise rejections from async handlers. Wrap all async handlers or use `express-async-errors`.
- The error-handling middleware must have exactly 4 parameters `(err, req, res, next)` to be recognized by Express.
- Never send `err.stack` or `err.message` (for 500 errors) to the client.
- Log full error details server-side with structured logging.
- Set `NODE_ENV=production` to prevent Express from sending stack traces in default error responses.

---

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "language": "javascript",
  "runtime": "<string: node | browser>",
  "framework": "<string: detected framework>",
  "module_system": "<string: esm | commonjs>",
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
  "imports_added": ["<string: new import/require statements>"],
  "packages_needed": ["<string: npm packages to install>"],
  "middleware_added": ["<string: middleware additions>"],
  "warnings": ["<string: manual review items>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries contain valid JavaScript code matching the project's module system and style.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **Cannot detect runtime** | Examine file content for `require`, `process`, `window`, `document` to determine Node.js vs browser. If ambiguous, flag for manual review. |
| **ESM vs CJS mismatch** | Match the module system used in the file. Do not mix `require()` and `import` in the same file unless the project uses dynamic `import()`. |
| **Express version incompatibility** | Check `package.json` for Express version. Express 4 and 5 have different error handling. Apply the version-appropriate pattern. |
| **Missing dependency** | Note the required npm package in `packages_needed`. Do not modify `package.json` directly. |
| **TypeScript file detected** | Defer to the TypeScript fix patterns skill. Note the detection in the output. |
| **React/Next.js SSR context** | Determine if the code runs server-side or client-side. Apply the appropriate pattern (Node.js for SSR, browser for CSR). |

## Constraints

- **Preserve functionality**: All generated code must be syntactically valid JavaScript and semantically equivalent to the original for valid inputs.
- **Module system consistency**: Use `require()` for CJS projects and `import` for ESM projects. Do not change the project's module system.
- **No runtime execution**: Do not execute JavaScript code or run `node` to test fixes.
- **Minimal diff**: Change only the code required for the security fix.
- **Async correctness**: If the original code is async, the fix must also be async. Do not introduce sync blocking calls in async code.
- **Browser compatibility**: For browser-side fixes, note any APIs that require specific browser support levels.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
