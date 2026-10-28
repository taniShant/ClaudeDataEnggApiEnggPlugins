---
name: cwe-022-path-traversal
description: "CWE-22: Path Traversal Remediation — Remediate path traversal vulnerabilities by applying path canonicalization combined with allowlist-based directory confinement checks. This skill iden"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-22: Path Traversal Remediation
## Quick Start

This skill provides the fix pattern for CWE-022. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-022 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-22
- **CWE Name**: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')
- **Severity**: High
- **OWASP Category**: A01:2021 - Broken Access Control

## Purpose

Remediate path traversal vulnerabilities by applying path canonicalization combined with allowlist-based directory confinement checks. This skill identifies where user-controlled input is used to construct file paths without proper validation, allowing attackers to access files outside the intended directory using sequences like `../`. It applies canonicalization (resolving to an absolute, normalized path) followed by a prefix check to ensure the resolved path stays within the allowed base directory. It covers Python (pathlib, os.path.realpath), Java (Path.normalize with toRealPath), and Node.js (path.resolve with startsWith check).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the path traversal vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-22`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.
- **base_directory** (optional, string): The intended base directory that file operations should be confined to. If not provided, must be inferred from code context.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language and file I/O patterns.**
   - Examine import statements, file extensions, and API calls to identify the language and file I/O libraries.

3. **Identify the vulnerable path construction.**
   - Locate where user-controlled input is used to build a file path.
   - Trace the input back to its source (request parameter, function argument, external data).
   - Identify the file operation that uses the constructed path (open, read, write, delete, etc.).

4. **Determine the intended base directory.**
   - Look for a base directory or root path that the code intends to confine file access to (e.g., `UPLOAD_DIR`, `STATIC_ROOT`, `DATA_PATH`).
   - If `base_directory` input is provided, use it.
   - If no base directory can be determined, flag for manual review -- the fix requires knowing which directory to confine to.

5. **Apply the canonicalization and confinement check.**
   - Resolve the user-supplied path relative to the base directory.
   - Canonicalize the result to an absolute path with all `.`, `..`, and symlinks resolved.
   - Verify that the canonicalized path starts with the canonicalized base directory.
   - If the check fails, raise an error or return a 403/404 response.

6. **Apply the edit.**
   - Use `Edit` to replace the vulnerable path construction with the safe version.
   - Add necessary imports (e.g., `from pathlib import Path`, `import java.nio.file.Path`).
   - Preserve code formatting, indentation, and surrounding logic.

7. **Scan for similar patterns in the same file.**
   - Use `Grep` to find other instances of the same vulnerable pattern.
   - Apply the same fix to all instances.

8. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm the fix is syntactically correct.
   - Confirm that all file path constructions using user input include canonicalization and confinement checks.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "base_directory": "<string: the base directory used for confinement>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the vulnerable code>",
      "fixed_code": "<string: the canonicalized + confined replacement>",
      "fix_type": "canonicalization_with_prefix_check | allowlist_validation"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries have valid `fixed_code` with a canonicalization and prefix check.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Path traversal occurs when user-controlled input is used to construct a file path without proper validation, allowing an attacker to use `../` sequences or absolute paths to access files outside the intended directory.

### Detection Patterns

**Direct path concatenation with user input:**
```
# Python:              open(base_dir + "/" + user_input)
# Python:              open(os.path.join(base_dir, user_input))
# Python:              Path(base_dir) / user_input
# Java:                new File(baseDir + File.separator + userInput)
# Java:                Paths.get(baseDir, userInput)
# Node.js:             fs.readFile(baseDir + '/' + userInput)
# Node.js:             fs.readFile(path.join(baseDir, userInput))
```

**Indicators of user-controlled input in file paths:**
- Variables sourced from `request.args`, `request.form`, `req.query`, `req.params`, `req.body`, `getParameter()`.
- URL path parameters or route parameters.
- File upload names or form-submitted filenames.

**Insufficient validation patterns (still vulnerable):**
```
# Blacklist check (bypassable):
if ".." not in filename:     # Can be bypassed with encoding
    open(base_dir + "/" + filename)

# Simple replace (bypassable):
filename = filename.replace("../", "")   # ....// becomes ../
```

## Fix Pattern

The general fix combines two operations: **path canonicalization** (resolving to an absolute, normalized path) and **prefix verification** (confirming the resolved path is within the allowed base directory).

**Transformation steps:**
1. Define or identify the base directory that file access should be confined to.
2. Join the user-supplied path component with the base directory.
3. Canonicalize (resolve) the resulting path to its real absolute form.
4. Canonicalize the base directory to its real absolute form.
5. Verify that the resolved file path starts with the resolved base directory.
6. If the check fails, deny the operation.

**Why blacklists and stripping fail:**
- Stripping `../` once does not handle `....//` (which becomes `../` after one strip).
- URL encoding (`%2e%2e%2f`), double encoding, or null bytes can bypass simple checks.
- Canonicalization resolves all these variations to the actual filesystem path, making the prefix check reliable.

## Language-Specific Examples

### Python -- pathlib

**Before (vulnerable):**
```python
from flask import request, send_file

@app.route('/download')
def download_file():
    filename = request.args.get('file')
    filepath = f"/var/app/uploads/{filename}"
    return send_file(filepath)
```

**After (fixed):**
```python
from pathlib import Path
from flask import request, send_file, abort

UPLOAD_DIR = Path("/var/app/uploads").resolve()

@app.route('/download')
def download_file():
    filename = request.args.get('file')
    if not filename:
        abort(400)
    filepath = (UPLOAD_DIR / filename).resolve()
    if not filepath.is_relative_to(UPLOAD_DIR):
        abort(403)
    return send_file(filepath)
```

**Explanation:** `Path.resolve()` canonicalizes the path, resolving all `..` components and symlinks into a real absolute path. `is_relative_to()` (Python 3.9+) checks that the resolved path starts with the base directory. If the user supplies `../../etc/passwd`, the resolved path will be `/etc/passwd`, which is not relative to `/var/app/uploads`, and the request is denied with a 403.

### Python -- os.path.realpath (Python < 3.9)

**Before (vulnerable):**
```python
import os
from flask import request, send_file

@app.route('/download')
def download_file():
    filename = request.args.get('file')
    filepath = os.path.join('/var/app/uploads', filename)
    return send_file(filepath)
```

**After (fixed):**
```python
import os
from flask import request, send_file, abort

UPLOAD_DIR = os.path.realpath('/var/app/uploads')

@app.route('/download')
def download_file():
    filename = request.args.get('file')
    if not filename:
        abort(400)
    filepath = os.path.realpath(os.path.join(UPLOAD_DIR, filename))
    if not filepath.startswith(UPLOAD_DIR + os.sep):
        abort(403)
    return send_file(filepath)
```

**Explanation:** `os.path.realpath()` resolves symlinks and normalizes the path. The `startswith` check uses `UPLOAD_DIR + os.sep` (not just `UPLOAD_DIR`) to prevent a partial prefix match (e.g., `/var/app/uploads_evil/secret` should not match `/var/app/uploads`).

### Java -- Path.normalize and toRealPath

**Before (vulnerable):**
```java
@GetMapping("/download")
public ResponseEntity<Resource> downloadFile(@RequestParam String filename) throws IOException {
    Path filePath = Paths.get("/var/app/uploads/" + filename);
    Resource resource = new UrlResource(filePath.toUri());
    return ResponseEntity.ok().body(resource);
}
```

**After (fixed):**
```java
import java.nio.file.Path;
import java.nio.file.Paths;

@GetMapping("/download")
public ResponseEntity<Resource> downloadFile(@RequestParam String filename) throws IOException {
    Path baseDir = Paths.get("/var/app/uploads").toRealPath();
    Path filePath = baseDir.resolve(filename).normalize().toRealPath();
    if (!filePath.startsWith(baseDir)) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
    }
    Resource resource = new UrlResource(filePath.toUri());
    return ResponseEntity.ok().body(resource);
}
```

**Explanation:** `normalize()` removes redundant `.` and `..` components. `toRealPath()` resolves symlinks and verifies the file exists. `startsWith` on Java `Path` objects does a proper path-component check (unlike string `startsWith`), so `/var/app/uploads_evil` will not match `/var/app/uploads`.

### Node.js -- path.resolve with startsWith

**Before (vulnerable):**
```javascript
const path = require('path');
const fs = require('fs');

app.get('/download', (req, res) => {
  const filename = req.query.file;
  const filePath = path.join(__dirname, 'uploads', filename);
  res.sendFile(filePath);
});
```

**After (fixed):**
```javascript
const path = require('path');
const fs = require('fs');

const UPLOAD_DIR = path.resolve(__dirname, 'uploads');

app.get('/download', (req, res) => {
  const filename = req.query.file;
  if (!filename) {
    return res.status(400).send('Missing file parameter');
  }
  const filePath = path.resolve(UPLOAD_DIR, filename);
  if (!filePath.startsWith(UPLOAD_DIR + path.sep)) {
    return res.status(403).send('Access denied');
  }
  res.sendFile(filePath);
});
```

**Explanation:** `path.resolve()` produces an absolute normalized path, resolving `..` components. The `startsWith` check (with `path.sep` appended to prevent partial directory name matches) confirms the file is within `UPLOAD_DIR`. Note: `path.resolve` does not resolve symlinks; if symlink traversal is a concern, use `fs.realpathSync()` instead.

### Node.js -- With Symlink Resolution

**After (fixed, with symlink protection):**
```javascript
const path = require('path');
const fs = require('fs');

const UPLOAD_DIR = fs.realpathSync(path.resolve(__dirname, 'uploads'));

app.get('/download', (req, res) => {
  const filename = req.query.file;
  if (!filename) {
    return res.status(400).send('Missing file parameter');
  }
  const requestedPath = path.resolve(UPLOAD_DIR, filename);
  let realPath;
  try {
    realPath = fs.realpathSync(requestedPath);
  } catch (err) {
    return res.status(404).send('File not found');
  }
  if (!realPath.startsWith(UPLOAD_DIR + path.sep)) {
    return res.status(403).send('Access denied');
  }
  res.sendFile(realPath);
});
```

**Explanation:** `fs.realpathSync()` resolves symlinks, ensuring that even if a symlink within the uploads directory points outside it, the check will catch it.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Manual test with traversal payloads:**
   - Input: `../../etc/passwd` -- should be denied (403).
   - Input: `..%2f..%2fetc%2fpasswd` (URL-encoded) -- should be denied after decoding.
   - Input: `....//....//etc/passwd` -- should be denied after normalization.
   - Input: `/etc/passwd` (absolute path) -- should be denied.
   - Input: `validfile.txt` -- should succeed (file within allowed directory).

2. **Automated test pattern:**
   ```python
   def test_path_traversal_prevented(client):
       response = client.get('/download?file=../../etc/passwd')
       assert response.status_code == 403

   def test_valid_file_accessible(client):
       response = client.get('/download?file=report.pdf')
       assert response.status_code == 200
   ```

3. **Semgrep rules that should pass after fix:**
   ```yaml
   rules:
     - id: python-path-traversal
       patterns:
         - pattern: |
             open(os.path.join($BASE, $INPUT))
         - pattern-not-inside: |
             if ... .startswith(...):
                 ...
       message: "Path traversal: user input in file path without confinement check"
       languages: [python]
       severity: ERROR
   ```

### Verifying Functionality is Preserved

- Verify that valid filenames (no traversal sequences) still work correctly.
- Test filenames with spaces, Unicode characters, and other special characters.
- Test with nested subdirectories within the allowed base directory (e.g., `subdir/file.txt`).
- Verify that the response codes are appropriate (403 for traversal attempts, 404 for missing files, 200 for valid files).

## Common Mistakes

1. **Checking before resolving.** Checking for `..` in the raw user input before canonicalization is bypassable (URL encoding, double dots, null bytes). Always canonicalize first, then check.

2. **Using `os.path.normpath` instead of `os.path.realpath` in Python.** `normpath` normalizes the string but does not resolve symlinks. An attacker who can create symlinks could bypass the check. Use `realpath` (or `Path.resolve()`) for full canonicalization.

3. **String `startsWith` without trailing separator.** Checking `filePath.startsWith(baseDir)` without appending a path separator allows `/var/app/uploads_evil/secret` to pass if `baseDir` is `/var/app/uploads`. Always append `os.sep` (or `path.sep` or `/`).

4. **Stripping `../` as a fix.** Replacing `../` in user input is unreliable. `....//` becomes `../` after one round of stripping. Repeated stripping is still fragile against other encodings. Canonicalization is the correct approach.

5. **Not handling empty or null filenames.** If the filename is empty or null, the resolved path may equal the base directory itself (a directory, not a file). Validate that the filename is non-empty and the resolved path is a file.

6. **Forgetting about symlinks.** Even within the allowed directory, a symlink could point outside it. Use functions that resolve symlinks (`realpath`, `toRealPath`, `fs.realpathSync`) for maximum safety.

7. **Allowing absolute paths in input.** If the user supplies `/etc/passwd` and the code does not resolve it relative to the base directory, the confinement check is bypassed. Always use relative resolution: join the base directory with the user input before canonicalization.

8. **Windows-specific path issues.** On Windows, `..\..\` uses backslashes, and drive letters (`C:`, `D:`) can bypass Unix-style checks. Ensure the canonicalization and prefix check work on the deployment platform.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine base directory** | Flag for manual review with a warning. The fix requires knowing which directory to confine to. |
| **Language not recognized** | Return error JSON. Path traversal remediation requires knowing the specific filesystem API. |
| **Multiple base directories** | If the code uses different base directories for different operations, apply a separate confinement check for each. If too complex, flag for manual review. |
| **Symlink-heavy environment** | Recommend `realpath`-based resolution and flag for review to confirm symlink behavior is intentional. |
| **Path constructed across multiple statements or files** | Trace the full path construction. If it spans multiple files, flag for manual review. |

## Constraints

- **Preserve file access functionality**: The fix must still allow access to files within the intended directory.
- **No execution**: Do not run the application or perform actual file system operations to test the fix.
- **No file deletion**: Do not modify or delete any files outside the vulnerability's source file.
- **Platform awareness**: Note if the fix is platform-specific (e.g., `os.sep` behavior on Windows vs. Unix). Recommend cross-platform testing in warnings.
- **Minimal diff**: Change only the vulnerable path construction. Do not refactor surrounding code unless required for the fix (e.g., adding imports, defining the base directory constant).
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
