---
name: cwe-434-unrestricted-upload
description: "CWE-434: Unrestricted File Upload Remediation — Remediate unrestricted file upload vulnerabilities by implementing comprehensive file validation including type checking, magic byte verification, siz"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-434: Unrestricted File Upload Remediation
## Quick Start

This skill provides the fix pattern for CWE-434. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-434 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-434
- **CWE Name**: Unrestricted Upload of File with Dangerous Type
- **Severity**: High
- **OWASP Category**: A04:2021 - Insecure Design

## Purpose

Remediate unrestricted file upload vulnerabilities by implementing comprehensive file validation including type checking, magic byte verification, size limits, filename sanitization, and safe storage practices. This skill identifies endpoints that accept file uploads without adequate validation and adds multiple layers of defense to prevent malicious file uploads that could lead to remote code execution, stored XSS, or denial of service. It covers Python (Flask, Django), Java (Spring), and JavaScript/Node.js (Express with multer).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the upload vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-434`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `upload_context` (string, optional): Context of the upload (`avatar`, `document`, `media`, `generic`). Helps determine allowed file types.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.
- **framework** (optional, string): Framework in use (`flask`, `django`, `spring`, `express`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language, framework, and upload handling mechanism.**
   - Examine import statements and the file upload handling pattern.
   - Identify the upload library or middleware (multer, Django file handling, Spring MultipartFile, Flask request.files).

3. **Identify what validations are missing.**
   - **File type validation**: Is the file extension and MIME type checked against an allowlist?
   - **Magic byte validation**: Are the file's magic bytes checked to confirm the actual file type?
   - **Size limit**: Is there a maximum file size enforced?
   - **Filename sanitization**: Is the filename sanitized to prevent path traversal and special characters?
   - **Storage location**: Are uploaded files stored outside the web root with non-executable permissions?

4. **Apply all missing validations.**
   - Add file extension allowlist checking.
   - Add magic byte (file signature) validation.
   - Add file size limits.
   - Sanitize the filename (strip path components, replace special characters, generate a random name).
   - Configure storage to a non-web-accessible directory.
   - Set proper file permissions (non-executable).

5. **Apply the edit.**
   - Use `Edit` to replace the vulnerable upload handler with the validated version.
   - Add necessary imports.
   - Preserve code formatting, indentation, and surrounding logic.

6. **Scan for similar patterns in the same file and related files.**
   - Use `Grep` to find other file upload handlers in the codebase.
   - Apply the same fix to all instances.

7. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm all validations are in place.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "validations_added": [
    "extension_allowlist",
    "magic_byte_check",
    "size_limit",
    "filename_sanitization",
    "safe_storage"
  ],
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the vulnerable code>",
      "fixed_code": "<string: the validated replacement>",
      "fix_type": "file_validation | filename_sanitization | size_limit | storage_config"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "allowed_extensions": ["<string: the configured allowed file extensions>"],
  "max_file_size": "<string: the configured maximum file size>",
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all necessary validations have been added.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Unrestricted file upload occurs when an application accepts files from users without validating the file type, content, size, or name, or stores them in a location where they can be executed by the web server. This can lead to remote code execution (uploading a web shell), stored XSS (uploading an HTML file with scripts), or denial of service (uploading very large files).

### Detection Patterns

**No validation on upload:**
```
# Flask:         file = request.files['file']; file.save(os.path.join(UPLOAD_DIR, file.filename))
# Django:        uploaded = request.FILES['file']; handle_uploaded_file(uploaded)
# Express:       app.post('/upload', upload.single('file'), handler)  # No filter in multer config
# Spring:        @PostMapping("/upload") void upload(@RequestParam MultipartFile file)
```

**Extension check using blacklist instead of allowlist:**
```
# Python:        if not filename.endswith('.exe'):  # Blacklist approach
# JavaScript:    if (!['exe', 'bat'].includes(ext))  # Blacklist approach
```

**Using user-provided filename directly:**
```
# Python:        filepath = os.path.join(upload_dir, file.filename)  # Path traversal risk
# JavaScript:    const path = `uploads/${req.file.originalname}`  # Path traversal risk
```

**Regex detection patterns:**
```
# No validation:     request\.files\[.*\]\.save\(
# User filename:     file\.filename|originalname|getOriginalFilename
# Missing multer filter: multer\(\{.*dest:.*\}\)(?!.*fileFilter)
# No size limit:     multer\(\{(?!.*limits)
```

## Fix Pattern

The general fix applies defense-in-depth with multiple validation layers:

1. **Extension allowlist**: Only permit specific, known-safe file extensions.
2. **MIME type validation**: Verify the Content-Type header matches the expected type (defense-in-depth; can be spoofed).
3. **Magic byte validation**: Read the first few bytes of the file and verify they match the expected file signature.
4. **File size limit**: Enforce a maximum file size at both the middleware and application levels.
5. **Filename sanitization**: Generate a random filename or sanitize the user-provided name (strip path separators, limit length, replace special characters).
6. **Safe storage**: Store files outside the web root, use non-executable permissions, and serve them through a controlled endpoint with proper Content-Disposition headers.

**Transformation steps:**
1. Define an allowlist of permitted file extensions and their magic bytes.
2. Add validation that checks extension, magic bytes, and size before saving.
3. Generate a safe filename (UUID-based or sanitized).
4. Save to a non-web-accessible directory.
5. Add imports for file validation utilities.

## Language-Specific Examples

### Python/Flask -- Unrestricted Upload

**Before (vulnerable):**
```python
import os
from flask import Flask, request, redirect

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    return redirect('/files')
```

**After (fixed):**
```python
import os
import uuid
from flask import Flask, request, redirect, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = '/var/app/uploads'  # Outside web root
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAGIC_BYTES = {
    'png': b'\x89PNG',
    'jpg': b'\xff\xd8\xff',
    'jpeg': b'\xff\xd8\xff',
    'gif': b'GIF8',
    'pdf': b'%PDF',
}

def validate_file(file):
    """Validate uploaded file type, content, and size."""
    if not file or not file.filename:
        return False, 'No file provided'

    # Check extension
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f'File type .{ext} is not allowed'

    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return False, 'File exceeds maximum size limit'

    # Check magic bytes
    header = file.read(8)
    file.seek(0)
    expected_magic = MAGIC_BYTES.get(ext)
    if expected_magic and not header.startswith(expected_magic):
        return False, 'File content does not match its extension'

    return True, None

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    is_valid, error = validate_file(file)
    if not is_valid:
        abort(400, description=error)

    ext = file.filename.rsplit('.', 1)[-1].lower()
    safe_filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
    file.save(filepath)
    os.chmod(filepath, 0o644)  # Non-executable
    return redirect('/files')
```

**Explanation:** The fix adds five layers of defense: (1) extension allowlist, (2) file size check, (3) magic byte validation, (4) UUID-generated filename to prevent path traversal and overwrites, and (5) storage outside the web root with non-executable permissions. The user-provided filename is never used directly.

### Python/Django -- File Upload Validation

**Before (vulnerable):**
```python
from django.http import JsonResponse

def upload_document(request):
    uploaded_file = request.FILES['document']
    with open(f'media/{uploaded_file.name}', 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    return JsonResponse({'status': 'uploaded'})
```

**After (fixed):**
```python
import os
import uuid
from django.http import JsonResponse
from django.conf import settings

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAGIC_BYTES = {
    'pdf': b'%PDF',
    'doc': b'\xd0\xcf\x11\xe0',
    'docx': b'PK\x03\x04',
    'txt': None,  # Text files have no fixed magic bytes
}

def validate_upload(uploaded_file):
    if not uploaded_file or not uploaded_file.name:
        return False, 'No file provided'

    ext = uploaded_file.name.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.name else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f'File type .{ext} is not allowed'

    if uploaded_file.size > MAX_FILE_SIZE:
        return False, 'File exceeds maximum size limit'

    header = uploaded_file.read(8)
    uploaded_file.seek(0)
    expected_magic = MAGIC_BYTES.get(ext)
    if expected_magic and not header.startswith(expected_magic):
        return False, 'File content does not match its extension'

    return True, None

def upload_document(request):
    uploaded_file = request.FILES.get('document')
    is_valid, error = validate_upload(uploaded_file)
    if not is_valid:
        return JsonResponse({'error': error}, status=400)

    ext = uploaded_file.name.rsplit('.', 1)[-1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    upload_path = os.path.join(settings.MEDIA_ROOT, 'documents', safe_name)
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)

    with open(upload_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    os.chmod(upload_path, 0o644)

    return JsonResponse({'status': 'uploaded', 'filename': safe_name})
```

**Explanation:** The uploaded file is validated for extension, size, and magic bytes before saving. The filename is replaced with a UUID to prevent path traversal and overwrites. Files are stored in a dedicated directory with non-executable permissions.

### Java/Spring -- MultipartFile Validation

**Before (vulnerable):**
```java
@RestController
public class FileUploadController {

    @PostMapping("/upload")
    public ResponseEntity<?> upload(@RequestParam("file") MultipartFile file) throws IOException {
        Path path = Paths.get("uploads/" + file.getOriginalFilename());
        Files.write(path, file.getBytes());
        return ResponseEntity.ok(Map.of("status", "uploaded"));
    }
}
```

**After (fixed):**
```java
import java.util.Set;
import java.util.UUID;

@RestController
public class FileUploadController {

    private static final String UPLOAD_DIR = "/var/app/uploads";
    private static final long MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
    private static final Set<String> ALLOWED_EXTENSIONS = Set.of("png", "jpg", "jpeg", "gif", "pdf");
    private static final Map<String, byte[]> MAGIC_BYTES = Map.of(
        "png", new byte[]{(byte)0x89, 0x50, 0x4E, 0x47},
        "jpg", new byte[]{(byte)0xFF, (byte)0xD8, (byte)0xFF},
        "jpeg", new byte[]{(byte)0xFF, (byte)0xD8, (byte)0xFF},
        "gif", new byte[]{0x47, 0x49, 0x46, 0x38},
        "pdf", new byte[]{0x25, 0x50, 0x44, 0x46}
    );

    @PostMapping("/upload")
    public ResponseEntity<?> upload(@RequestParam("file") MultipartFile file) throws IOException {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "No file provided"));
        }

        // Validate extension
        String originalName = file.getOriginalFilename();
        String ext = "";
        if (originalName != null && originalName.contains(".")) {
            ext = originalName.substring(originalName.lastIndexOf('.') + 1).toLowerCase();
        }
        if (!ALLOWED_EXTENSIONS.contains(ext)) {
            return ResponseEntity.badRequest().body(Map.of("error", "File type not allowed"));
        }

        // Validate size
        if (file.getSize() > MAX_FILE_SIZE) {
            return ResponseEntity.badRequest().body(Map.of("error", "File exceeds size limit"));
        }

        // Validate magic bytes
        byte[] header = new byte[8];
        try (var is = file.getInputStream()) {
            is.read(header);
        }
        byte[] expectedMagic = MAGIC_BYTES.get(ext);
        if (expectedMagic != null) {
            for (int i = 0; i < expectedMagic.length; i++) {
                if (header[i] != expectedMagic[i]) {
                    return ResponseEntity.badRequest()
                        .body(Map.of("error", "File content does not match extension"));
                }
            }
        }

        // Save with safe filename
        String safeFilename = UUID.randomUUID().toString() + "." + ext;
        Path uploadPath = Paths.get(UPLOAD_DIR, safeFilename);
        Files.createDirectories(uploadPath.getParent());
        Files.write(uploadPath, file.getBytes());

        return ResponseEntity.ok(Map.of("status", "uploaded", "filename", safeFilename));
    }
}
```

**Explanation:** Extension allowlist, size limit, and magic byte checks are added before saving. The original filename is replaced with a UUID. Files are stored outside the web root.

### JavaScript/Express -- Multer Configuration

**Before (vulnerable):**
```javascript
const multer = require('multer');
const upload = multer({ dest: 'public/uploads/' });

app.post('/upload', upload.single('file'), (req, res) => {
  res.json({ status: 'uploaded', path: req.file.path });
});
```

**After (fixed):**
```javascript
const multer = require('multer');
const path = require('path');
const crypto = require('crypto');
const fs = require('fs');

const UPLOAD_DIR = '/var/app/uploads'; // Outside web root
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
const ALLOWED_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.pdf']);
const ALLOWED_MIMES = new Set([
  'image/png', 'image/jpeg', 'image/gif', 'application/pdf'
]);
const MAGIC_BYTES = {
  '.png': Buffer.from([0x89, 0x50, 0x4E, 0x47]),
  '.jpg': Buffer.from([0xFF, 0xD8, 0xFF]),
  '.jpeg': Buffer.from([0xFF, 0xD8, 0xFF]),
  '.gif': Buffer.from([0x47, 0x49, 0x46, 0x38]),
  '.pdf': Buffer.from([0x25, 0x50, 0x44, 0x46]),
};

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, UPLOAD_DIR),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const safeName = crypto.randomUUID() + ext;
    cb(null, safeName);
  }
});

const fileFilter = (req, file, cb) => {
  const ext = path.extname(file.originalname).toLowerCase();
  if (!ALLOWED_EXTENSIONS.has(ext) || !ALLOWED_MIMES.has(file.mimetype)) {
    return cb(new Error('File type not allowed'), false);
  }
  cb(null, true);
};

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: MAX_FILE_SIZE }
});

app.post('/upload', upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file provided' });
  }

  // Validate magic bytes after upload
  const ext = path.extname(req.file.originalname).toLowerCase();
  const expectedMagic = MAGIC_BYTES[ext];
  if (expectedMagic) {
    const fd = fs.openSync(req.file.path, 'r');
    const header = Buffer.alloc(8);
    fs.readSync(fd, header, 0, 8, 0);
    fs.closeSync(fd);
    if (!header.slice(0, expectedMagic.length).equals(expectedMagic)) {
      fs.unlinkSync(req.file.path); // Delete the invalid file
      return res.status(400).json({ error: 'File content does not match extension' });
    }
  }

  res.json({ status: 'uploaded', filename: req.file.filename });
});

// Handle multer errors
app.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    if (err.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ error: 'File exceeds size limit' });
    }
    return res.status(400).json({ error: err.message });
  }
  if (err.message === 'File type not allowed') {
    return res.status(400).json({ error: err.message });
  }
  next(err);
});
```

**Explanation:** Multer is configured with a `fileFilter` for extension and MIME type validation, a `limits` object for size enforcement, and a `storage` configuration that generates UUID filenames. After upload, magic bytes are verified and the file is deleted if validation fails. Files are stored outside the web root (`/var/app/uploads`).

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Malicious file type test**: Attempt to upload a `.php`, `.jsp`, `.exe`, or `.html` file. Verify the upload is rejected.
2. **Extension spoofing test**: Rename a PHP file to `shell.php.jpg` or `shell.jpg`. Verify the magic byte check catches the mismatch.
3. **Oversized file test**: Attempt to upload a file exceeding the size limit. Verify the upload is rejected.
4. **Path traversal test**: Upload a file with a name like `../../etc/passwd` or `..\..\web.config`. Verify the filename is sanitized.
5. **Double extension test**: Upload a file named `image.jpg.php`. Verify the validation uses the correct (final) extension.

### Automated Test Pattern

```python
def test_disallowed_extension(client):
    data = {'file': (io.BytesIO(b'<?php system("id"); ?>'), 'shell.php')}
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400

def test_magic_byte_mismatch(client):
    data = {'file': (io.BytesIO(b'<?php system("id"); ?>'), 'shell.jpg')}
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400

def test_valid_upload(client):
    png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    data = {'file': (io.BytesIO(png_header), 'image.png')}
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
```

### Semgrep Rules That Should Pass After Fix

```yaml
rules:
  - id: unrestricted-file-upload
    patterns:
      - pattern: |
          $FILE.save($PATH)
      - pattern-not-inside: |
          if $EXT in $ALLOWED:
              ...
    message: "File upload without extension validation"
    languages: [python]
    severity: ERROR
```

### Verifying Functionality is Preserved

- Verify that valid files with allowed extensions upload successfully.
- Verify that uploaded files are retrievable and intact.
- Verify that the application handles edge cases (empty filename, no extension, very long filename).
- Test with various valid file types to ensure magic byte validation does not reject legitimate files.

## Common Mistakes

1. **Using a blacklist instead of an allowlist.** Blocking `.exe` and `.php` misses hundreds of other dangerous extensions (`.phtml`, `.shtml`, `.jsp`, `.aspx`, `.cgi`, `.py`, `.pl`, `.sh`). Always use an allowlist of known-safe extensions.

2. **Checking only the MIME type from the Content-Type header.** The Content-Type header is controlled by the client and can be spoofed. Always validate magic bytes in addition to the MIME type.

3. **Not checking for double extensions.** Files named `shell.php.jpg` may be executed as PHP by misconfigured web servers. Validate only the final extension and verify magic bytes.

4. **Storing files in the web root.** Files in `public/` or `static/` may be directly accessible and executable by the web server. Store uploads outside the web root and serve them through a controlled endpoint.

5. **Using the original filename.** The user-provided filename can contain path traversal sequences (`../`), special characters, or be extremely long. Always generate a safe filename (UUID-based).

6. **Not limiting file size at the middleware level.** Checking size only after the file is fully uploaded still allows memory exhaustion. Configure size limits in the upload middleware (multer limits, Django DATA_UPLOAD_MAX_MEMORY_SIZE, Spring multipart.max-file-size).

7. **Forgetting to validate file content after antivirus scanning.** Even if an antivirus scanner is used, it may not catch all malicious files. Defense-in-depth (extension + magic bytes + size + safe storage) is essential.

8. **Allowing SVG uploads without sanitization.** SVG files can contain embedded JavaScript and are a common XSS vector. If SVG uploads are needed, sanitize them to remove script elements.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine upload context** | Apply the most restrictive validation (images only: png, jpg, gif). Flag for manual review to expand the allowlist if needed. |
| **Upload handling is in a third-party library** | Verify the library's configuration supports file filtering. Flag for manual review if configuration is not accessible. |
| **File storage uses cloud services (S3, GCS)** | Apply the same validation before uploading to cloud storage. Ensure the cloud bucket is not publicly accessible. Flag for review. |
| **Multiple upload fields in one form** | Validate each uploaded file independently. Apply the same rules to all upload fields. |
| **Streaming uploads** | For streaming uploads where the file is not buffered in memory, validate the first chunk for magic bytes and enforce size limits via the streaming API. Flag for manual review. |

## Constraints

- **Preserve upload functionality**: Valid files with allowed types must still upload successfully.
- **No execution**: Do not execute uploaded files or run the application to test uploads.
- **Defense-in-depth**: Apply multiple validation layers (extension, magic bytes, size, filename, storage). Do not rely on a single check.
- **Minimal diff**: Add validation logic around the existing upload handler. Do not refactor unrelated code.
- **Safe defaults**: If the upload context is unknown, default to the most restrictive allowlist (images only).
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
