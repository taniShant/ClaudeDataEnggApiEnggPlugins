---
name: cwe-502-deserialization
description: "CWE-502: Insecure Deserialization Remediation — Remediate insecure deserialization vulnerabilities by replacing dangerous deserialization mechanisms with safe alternatives. This skill transforms cod"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-502: Insecure Deserialization Remediation
## Quick Start

This skill provides the fix pattern for CWE-502. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-502 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-502
- **CWE Name**: Deserialization of Untrusted Data
- **Severity**: Critical
- **OWASP Category**: A08:2021 — Software and Data Integrity Failures

## Purpose

Remediate insecure deserialization vulnerabilities by replacing dangerous deserialization mechanisms with safe alternatives. This skill transforms code that uses native object serialization formats (pickle, Java ObjectInputStream, yaml.load, node-serialize) on untrusted data into code that uses safe data interchange formats (JSON, YAML safe_load, allowlisted type deserialization) or adds integrity verification, preventing remote code execution and object injection attacks.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the affected file.
  - `line_number` (integer, required): Line where the insecure deserialization was detected.
  - `code_snippet` (string, optional): The vulnerable code flagged by the scanner.
  - `cwe_id` (string, required): Must be `CWE-502`.
- **code_context** (required, JSON object): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root.

## Vulnerable Pattern

Insecure deserialization occurs when an application deserializes data from an untrusted source using a serialization format that can instantiate arbitrary objects, execute code during deserialization, or manipulate application state. Native serialization formats in most languages (Python pickle, Java ObjectInputStream, PHP unserialize, Ruby Marshal, Node.js node-serialize) allow arbitrary code execution during deserialization.

### Detection Patterns

**General indicators:**
- Deserialization of data received from user input, network connections, files, databases, or message queues using native serialization.
- Use of pickle, shelve, yaml.load (without SafeLoader), ObjectInputStream, node-serialize, or similar on untrusted data.

**Regex patterns for detection:**
```
# Python pickle
pickle\.(load|loads)\s*\(
# Python shelve
shelve\.open\s*\(
# Python yaml unsafe load
yaml\.load\s*\((?!.*Loader\s*=\s*yaml\.SafeLoader)(?!.*Loader\s*=\s*yaml\.CSafeLoader)
yaml\.unsafe_load\s*\(
yaml\.full_load\s*\(
# Java ObjectInputStream
new\s+ObjectInputStream\s*\(|\.readObject\s*\(\s*\)
# Node.js node-serialize
(require\s*\(\s*['"]node-serialize['"]\s*\)|serialize\s*\.\s*unserialize\s*\()
# Node.js js-yaml unsafe
yaml\.load\s*\((?!.*schema\s*:\s*yaml\.SAFE_SCHEMA)
```

## Fix Pattern

### General Approach

1. **Replace with safe data formats**: Use JSON, MessagePack, Protocol Buffers, or other formats that only represent data (not executable objects) for data interchange.
2. **Use safe deserialization modes**: If the serialization library offers a safe mode (e.g., `yaml.safe_load`, `yaml.SafeLoader`), switch to it.
3. **Implement type allowlisting**: If native deserialization must be used (rare), restrict the types that can be deserialized to an explicit allowlist.
4. **Add integrity verification**: Sign serialized data with HMAC before serialization and verify before deserialization.
5. **Isolate deserialization**: If native deserialization is unavoidable, run it in a sandboxed environment with minimal privileges.

### Step-by-Step Transformation

1. Identify the deserialization call and the source of the data being deserialized.
2. Determine what types of objects are being deserialized (simple data types vs. complex objects).
3. Choose the appropriate safe alternative based on the data requirements.
4. Replace the deserialization call with the safe alternative.
5. Update the serialization call (if in the same codebase) to use the matching safe format.
6. Update any code that depends on the deserialized objects to work with the new format.
7. If migration is not immediately possible, add integrity verification (HMAC) as an interim measure.

## Language-Specific Examples

### Python (pickle to JSON)

**Before (vulnerable):**
```python
import pickle

def load_user_preferences(data: bytes) -> dict:
    return pickle.loads(data)

def save_user_preferences(prefs: dict) -> bytes:
    return pickle.dumps(prefs)
```

**After (fixed):**
```python
import json

def load_user_preferences(data: str | bytes) -> dict:
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return json.loads(data)

def save_user_preferences(prefs: dict) -> str:
    return json.dumps(prefs)
```

**Explanation:** Replace `pickle.loads` and `pickle.dumps` with `json.loads` and `json.dumps`. JSON only represents data types (strings, numbers, booleans, arrays, objects, null) and cannot execute arbitrary code during deserialization. The function signatures are updated to reflect the new data format.

### Python (pickle with HMAC — when JSON migration is not feasible)

**Before (vulnerable):**
```python
import pickle

def load_session(data: bytes) -> dict:
    return pickle.loads(data)
```

**After (fixed):**
```python
import hashlib
import hmac
import json
import os

SESSION_SECRET = os.environ["SESSION_SECRET"]

def load_session(signed_data: str) -> dict:
    """Load session data from a signed JSON payload."""
    try:
        signature, _, payload = signed_data.partition(".")
        expected_sig = hmac.new(
            SESSION_SECRET.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid session signature")
        return json.loads(payload)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid session data: {e}")

def save_session(session: dict) -> str:
    """Save session data as a signed JSON payload."""
    payload = json.dumps(session, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(
        SESSION_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{signature}.{payload}"
```

**Explanation:** When object types are simple enough for JSON, replace pickle with JSON and add HMAC signing for integrity. The secret key is loaded from an environment variable. `hmac.compare_digest` is used for constant-time comparison to prevent timing attacks.

### Python (yaml.load to yaml.safe_load)

**Before (vulnerable):**
```python
import yaml

def load_config(config_file: str) -> dict:
    with open(config_file) as f:
        return yaml.load(f)
```

**After (fixed):**
```python
import yaml

def load_config(config_file: str) -> dict:
    with open(config_file) as f:
        return yaml.safe_load(f)
```

**Explanation:** Replace `yaml.load` with `yaml.safe_load`. The safe loader only deserializes basic Python types (strings, numbers, lists, dicts, booleans, None) and does not construct arbitrary Python objects. This is a one-line fix that eliminates the vulnerability.

### Python (yaml.load with explicit Loader)

**Before (vulnerable):**
```python
import yaml

data = yaml.load(yaml_string, Loader=yaml.FullLoader)
```

**After (fixed):**
```python
import yaml

data = yaml.safe_load(yaml_string)
```

**Explanation:** `yaml.FullLoader` is still partially vulnerable to deserialization attacks. Replace with `yaml.safe_load` (equivalent to `yaml.load(data, Loader=yaml.SafeLoader)`).

### Java (ObjectInputStream)

**Before (vulnerable):**
```java
import java.io.ObjectInputStream;
import java.io.ByteArrayInputStream;

public Object deserialize(byte[] data) throws Exception {
    ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data));
    return ois.readObject();
}
```

**After (fixed — replace with JSON):**
```java
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.databind.DeserializationFeature;

public class SafeDeserializer {

    private static final ObjectMapper mapper = JsonMapper.builder()
        .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
        .build();

    public <T> T deserialize(String jsonData, Class<T> targetType) throws Exception {
        return mapper.readValue(jsonData, targetType);
    }
}
```

**Explanation:** Replace `ObjectInputStream.readObject()` with Jackson JSON deserialization into a specific target type. Jackson deserializes into a known type rather than allowing arbitrary object construction. `FAIL_ON_UNKNOWN_PROPERTIES` is disabled for forward compatibility.

### Java (ObjectInputStream with allowlist — when JSON migration is not feasible)

**Before (vulnerable):**
```java
import java.io.ObjectInputStream;
import java.io.InputStream;

public Object deserialize(InputStream input) throws Exception {
    ObjectInputStream ois = new ObjectInputStream(input);
    return ois.readObject();
}
```

**After (fixed):**
```java
import java.io.InputStream;
import java.io.ObjectInputStream;
import java.io.ObjectStreamClass;
import java.util.Set;

public class SafeObjectInputStream extends ObjectInputStream {

    private static final Set<String> ALLOWED_CLASSES = Set.of(
        "com.example.model.UserPreferences",
        "com.example.model.Settings",
        "java.lang.String",
        "java.lang.Integer",
        "java.lang.Long",
        "java.util.HashMap",
        "java.util.ArrayList"
    );

    public SafeObjectInputStream(InputStream in) throws Exception {
        super(in);
    }

    @Override
    protected Class<?> resolveClass(ObjectStreamClass desc) throws Exception {
        if (!ALLOWED_CLASSES.contains(desc.getName())) {
            throw new SecurityException("Deserialization of class not allowed: " + desc.getName());
        }
        return super.resolveClass(desc);
    }
}

// Usage:
public Object deserialize(InputStream input) throws Exception {
    SafeObjectInputStream ois = new SafeObjectInputStream(input);
    return ois.readObject();
}
```

**Explanation:** When `ObjectInputStream` cannot be eliminated, override `resolveClass` to enforce a strict allowlist of classes that may be deserialized. Any class not on the allowlist causes a `SecurityException`.

### Node.js (node-serialize)

**Before (vulnerable):**
```javascript
const serialize = require('node-serialize');

app.post('/load', (req, res) => {
    const data = serialize.unserialize(req.body.data);
    res.json(data);
});
```

**After (fixed):**
```javascript
app.post('/load', (req, res) => {
    try {
        const data = JSON.parse(req.body.data);
        res.json(data);
    } catch (err) {
        res.status(400).json({ error: 'Invalid data format' });
    }
});
```

**Explanation:** Replace `node-serialize` with `JSON.parse`. The `node-serialize` library is fundamentally unsafe because it can execute arbitrary JavaScript during deserialization (via serialized function expressions). `JSON.parse` only produces plain data types and is safe. Remove the `node-serialize` dependency from `package.json`.

### Node.js (js-yaml)

**Before (vulnerable):**
```javascript
const yaml = require('js-yaml');
const fs = require('fs');

function loadConfig(configPath) {
    const content = fs.readFileSync(configPath, 'utf8');
    return yaml.load(content, { schema: yaml.DEFAULT_SCHEMA });
}
```

**After (fixed):**
```javascript
const yaml = require('js-yaml');
const fs = require('fs');

function loadConfig(configPath) {
    const content = fs.readFileSync(configPath, 'utf8');
    return yaml.load(content, { schema: yaml.SAFE_SCHEMA });
}
```

**Explanation:** Replace `yaml.DEFAULT_SCHEMA` with `yaml.SAFE_SCHEMA`. The safe schema only supports basic data types and will not instantiate JavaScript objects or execute code.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Python pickle RCE test**: Attempt to deserialize a pickle payload that executes `os.system`:
   ```python
   import pickle, os
   class Exploit:
       def __reduce__(self):
           return (os.system, ("echo pwned",))
   payload = pickle.dumps(Exploit())
   # After fix: json.loads(payload) should raise JSONDecodeError
   ```
   The application must reject the payload.

2. **Python YAML RCE test**: Attempt to load YAML with a Python object tag:
   ```yaml
   !!python/object/apply:os.system ["echo pwned"]
   ```
   With `yaml.safe_load`, this must raise a `ConstructorError`.

3. **Java deserialization test**: Attempt to deserialize a crafted payload (e.g., using ysoserial) targeting common gadget chains. The application must either reject the payload (with allowlist) or not use `ObjectInputStream` at all (with JSON).

4. **Node.js node-serialize test**: Attempt to deserialize a payload with a function:
   ```json
   {"cmd": "_$$ND_FUNC$$_function() { require('child_process').exec('echo pwned'); }()"}
   ```
   With `JSON.parse`, this is treated as a plain string.

### Verifying Existing Functionality Is Preserved

1. Serialize a known data structure using the new safe format and deserialize it. Verify the result matches the original structure.
2. If the serialization format changed (e.g., pickle to JSON), verify that all consumers of the serialized data are updated.
3. Test with edge cases: empty objects, nested structures, unicode strings, large payloads.

### Semgrep Rules

After the fix, the following Semgrep patterns should no longer match:
```yaml
rules:
  - id: insecure-pickle-load
    patterns:
      - pattern-either:
          - pattern: pickle.loads(...)
          - pattern: pickle.load(...)
    message: "Use of pickle for deserialization is unsafe"
    severity: ERROR
  - id: insecure-yaml-load
    patterns:
      - pattern: yaml.load(...)
      - pattern-not: yaml.load(..., Loader=yaml.SafeLoader)
    message: "yaml.load without SafeLoader is unsafe"
    severity: ERROR
  - id: insecure-java-deserialization
    pattern: $OIS.readObject()
    message: "ObjectInputStream.readObject() on untrusted data"
    severity: ERROR
```

## Common Mistakes

1. **Replacing pickle with JSON but not updating the serializer**: If the serialization side still produces pickle format, the deserialization side will fail. Both sides must be migrated together.
2. **Using `yaml.FullLoader` instead of `yaml.SafeLoader`**: `FullLoader` is not fully safe. Always use `SafeLoader` or `yaml.safe_load`.
3. **Using Jackson with `enableDefaultTyping()`**: Jackson's default typing feature can be exploited similarly to native deserialization. Never enable it on untrusted data.
4. **Allowlisting too many classes in Java**: The allowlist should be as minimal as possible. Including common collection classes like `HashMap` is usually necessary but avoid including any class with a dangerous `readObject` implementation.
5. **Not removing the unsafe dependency**: After replacing `node-serialize` or similar, remove the package from `package.json` to prevent accidental reuse.
6. **Ignoring serialized data in databases or caches**: If pickle/serialized data is stored in a database or cache (Redis, Memcached), the stored data must also be migrated to the new format.
7. **Using `shelve` as a replacement for `pickle`**: `shelve` uses `pickle` internally and is equally vulnerable. Replace with a JSON-based or SQLite-based storage.
8. **Not handling the migration period**: When changing serialization formats, old data may still be in the old format. Plan a migration strategy that can read both formats temporarily, using the safe format for all new writes.

## Steps

1. Use `Read` to open the file at `vulnerability.file_path` and examine the `code_context` to identify the deserialization mechanism and data source.
2. Identify the serialization library (pickle, yaml, ObjectInputStream, node-serialize, etc.) and what data types are being deserialized.
3. Use `Grep` to find the corresponding serialization call (the producer of the data) — it may be in the same file or a different file.
4. Determine whether a safe format migration (e.g., JSON) is feasible by examining the types being serialized.
5. Use `Edit` to replace the deserialization call with the safe alternative.
6. If a matching serialization call exists in the codebase, use `Edit` to update it as well.
7. Use `Grep` to check for other instances of the same unsafe deserialization pattern in the project.
8. If a dependency should be removed (e.g., `node-serialize`), note it in the output but do not modify `package.json` without confirming with the pipeline.

## Output Format

Return a JSON object:

```json
{
  "status": "fixed | failed | needs_review",
  "file_path": "<string: absolute path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: line where the change was made>",
      "description": "<string: what was changed and why>"
    }
  ],
  "original_mechanism": "<string: the unsafe deserialization library/method replaced>",
  "replacement_mechanism": "<string: the safe alternative used>",
  "serializer_updated": "<boolean: whether the corresponding serialization call was also updated>",
  "notes": "<string: any additional context, migration notes, or recommendations>"
}
```

### Success Indicator

The `status` field is `"fixed"` and the unsafe deserialization call has been replaced with a safe alternative.

### Failure Indicator

The `status` field is `"failed"` with a description of what prevented the fix.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return `{"status": "failed", "reason": "File not found"}`. Do not retry. |
| **Complex object types prevent JSON migration** | Use a type-restricted deserialization (Java allowlist, custom safe loader). Set `status` to `"needs_review"`. |
| **Serialization and deserialization in different repositories** | Fix only the deserialization side. Note in `notes` that the serialization side needs updating. Set `status` to `"needs_review"`. |
| **Data migration required** | Fix the code but set `status` to `"needs_review"` with a note about data migration requirements. |
| **Cannot determine data source trustworthiness** | Apply the fix defensively (assume untrusted). Note the assumption in `notes`. |

## Constraints

- **Preserve functionality**: The fix must not break data exchange. Ensure the serialization and deserialization sides agree on the format.
- **Data compatibility**: Consider existing serialized data in storage. If format changes are needed, document the migration path.
- **Minimal diff**: Replace only the deserialization mechanism. Do not refactor unrelated code.
- **No new unsafe patterns**: Do not replace one unsafe mechanism with another (e.g., do not replace pickle with `eval`).
- **Dependency management**: If adding new dependencies (e.g., Jackson, defusedxml), ensure they are added to the project manifest.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Edit` for code modifications.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
